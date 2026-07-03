<template>
  <v-combobox
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event ?? [])"
    label="Expected Flavours"
    variant="outlined"
    density="compact"
    clearable
    chips
    multiple
    closable-chips
    hint="Press Enter to add a new flavour or select from available options"
    persistent-hint
    :items="availableFlavours"
    :loading="loading"
    :rules="[flavourRule]"
  >
    <template #item="{ props, item }">
      <v-list-item v-bind="props" :title="item.title === '' ? 'Empty' : item.title" />
    </template>
  </v-combobox>
</template>

<script setup lang="ts">
interface Props {
  modelValue: string[] | null | undefined
  availableFlavours: string[]
  loading?: boolean
}

defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const flavourRule = (value: unknown) => {
  if (!value || (Array.isArray(value) && value.length === 0)) return true
  const flavours = Array.isArray(value) ? value : [value]
  const invalid = flavours.filter((f: string) => f && !/^[a-zA-Z]+$/.test(f))
  if (invalid.length > 0) {
    return `Flavours must contain only alphabetic characters. Invalid: ${invalid.join(', ')}`
  }
  return true
}
</script>
