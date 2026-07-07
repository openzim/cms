<template>
  <v-text-field
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    label="Language"
    variant="outlined"
    density="comfortable"
    :rules="[langCodeRule]"
    clearable
    :color="languageInvalid ? 'warning' : undefined"
    :base-color="languageInvalid ? 'warning' : undefined"
  >
    <template v-if="languageInvalid" #append-inner>
      <v-icon color="warning" icon="mdi-alert-circle" />
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: string | null | undefined
}

const props = defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const langCodeRule = (value: unknown) => {
  if (!value) return true
  const parts = String(value).split(',')
  return parts.every((part) => part.trim().length === 3)
    ? true
    : 'Language code(s) must be 3 characters long'
}

const languageInvalid = computed(() => {
  const value = props.modelValue
  if (!value) return false
  const parts = String(value).split(',')
  return !parts.every((part) => part.trim().length === 3)
})
</script>
