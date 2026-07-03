<template>
  <v-switch
    :model-value="modelValue === 'stable'"
    color="primary"
    density="comfortable"
    :hint="hint"
    persistent-hint
    @update:model-value="$emit('update:modelValue', $event ? 'stable' : 'unstable')"
  >
    <template #label>
      <span class="text-subtitle-1">
        Maturity: <strong>{{ modelValue }}</strong>
      </span>
    </template>
  </v-switch>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: string
}

const props = defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: string]
}>()

const hint = computed(() => {
  if (props.modelValue === 'unstable') {
    return 'ZIM files will go through staging first before moving to production.'
  }
  return 'ZIM files will go directly to production.'
})
</script>
