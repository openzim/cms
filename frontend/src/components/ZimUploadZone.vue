<template>
  <div>
    <!-- Drop Zone -->
    <v-sheet
      :class="['rounded', 'overflow-hidden', 'position-relative', { 'border-primary': isDragging }]"
      :style="{
        border: isDragging
          ? '2px dashed rgb(var(--v-theme-primary))'
          : '2px dashed rgb(var(--v-border-color))',
        minHeight: '220px',
        cursor: state === 'uploading' ? 'default' : 'pointer',
        backgroundColor: isDragging ? 'rgb(var(--v-theme-primary), 0.05)' : undefined,
      }"
      @click="handleDropZoneClick"
      @drop.prevent="handleDrop"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @dragenter.prevent="isDragging = true"
      @paste="handlePaste"
      tabindex="0"
    >
      <div class="d-flex flex-column align-center justify-center pa-8" style="min-height: 220px">
        <!-- Idle / No file selected -->
        <template v-if="state === 'idle'">
          <v-icon size="48" color="grey-lighten-1">mdi-cloud-upload</v-icon>
          <p class="text-body-1 text-grey-darken-1 mt-3 mb-0 text-center">
            Drag &amp; drop a ZIM file here
          </p>
          <p class="text-body-2 text-grey mt-2 mb-0 text-center">
            or click to browse, or paste (Ctrl+V)
          </p>
        </template>

        <!-- File selected, ready to upload -->
        <template v-if="state === 'ready' || state === 'paused'">
          <v-icon size="48" color="primary">mdi-file</v-icon>
          <p class="text-body-1 mt-3 mb-1 text-center font-weight-medium">
            {{ selectedFile!.name }}
          </p>
          <p class="text-body-2 text-grey mb-0">
            {{ formattedBytesSize(selectedFile!.size) }}
          </p>
        </template>

        <!-- Uploading -->
        <template v-if="state === 'uploading'">
          <v-progress-circular
            :model-value="uploadProgressPercent"
            :size="64"
            :width="6"
            color="primary"
          >
            {{ uploadProgressPercent }}%
          </v-progress-circular>
          <p class="text-body-1 mt-3 mb-0 text-center">Uploading {{ selectedFile!.name }}</p>
          <p v-if="uploadSpeedText || uploadEtaText" class="text-body-2 text-grey mt-2 mb-0">
            <template v-if="uploadSpeedText">{{ uploadSpeedText }}</template>
            <template v-if="uploadSpeedText && uploadEtaText"> · </template>
            <template v-if="uploadEtaText">{{ uploadEtaText }}</template>
          </p>
          <v-btn variant="text" color="warning" size="small" class="mt-2" @click.stop="handlePause">
            <v-icon class="mr-1">mdi-pause</v-icon>
            Pause
          </v-btn>
        </template>

        <!-- Completing -->
        <template v-if="state === 'completing'">
          <v-progress-circular indeterminate size="48" color="primary" />
          <p class="text-body-1 mt-3 mb-0">Finalizing upload...</p>
        </template>

        <!-- Done -->
        <template v-if="state === 'done'">
          <v-icon size="48" color="success">mdi-check-circle</v-icon>
          <p class="text-body-1 mt-3 mb-0 text-success font-weight-medium">
            Upload complete! Zimfarm is now processing your ZIM file and will be imported into the
            CMS shortly. Please, wait for book to be associated with title.
          </p>
          <p class="text-body-2 text-grey mt-1 mb-0">{{ selectedFile!.name }}</p>
          <v-btn
            variant="text"
            color="primary"
            size="small"
            class="mt-2"
            @click.stop="handleUploadAnother"
          >
            <v-icon class="mr-1">mdi-plus</v-icon>
            Upload another
          </v-btn>
        </template>

        <!-- Error -->
        <template v-if="state === 'error'">
          <v-icon size="48" color="error">mdi-alert-circle</v-icon>
          <p class="text-body-1 mt-3 mb-0 text-error">Upload failed</p>
          <p class="text-body-2 text-grey mt-1 mb-0 text-center">{{ errorMessage }}</p>
          <div class="d-flex ga-2 mt-3">
            <v-btn variant="tonal" color="primary" size="small" @click.stop="handleStartUpload">
              <v-icon class="mr-1">mdi-refresh</v-icon>
              Retry
            </v-btn>
            <v-btn variant="text" size="small" @click.stop="handleReset"> Cancel </v-btn>
          </div>
        </template>
      </div>
    </v-sheet>

    <div v-if="state === 'ready' || state === 'paused'" class="d-flex ga-2 mt-3 justify-end">
      <v-btn variant="outlined" @click="handleReset">
        <v-icon class="mr-1">mdi-close</v-icon>
        Cancel
      </v-btn>
      <v-btn variant="elevated" color="primary" :disabled="!canUpload" @click="handleStartUpload">
        <v-icon class="mr-1">mdi-upload</v-icon>
        {{ state === 'paused' ? 'Resume Upload' : 'Upload' }}
      </v-btn>
    </div>

    <v-alert v-if="state === 'error' && errorMessage" type="error" class="mt-3" density="compact">
      {{ errorMessage }}
    </v-alert>

    <input
      ref="fileInputRef"
      type="file"
      accept=".zim"
      style="display: none"
      @change="handleFileInputChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import axios from 'axios'
import { useTitleStore } from '@/stores/title'
import { useNotificationStore } from '@/stores/notification'
import { S3MultipartUpload } from '@/utils/s3'
import { formattedBytesSize, formatEta } from '@/utils/format'
import type { UploadProgress } from '@/types/s3'

interface Props {
  titleId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'upload-complete'): void
}>()

type UploadState = 'idle' | 'ready' | 'uploading' | 'paused' | 'completing' | 'done' | 'error'

