<template>
  <InlineImageEditor
    :model-value="normalizedModelValue"
    :label="label"
    :required="required"
    :description="description"
    :loading="loading"
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
import { computed, ref } from 'vue'
import InlineImageEditor from './InlineImageEditor.vue'

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

// Convert raw base64 to data URL if needed
const normalizedModelValue = computed(() => {
  if (!modelValue) return undefined

  // If already a data URL, return as is
  if (modelValue.startsWith('data:')) {
    return modelValue
  }

  // If it's raw base64, add the data URL prefix
  // Assume PNG format for base64 strings (most common)
  return `data:image/png;base64,${modelValue}`
})

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
  background-color: rgba(var(--v-theme-primary), 0.05);
}
</style>
