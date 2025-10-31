<template>
  <span v-if="!zimfarmNotification.processed" class="d-flex align-center">
    <v-icon size="small" color="success" icon="mdi-clock-check-outline"></v-icon>
    <span class="text-caption ml-1">Pending</span>
  </span>
  <span v-else-if="zimfarmNotification.errored" class="d-flex align-center">
    <v-icon size="small" color="error" icon="mdi-alert-circle-outline"></v-icon>
    <span class="text-caption ml-1">Fatal Error</span>
  </span>
  <span v-else-if="!zimfarmNotification.book_id" class="d-flex align-center">
    <v-icon size="small" color="warning" icon="mdi-alert-circle-outline"></v-icon>
    <span class="text-caption ml-1">Bad Notification</span>
  </span>
  <span v-else class="d-flex align-center">
    <v-icon size="small" color="success" icon="mdi-check"></v-icon>
    <span class="text-caption ml-1">Processed</span>
  </span>
</template>

<script setup lang="ts">
import type { ZimfarmNotification, ZimfarmNotificationLight } from '@/types/zimfarmNotification'

// Props

defineProps<{
  zimfarmNotification: ZimfarmNotification | ZimfarmNotificationLight
}>()
</script>
