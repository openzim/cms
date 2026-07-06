<template>
  <v-chip size="x-small" :color="locationColor" variant="flat" style="width: fit-content">
    {{ locationLabel }}
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Book, BookLight } from '@/types/book'

const props = defineProps<{
  book: Book | BookLight
}>()

const locationLabel = computed(() => {
  switch (props.book.location_kind) {
    case 'quarantine':
      return 'Quarantine'
    case 'staging':
      return 'Staging'
    case 'prod':
      return 'Production'
    case 'to_delete':
      return 'To Delete'
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
