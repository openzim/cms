<template>
  <InlineImageEditor
    :model-value="resolvedModelValue"
    :label="label"
    :required="required"
    :description="description"
    :loading="loading || resolving"
    :error-message="errorMessage"
    @update:model-value="handleUpdate"
  />

  <!-- Hidden file input for compatibility -->
  <input
    ref="fileInputRef"
    type="file"
    accept="image/*"
    style="display: none"
    @change="handleFileChange"
  />
</template>

<script setup lang="ts">
import { inject, ref, watch } from 'vue'
import InlineImageEditor from '@/components/InlineImageEditor.vue'
import constants from '@/constants'
import type { Config } from '@/config'
import { fetchImageAsDataUrl, getIllustrationUrl, isIllustrationHexDigest } from '@/utils/image'

interface Props {
  modelValue: string | null | undefined
  label?: string
  required?: boolean
  description?: string | null
}

const { modelValue, label, required, description } = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const fileInputRef = ref<HTMLInputElement | null>(null)
const errorMessage = ref<string>('')
const loading = ref(false)
const resolving = ref(false)
const resolvedModelValue = ref<string | undefined>(undefined)
const config = inject<Config | null>(constants.config, null)

watch(
  () => modelValue,
  async (value) => {
    if (!value) {
      resolvedModelValue.value = undefined
      return
    }

    if (isIllustrationHexDigest(value)) {
      if (!config) {
        resolvedModelValue.value = undefined
        return
      }
      resolving.value = true
      try {
        resolvedModelValue.value = await fetchImageAsDataUrl(
          getIllustrationUrl(config.CMS_API, value),
        )
      } finally {
        resolving.value = false
      }
      return
    }

    resolvedModelValue.value = value.startsWith('data:') ? value : `data:image/png;base64,${value}`
  },
  { immediate: true },
)

const handleUpdate = (value: string) => {
  if (!value) {
    emit('update:modelValue', null)
    return
  }

  // Extract raw base64 (without data URL prefix) for backend
  const base64Data = value.includes(',') ? value.split(',')[1] : value
  emit('update:modelValue', base64Data)
}

const handleFileChange = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = target.files

  if (!files || files.length === 0) {
    return
  }

  // Clear file input
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}
</script>

<style scoped>
.drag-over :deep(.v-field) {
  border: 2px dashed rgb(var(--v-theme-primary));
  background-color: var(--overlay-primary-05);
}
</style>
