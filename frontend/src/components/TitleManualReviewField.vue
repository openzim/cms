<template>
  <v-switch
    :model-value="modelValue"
    color="primary"
    density="comfortable"
    :hint="hint"
    persistent-hint
    @update:model-value="$emit('update:modelValue', $event === true)"
  >
    <template #label>
      <span class="text-body-large">
        Manual review: <strong>{{ modelValue ? 'yes' : 'no' }}</strong>
      </span>
    </template>
  </v-switch>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const hint = computed(() => {
  if (props.modelValue) {
    return 'ZIM files will go through staging first before moving to production.'
  }
  return 'ZIM files will go directly to production.'
})
</script>
