<template>
  <ImageEditor
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    :label="label"
    description="Upload a 48x48 pixel illustration image"
  />
</template>

<script setup lang="ts">
import ImageEditor from '@/components/ImageEditor.vue'

interface Props {
  modelValue: string | null | undefined
  label?: string
}

withDefaults(defineProps<Props>(), {
  label: 'Illustration',
})

defineEmits<{
  'update:modelValue': [value: string | null]
}>()
</script>
