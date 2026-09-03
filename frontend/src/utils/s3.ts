import axios from 'axios'
import type { PresignedUrlPart, S3UploadProgress, UploadProgress, PartEtag } from '@/types/s3'

interface S3MultipartUploadOptions {
  uploadId: string
  bucket: string
  key: string
  file: File
  partSize?: number
  presignedUrls: PresignedUrlPart[]
  uploadedParts?: Record<number, string>
}

const DEFAULT_PART_SIZE = 5 * 1024 * 1024 // 5 MB

/**
 * Client-side S3 multipart uploader.
 *
 * Manages chunked uploads to S3 presigned URLs with pause/resume support.
 * Backend API calls (initiate, complete, resume) are handled by the store
 * so that auth token refresh is handled transparently.
 */
export class S3MultipartUpload {
  readonly uploadId: string
  readonly bucket: string
  readonly key: string
  readonly file: File
  readonly partSize: number
  readonly presignedUrls: PresignedUrlPart[]
  uploadedParts: Record<number, string>
  private abortController: AbortController

  constructor(options: S3MultipartUploadOptions) {
    this.uploadId = options.uploadId
    this.bucket = options.bucket
    this.key = options.key
    this.file = options.file
    this.partSize = options.partSize ?? DEFAULT_PART_SIZE
    this.presignedUrls = options.presignedUrls
    this.uploadedParts = options.uploadedParts ?? {}
    this.abortController = new AbortController()
  }

  /** Total number of parts for this file. */
  get totalParts(): number {
    return Math.ceil(this.file.size / this.partSize)
  }

  /** Upload a single part to S3 using its presigned URL. */
  async uploadPart(partNumber: number, part: Blob): Promise<string | undefined> {
    if (this.uploadedParts[partNumber]) {
      console.log(`Part ${partNumber} already uploaded`)
      return this.uploadedParts[partNumber]
    }

    const presignedEntry = this.presignedUrls.find((p) => p.part_number === partNumber)

    if (!presignedEntry) {
      throw new Error(`No presigned URL found for part ${partNumber}`)
    }

    try {
      const response = await axios.put(presignedEntry.url, part, {
        headers: {
          'Content-Type': '',
        },
        signal: this.abortController.signal,
        timeout: 300000, // 5 minutes per 5 MB part
      })

      if (response.status < 200 || response.status >= 300) {
        throw new Error(`Upload failed for part ${partNumber}: HTTP ${response.status}`)
      }

      const etag = response.headers.etag
      if (!etag) {
        throw new Error(`No ETag returned for part ${partNumber}`)
      }

      this.uploadedParts[partNumber] = etag
      this.saveProgress()

      return etag
    } catch (error: unknown) {
      if (axios.isCancel(error)) {
        console.log(`Part ${partNumber} upload paused`)
        return undefined
      }
      throw error
    }
  }

  /** Upload all parts sequentially with progress tracking. */
  async uploadAll(onProgress: (progress: UploadProgress) => void): Promise<void> {
    const totalParts = this.totalParts

    for (let partNumber = 1; partNumber <= totalParts; partNumber++) {
      if (this.uploadedParts[partNumber]) {
        onProgress({
          partNumber,
          uploaded: totalParts,
          completed: Object.keys(this.uploadedParts).length,
          status: 'already_uploaded',
        })
        continue
      }

      onProgress({
        partNumber,
        uploaded: totalParts,
        completed: Object.keys(this.uploadedParts).length,
        status: 'started',
      })

      const start = (partNumber - 1) * this.partSize
      const end = Math.min(start + this.partSize, this.file.size)
      await this.uploadPart(partNumber, this.file.slice(start, end))

      // If the signal was aborted (user paused), stop iterating so we don't
      // silently skip remaining parts and later fail in completeUpload.
      if (this.abortController.signal.aborted) {
        throw new Error('Upload paused')
      }

      onProgress({
        partNumber,
        uploaded: totalParts,
        completed: Object.keys(this.uploadedParts).length,
        status: 'completed',
      })
    }
  }

  /**
   * Get ETags sorted by part number
   */
  getPartETags(): PartEtag[] {
    return Object.entries(this.uploadedParts)
      .sort(([a], [b]) => parseInt(a) - parseInt(b))
      .map(([part_number, etag]) => ({
        part_number: parseInt(part_number),
        etag,
      }))
  }

  /** Pause the upload by aborting in-flight requests. */
  pause(): void {
    this.abortController.abort()
  }

  /** Reset the abort controller so the upload can resume. */
  resume(): void {
    this.abortController = new AbortController()
  }

  /** Save current progress to localStorage for resume capability. */
  saveProgress(): void {
    const progress: S3UploadProgress = {
      uploadId: this.uploadId,
      key: this.key,
      bucket: this.bucket,
      uploadedParts: this.uploadedParts,
      fileName: this.file.name,
      fileSize: this.file.size,
      fileType: this.file.type,
      timestamp: Date.now(),
    }
    localStorage.setItem(`s3-upload-${this.uploadId}`, JSON.stringify(progress))
  }

  /** Remove progress from localStorage (called on successful completion). */
  clearProgress(): void {
    localStorage.removeItem(`s3-upload-${this.uploadId}`)
  }

  /** Load previously saved progress from localStorage. */
  static loadProgress(uploadId: string): S3UploadProgress | null {
    const saved = localStorage.getItem(`s3-upload-${uploadId}`)
    if (!saved) return null
    try {
      return JSON.parse(saved) as S3UploadProgress
    } catch {
      return null
    }
  }
}
