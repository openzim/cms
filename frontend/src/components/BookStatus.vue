<template>
  <span v-if="book.status === 'pending_processing'" class="d-flex align-center">
    <v-icon size="small" color="grey" icon="mdi-clock-outline"></v-icon>
    <span class="text-caption ml-1">Pending Processing</span>
  </span>
  <span v-else-if="book.status === 'qa_failed'" class="d-flex align-center">
    <v-icon size="small" color="warning" icon="mdi-alert-circle-outline"></v-icon>
    <span class="text-caption ml-1">QA Failed</span>
  </span>
  <span v-else-if="book.status === 'pending_title'" class="d-flex align-center">
    <v-icon size="small" color="info" icon="mdi-book-search-outline"></v-icon>
    <span class="text-caption ml-1">Pending Title</span>
  </span>
  <span v-else-if="book.status === 'pending_move'" class="d-flex align-center">
    <v-icon size="small" color="info" icon="mdi-truck-delivery-outline"></v-icon>
    <span class="text-caption ml-1">Pending Move</span>
  </span>
  <span v-else-if="book.status === 'published'" class="d-flex align-center">
    <v-icon size="small" color="success" icon="mdi-check-circle"></v-icon>
    <span class="text-caption ml-1">Published</span>
  </span>
  <span v-else-if="book.status === 'errored'" class="d-flex align-center">
    <v-icon size="small" color="error" icon="mdi-alert-circle-outline"></v-icon>
    <span class="text-caption ml-1">Errored</span>
  </span>
  <span v-else class="d-flex align-center">
    <v-icon size="small" color="grey" icon="mdi-help-circle-outline"></v-icon>
    <span class="text-caption ml-1">{{ book.status }}</span>
  </span>
</template>

<script setup lang="ts">
import type { Book, BookLight } from '@/types/book'

// Props
defineProps<{
  book: Book | BookLight
}>()
</script>
