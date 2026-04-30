<template>
  <div
    class="d-flex ga-1 py-md-1 ga-md-0"
    :class="
      forceRow ? 'flex-row justify-start' : 'flex-row flex-md-column justify-end justify-md-end'
    "
  >
    <div class="d-flex align-center" :class="forceRow ? 'mb-0 mr-2' : 'mb-1 mb-md-0 mr-md-2'">
      <template v-if="isErrored">
        <v-icon size="small" color="error" icon="mdi-alert-circle-outline"></v-icon>
        <span class="text-caption ml-1">Errored</span>
      </template>
      <template v-else-if="isProcessing">
        <v-icon size="small" color="grey" icon="mdi-clock-outline"></v-icon>
        <span class="text-caption ml-1">Processing</span>
      </template>
      <template v-else-if="isDeleted">
        <v-icon size="small" color="grey-darken-2" icon="mdi-delete"></v-icon>
        <span class="text-caption ml-1">Deleted</span>
      </template>
      <template v-else-if="isToBeDeleted">
        <v-icon size="small" color="warning" icon="mdi-delete-clock"></v-icon>
        <span class="text-caption ml-1">To Be Deleted</span>
      </template>
      <template v-else-if="isMovingFiles">
        <v-icon size="small" color="info" icon="mdi-truck-delivery-outline"></v-icon>
        <span class="text-caption ml-1">Moving Files</span>
      </template>
      <template v-else-if="!hasTitle">
        <v-icon size="small" color="warning" icon="mdi-alert-circle-outline"></v-icon>
        <span class="text-caption ml-1">Pending Title</span>
      </template>
      <template v-else>
        <v-icon size="small" color="success" icon="mdi-check-circle"></v-icon>
        <span class="text-caption ml-1">Published</span>
      </template>
    </div>
    <v-chip
      v-if="showLocationChip"
      size="x-small"
      :color="locationColor"
      variant="flat"
      class="align-self-start"
    >
      {{ locationLabel }}
    </v-chip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Book, BookLight } from '@/types/book'

const props = withDefaults(
  defineProps<{
    book: Book | BookLight
    forceRow?: boolean
  }>(),
  {
    forceRow: false,
  },
)

const isErrored = computed(() => props.book.has_error)
const isDeleted = computed(() => props.book.location_kind === 'deleted')
const isToBeDeleted = computed(() => props.book.location_kind === 'to_delete')
const isProcessing = computed(() => props.book.needs_processing && !props.book.has_error)
const isMovingFiles = computed(
  () =>
    props.book.needs_file_operation &&
    !props.book.has_error &&
    props.book.location_kind !== 'to_delete' &&
    props.book.location_kind !== 'deleted',
)
const hasTitle = computed(() => props.book.title_id)

const showLocationChip = computed(() => {
  // If the evaluated status is 'Errored' or 'Processing', we want to show the location chip
  // even if the location is 'deleted' or 'to_delete' so the user knows where the errored/processing book is.
  if (isErrored.value) return true
  if (isProcessing.value) return true
  // Otherwise, if the status evaluates exactly to 'Deleted' or 'To Be Deleted', we hide the redundant chip.
  if (isDeleted.value) return false
  if (isToBeDeleted.value) return false
  return true
})

const locationLabel = computed(() => {
  switch (props.book.location_kind) {
    case 'quarantine':
      return 'Quarantine'
    case 'staging':
      return 'Staging'
    case 'prod':
      return 'Production'
    case 'to_delete':
      return 'To Be Deleted'
    case 'deleted':
      return 'Deleted'
    default:
      return 'Unknown'
  }
})

const locationColor = computed(() => {
  switch (props.book.location_kind) {
    case 'quarantine':
      return 'warning'
    case 'staging':
      return 'secondary'
    case 'prod':
      return 'success'
    case 'to_delete':
      return 'info'
    case 'deleted':
      return 'red-lighten-1'
    default:
      return 'grey'
  }
})
</script>
