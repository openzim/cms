<template>
  <v-text-field
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    :label="label"
    variant="outlined"
    density="comfortable"
    :rules="[titleNameRule]"
    :error="nameInvalid"
  >
    <template v-if="nameInvalid" #append-inner>
      <v-icon color="error" icon="mdi-alert-circle" />
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { titleNameRule } from '@/utils/validation'

interface Props {
  modelValue: string | null | undefined
  label?: string
}

const props = withDefaults(defineProps<Props>(), {
  label: 'Title Name',
})

defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const nameInvalid = computed(() => {
  const value = props.modelValue
  if (!value) return false
  return titleNameRule(value) !== true
})
</script>
