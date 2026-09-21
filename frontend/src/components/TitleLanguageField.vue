<template>
  <v-text-field
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    :label="label"
    variant="outlined"
    density="comfortable"
    :rules="[languageRule]"
    clearable
    :error="languageInvalid"
  >
    <template v-if="languageInvalid" #append-inner>
      <v-icon color="error" icon="mdi-alert-circle" />
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { languageRule } from '@/utils/validation'

interface Props {
  modelValue: string | null | undefined
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: 'Language',
})

defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const languageInvalid = computed(() => {
  const value = props.modelValue
  if (!value) return false
  return languageRule(value) !== true
})
</script>
