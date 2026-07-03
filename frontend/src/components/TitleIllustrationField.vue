<template>
  <ImageEditor
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    label="Illustration"
    description="Upload a 48x48 pixel illustration image"
  />
</template>

<script setup lang="ts">
import ImageEditor from '@/components/ImageEditor.vue'

interface Props {
  modelValue: string | null | undefined
}

defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: string | null]
}>()
</script>
