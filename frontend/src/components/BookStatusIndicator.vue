<template>
  <div class="d-inline-flex align-center">
    <template v-if="isErrored">
      <v-icon size="small" color="error" icon="mdi-alert-circle-outline" />
      <span class="text-caption ml-1">Errored</span>
    </template>
    <template v-else-if="isProcessing">
      <v-icon size="small" color="grey" icon="mdi-clock-outline" />
      <span class="text-caption ml-1">Processing</span>
    </template>
    <template v-else-if="isDeleted">
      <v-icon size="small" color="grey-darken-2" icon="mdi-delete" />
      <span class="text-caption ml-1">Deleted</span>
    </template>
    <template v-else-if="isToBeDeleted">
      <v-icon size="small" color="warning" icon="mdi-delete-clock" />
      <span class="text-caption ml-1">To Be Deleted</span>
    </template>
    <template v-else-if="isMovingFiles">
      <v-icon size="small" color="info" icon="mdi-truck-delivery-outline" />
      <span class="text-caption ml-1">Moving Files</span>
    </template>
    <template v-else-if="!hasTitle">
      <v-icon size="small" color="warning" icon="mdi-alert-circle-outline" />
      <span class="text-caption ml-1">Pending Title</span>
    </template>
    <template v-else-if="isStaging">
      <v-icon size="small" color="warning" icon="mdi-eye-outline" />
      <span class="text-caption ml-1">Staging</span>
    </template>
    <template v-else>
      <v-icon size="small" color="success" icon="mdi-check-circle" />
      <span class="text-caption ml-1">Published</span>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Book, BookLight } from '@/types/book'

const props = defineProps<{
  book: Book | BookLight
}>()

const isErrored = computed(() => props.book.has_error)
const isDeleted = computed(() => props.book.location_kind === 'deleted')
const isToBeDeleted = computed(() => props.book.location_kind === 'to_delete')
const isStaging = computed(() => props.book.location_kind === 'staging')
const isProcessing = computed(() => props.book.needs_processing && !props.book.has_error)
const isMovingFiles = computed(
  () =>
    props.book.needs_file_operation &&
    !props.book.has_error &&
    props.book.location_kind !== 'to_delete' &&
    props.book.location_kind !== 'deleted',
)
const hasTitle = computed(() => props.book.title_id)
</script>
