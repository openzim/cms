<template>
  <span v-if="isErrored" class="d-flex align-center">
    <v-icon size="small" color="error" icon="mdi-alert-circle-outline"></v-icon>
    <span class="text-caption ml-1">Errored</span>
  </span>
  <span v-else-if="isProcessing" class="d-flex align-center">
    <v-icon size="small" color="grey" icon="mdi-clock-outline"></v-icon>
    <span class="text-caption ml-1">Processing</span>
  </span>
  <span v-else-if="isMovingFiles" class="d-flex align-center">
    <v-icon size="small" color="info" icon="mdi-truck-delivery-outline"></v-icon>
    <span class="text-caption ml-1">Moving Files</span>
    <v-chip size="x-small" class="ml-1" :color="locationColor">
      {{ locationLabel }}
    </v-chip>
  </span>
  <span v-else class="d-flex align-center">
    <v-icon size="small" color="success" icon="mdi-check-circle"></v-icon>
    <span class="text-caption ml-1">Published</span>
    <v-chip size="x-small" class="ml-1" :color="locationColor">
      {{ locationLabel }}
    </v-chip>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Book, BookLight } from '@/types/book'

const props = defineProps<{
  book: Book | BookLight
}>()

const isErrored = computed(() => props.book.has_error)
const isProcessing = computed(() => props.book.needs_processing && !props.book.has_error)
const isMovingFiles = computed(() => props.book.needs_file_operation && !props.book.has_error)

const locationLabel = computed(() => {
  switch (props.book.location_kind) {
    case 'quarantine':
      return 'Quarantine'
    case 'staging':
      return 'Staging'
    case 'prod':
      return 'Production'
    default:
      return 'Unknown'
  }
})

const locationColor = computed(() => {
  switch (props.book.location_kind) {
    case 'quarantine':
      return 'grey'
    case 'staging':
      return 'info'
    case 'prod':
      return 'success'
    default:
      return 'grey'
  }
})
</script>