const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const PART_SIZE = 5 * 1024 * 1024

const fileInputRef = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const state = ref<UploadState>('idle')
const selectedFile = ref<File | null>(null)
const errorMessage = ref('')

const uploadInstance = ref<S3MultipartUpload | null>(null)
const completedParts = ref(0)

const uploadSpeedBps = ref(0)
const uploadEtaSeconds = ref(0)
let currentPartStartedAt = 0
const totalParts = computed(() => {
  if (!selectedFile.value) return 0
  return Math.ceil(selectedFile.value.size / PART_SIZE)
})

const canUpload = computed(() => {
  return selectedFile.value !== null
})

const uploadProgressPercent = computed(() => {
  if (totalParts.value === 0) return 0
  return Math.round((completedParts.value / totalParts.value) * 100)
})

const uploadSpeedText = computed(() => {
  if (uploadSpeedBps.value <= 0) return ''
  return `${formattedBytesSize(uploadSpeedBps.value)}/s`
})

const uploadEtaText = computed(() => {
  if (uploadEtaSeconds.value <= 0) return ''
  return formatEta(uploadEtaSeconds.value)
})

function selectFile(file: File): boolean {
  if (!file.name.endsWith('.zim')) return false
  selectedFile.value = file
  errorMessage.value = ''
  state.value = 'ready'
  return true
}

function handleDropZoneClick(event: MouseEvent) {
  if ((event.target as HTMLElement).closest('button')) return
  fileInputRef.value?.click()
}

function handleFileInputChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || files.length === 0) return
  if (selectFile(files[0])) {
    // state already set to 'ready' in selectFile
  }
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function handleDrop(event: DragEvent) {
  isDragging.value = false
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return
  selectFile(files[0])
}

function handlePaste(event: ClipboardEvent) {
  const files = event.clipboardData?.files
  if (files && files.length > 0) {
    event.preventDefault()
    selectFile(files[0])
  }
}

async function handleStartUpload() {
  if (!selectedFile.value) return

  state.value = 'uploading'
  errorMessage.value = ''
  uploadSpeedBps.value = 0
  uploadEtaSeconds.value = 0
  currentPartStartedAt = 0

  try {
    if (!uploadInstance.value) {
      const init = await titleStore.initiateUpload(props.titleId, selectedFile.value, PART_SIZE)

      uploadInstance.value = new S3MultipartUpload({
        uploadId: init.upload_id,
        bucket: init.bucket,
        key: init.key,
        file: selectedFile.value,
        partSize: PART_SIZE,
        presignedUrls: init.presigned_urls,
      })
    } else {
      uploadInstance.value.resume()
    }

    await uploadInstance.value.uploadAll((progress: UploadProgress) => {
      completedParts.value = progress.completed

      if (progress.status === 'started') {
        currentPartStartedAt = performance.now()
      }

      if (progress.status === 'completed') {
        const chunkStart = (progress.partNumber - 1) * PART_SIZE
        const chunkEnd = Math.min(chunkStart + PART_SIZE, selectedFile.value!.size)
        const chunkBytes = chunkEnd - chunkStart

        if (currentPartStartedAt > 0) {
          const elapsedMs = performance.now() - currentPartStartedAt
          const speedBps = (chunkBytes / elapsedMs) * 1000
          if (Number.isFinite(speedBps) && speedBps > 0) {
            uploadSpeedBps.value = speedBps
            const remainingBytes = selectedFile.value!.size - chunkEnd
            uploadEtaSeconds.value = remainingBytes / speedBps
          }
        }
      }
    })

    state.value = 'completing'
    await titleStore.completeUpload(props.titleId, {
      upload_id: uploadInstance.value.uploadId,
      key: uploadInstance.value.key,
      bucket: uploadInstance.value.bucket,
      parts: uploadInstance.value.getPartETags(),
    })

    uploadInstance.value.clearProgress()
    state.value = 'done'
    notificationStore.showSuccess(
      `"${selectedFile.value.name}" uploaded successfully! A zimfarm task has been created.`,
    )
    emit('upload-complete')
  } catch (err: unknown) {
    // If the user intentionally paused, don't treat it as an error
    if (err instanceof Error && err.message === 'Upload paused') {
      return
    }

    // 409 Conflict means the upload is broken (already completed/aborted
    // server-side). Clean up so we don't reuse a stale upload ID.
    // Errors during part uploads are retryable; keep the instance so resume works.
    const isConflict = axios.isAxiosError(err) && err.response?.status === 409
    const failedDuringCompletion = state.value === 'completing'
    if (isConflict || failedDuringCompletion) {
      uploadInstance.value?.clearProgress()
      uploadInstance.value = null
    }

    const apiErrors = titleStore.errors.length > 0 ? [...titleStore.errors] : []
    const message =
      apiErrors.length > 0
        ? apiErrors.join(', ')
        : err instanceof Error
          ? err.message
          : 'Unknown error'

    console.error('Upload failed:', err)

    if (apiErrors.length > 0) {
      notificationStore.showErrors(apiErrors)
    } else {
      notificationStore.showError(message)
    }

    state.value = 'error'
    errorMessage.value = message
  }
}

function handlePause() {
  uploadInstance.value?.pause()
  state.value = 'paused'
}

function handleReset() {
  uploadInstance.value?.pause()
  uploadInstance.value?.clearProgress()
  uploadInstance.value = null
  selectedFile.value = null
  completedParts.value = 0
  uploadSpeedBps.value = 0
  uploadEtaSeconds.value = 0
  currentPartStartedAt = 0
  errorMessage.value = ''
  state.value = 'idle'
}

function handleUploadAnother() {
  handleReset()
  nextTick(() => {
    fileInputRef.value?.click()
  })
}
</script>
