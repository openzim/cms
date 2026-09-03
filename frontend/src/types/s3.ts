export interface PresignedUrlPart {
  part_number: number
  url: string
}

export interface S3MultipartUpload {
  upload_id: string
  key: string
  bucket: string
  presigned_urls: PresignedUrlPart[]
}

export interface FileUploadRequest {
  filename: string
  filesize: number
  part_size: number
  upload_id?: string // optional, for resuming a previous upload
}

export interface PartEtag {
  part_number: number
  etag: string
}

export interface MultipartCompleteRequest {
  upload_id: string
  key: string
  bucket: string
  parts: PartEtag[]
}

/** Saved upload progress in localStorage for resume capability. */
export interface S3UploadProgress {
  uploadId: string
  key: string
  bucket: string
  uploadedParts: Record<number, string> // partNumber -> ETag
  fileName: string
  fileSize: number
  fileType: string
  timestamp: number
}

/** Progress event emitted during upload. */
export interface UploadProgress {
  partNumber: number
  uploaded: number
  completed: number
  status: 'already_uploaded' | 'completed' | 'started'
}
