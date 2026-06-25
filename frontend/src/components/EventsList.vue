<template>
  <div v-if="events.length > 0">
    <v-btn size="small" variant="outlined" class="mb-2" @click="copyToClipboard(events.join('\n'))">
      <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
      Copy All
    </v-btn>

    <v-list
      lines="one"
      density="compact"
      class="overflow-y-auto events-list-container striped-list"
      style="max-height: 400px"
    >
      <v-list-item v-for="(event, index) in events" :key="index" class="px-3 py-1">
        <v-list-item-title class="text-body-2 text-wrap">
          {{ event }}
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </div>
  <span v-else class="text-grey">No events</span>
</template>

<script setup lang="ts">
import { nextTick, watch } from 'vue'
import { useNotificationStore } from '@/stores/notification'

interface Props {
  events: string[]
}

const props = withDefaults(defineProps<Props>(), {
  events: () => [],
})

const notificationStore = useNotificationStore()

const scrollEventsToBottom = () => {
  const eventsList = document.querySelectorAll('.events-list-container')
  eventsList.forEach((element) => {
    element.scrollTop = element.scrollHeight
  })
}

watch(
  () => props.events,
  () => {
    nextTick(() => {
      scrollEventsToBottom()
    })
  },
  { deep: true, immediate: true },
)

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText('```\n' + text + '\n```\n')
    notificationStore.showSuccess('Copied to Clipboard!')
  } catch {
    notificationStore.showError('Unable to copy to clipboard 😞. Please copy it manually.')
  }
}
</script>

<style scoped>
.striped-list :deep(.v-list-item:nth-child(even)) {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}
</style>
