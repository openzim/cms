<template>
  <v-tooltip v-if="iconOnly" location="bottom">
    <template #activator="{ props: tooltipProps }">
      <span v-bind="tooltipProps">
        <v-icon
          v-if="isErrored"
          size="small"
          color="error"
          icon="mdi-alert-circle-outline"
        ></v-icon>
        <v-icon
          v-else-if="isProcessing"
          size="small"
          color="grey"
          icon="mdi-clock-outline"
        ></v-icon>
        <v-icon
          v-else-if="isMovingFiles"
          size="small"
          color="info"
          icon="mdi-truck-delivery-outline"
        ></v-icon>
        <v-icon
          v-else-if="!hasTitle"
          size="small"
          color="warning"
          icon="mdi-alert-circle-outline"
        ></v-icon>
        <v-icon v-else size="small" color="success" icon="mdi-check-circle"></v-icon>
      </span>
    </template>
    <div>
      <div class="font-weight-bold">{{ statusLabel }}</div>
      <div class="text-caption">{{ locationLabel }}</div>
    </div>
  </v-tooltip>

  <span v-else>
    <span v-if="isErrored">
      <v-icon size="small" color="error" icon="mdi-alert-circle-outline"></v-icon>
      <span class="text-caption ml-1">Errored</span>
    </span>
    <span v-else-if="isProcessing">
      <v-icon size="small" color="grey" icon="mdi-clock-outline"></v-icon>
      <span class="text-caption ml-1">Processing</span>
    </span>
    <span v-else-if="isMovingFiles">
      <v-icon size="small" color="info" icon="mdi-truck-delivery-outline"></v-icon>
      <span class="text-caption ml-1">Moving Files</span>
      <v-chip size="x-small" class="ml-1" :color="locationColor">
        {{ locationLabel }}
      </v-chip>
    </span>
    <span v-else-if="!hasTitle">
      <v-icon size="small" color="warning" icon="mdi-alert-circle-outline"></v-icon>
      <span class="text-caption ml-1">Pending Title</span>
      <v-chip size="x-small" class="ml-1" :color="locationColor">
        {{ locationLabel }}
      </v-chip>
    </span>
    <span v-else>
      <v-icon size="small" color="success" icon="mdi-check-circle"></v-icon>
      <span class="text-caption ml-1">Published</span>
      <v-chip size="x-small" class="ml-1" :color="locationColor">
        {{ locationLabel }}
      </v-chip>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Book, BookLight } from '@/types/book'

const props = withDefaults(
  defineProps<{
    book: Book | BookLight
    iconOnly?: boolean
  }>(),
  {
    iconOnly: false,
  },
)

const isErrored = computed(() => props.book.has_error)
const isProcessing = computed(() => props.book.needs_processing && !props.book.has_error)
const isMovingFiles = computed(() => props.book.needs_file_operation && !props.book.has_error)
const hasTitle = computed(() => props.book.title_id)

const statusLabel = computed(() => {
  if (isErrored.value) return 'Errored'
  if (isProcessing.value) return 'Processing'
  if (isMovingFiles.value) return 'Moving Files'
  if (!hasTitle.value) return 'Pending Title'
  return 'Published'
})

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
