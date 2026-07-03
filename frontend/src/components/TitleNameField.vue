<template>
  <v-text-field
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    label="Title Name"
    variant="outlined"
    density="comfortable"
    :rules="[rules.required, rules.name]"
    :color="nameInvalid ? 'warning' : undefined"
    :base-color="nameInvalid ? 'warning' : undefined"
  >
    <template v-if="nameInvalid" #append-inner>
      <v-icon color="warning" icon="mdi-alert-circle" />
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const TITLE_NAME_PATTERN = '^[a-z0-9\\-\\.]+?_[a-z]{2,3}(?:-[a-z]{2,10})?_[a-z0-9\\-\\.]+?$'

interface Props {
  modelValue: string | null | undefined
}

const props = defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const rules = {
  required: (value: unknown) => !!value || 'This field is required',
  name: (value: unknown) => {
    if (!value) return true
    const regex = new RegExp(TITLE_NAME_PATTERN)
    if (!regex.test(String(value))) {
      return `Value does not meet pattern: ${TITLE_NAME_PATTERN}`
    }
    return true
  },
}

const nameInvalid = computed(() => {
  const value = props.modelValue
  if (!value) return false
  const regex = new RegExp(TITLE_NAME_PATTERN)
  return !regex.test(String(value))
})
</script>
