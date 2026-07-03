<template>
  <v-text-field
    v-if="!textarea"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    :label="label"
    variant="outlined"
    density="comfortable"
    :rules="allRules"
    clearable
    :color="invalid ? 'warning' : undefined"
    :base-color="invalid ? 'warning' : undefined"
  >
    <template v-if="maxGraphemes" #counter> {{ graphemeCount }}/{{ maxGraphemes }} </template>
    <template v-if="invalid" #append-inner>
      <v-icon color="warning" icon="mdi-alert-circle" />
    </template>
  </v-text-field>
  <v-textarea
    v-else
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? null)"
    :label="label"
    variant="outlined"
    density="comfortable"
    :rules="allRules"
    :rows="rows ?? 3"
    clearable
    :color="invalid ? 'warning' : undefined"
    :base-color="invalid ? 'warning' : undefined"
  >
    <template v-if="maxGraphemes" #counter> {{ graphemeCount }}/{{ maxGraphemes }} </template>
    <template v-if="invalid" #append-inner>
      <v-icon color="warning" icon="mdi-alert-circle" />
    </template>
  </v-textarea>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { byGrapheme } from 'split-by-grapheme'

interface Props {
  modelValue: string | null | undefined
  label: string
  rules?: Array<(value: unknown) => string | true>
  textarea?: boolean
  rows?: number
  maxGraphemes?: number
}

const props = withDefaults(defineProps<Props>(), {
  rules: () => [],
  textarea: false,
  maxGraphemes: undefined,
})

defineEmits<{
  'update:modelValue': [value: string | null]
}>()

const graphemeCount = computed(() => {
  if (!props.modelValue) return 0
  return String(props.modelValue).split(byGrapheme).length
})

const lengthRule = computed(() => {
  if (!props.maxGraphemes) return []
  return [
    (value: unknown) => {
      if (!value) return true
      if (String(value).split(byGrapheme).length > props.maxGraphemes!) {
        return `Maximum length is ${props.maxGraphemes} characters.`
      }
      return true
    },
  ]
})

const allRules = computed(() => [...props.rules, ...lengthRule.value])

const invalid = computed(() => {
  for (const rule of allRules.value) {
    const result = rule(props.modelValue)
    if (typeof result === 'string') return true
  }
  if (props.maxGraphemes && graphemeCount.value > props.maxGraphemes) return true
  return false
})
</script>
