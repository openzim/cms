<template>
  <div>
    <!-- The input field comes from the parent via default slot -->
    <slot />

    <!-- Diff warning banner -->
    <div v-if="showDiff" class="text-body-2" :class="{ 'mt-2': hasCustomContent, 'mb-2': true }">
      <div class="mb-1 text-warning font-weight-medium">
        {{ diffLabel }}
      </div>
      <div class="d-flex align-center justify-space-between" :class="{ 'mb-2': hasCustomContent }">
        <!-- Custom diff content (e.g. illustration preview) -->
        <template v-if="hasCustomContent">
          <slot name="diff-content" />
        </template>
        <!-- Default: plain text value -->
        <template v-else>
          <strong>{{ diffValue ?? '(no value)' }}</strong>
        </template>

        <v-btn size="small" variant="outlined" color="warning" class="ml-3" @click="$emit('use')">
          Use this
        </v-btn>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'

defineProps<{
  /** Whether to show the diff warning banner */
  showDiff: boolean
  /** Label text, e.g. "Different from title which has:" */
  diffLabel: string
  /** The comparison value to display (used when no #diff-content slot is provided) */
  diffValue?: string | null
}>()

defineEmits<{
  /** Emitted when the user clicks "Use this" */
  use: []
}>()

const slots = useSlots()
const hasCustomContent = computed(() => !!slots['diff-content'])
</script>
