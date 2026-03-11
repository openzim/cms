<template>
  <div v-if="events.length > 0">
    <v-btn size="small" variant="outlined" class="mb-2" @click="copyToClipboard(events.join('\n'))">
      <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
      Copy All
    </v-btn>

    <v-list
      lines="one"
      density="compact"
      class="overflow-y-auto events-list-container"
      style="max-height: 400px"
    >
      <v-list-item
        v-for="(event, index) in parsedEvents"
        :key="index"
        :class="index % 2 === 0 ? 'bg-grey-lighten-4' : ''"
        class="px-3 py-1"
      >
        <v-list-item-title class="text-body-2 text-wrap">
          {{ event.timestamp }}: {{ event.message }}
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </div>
  <span v-else class="text-grey">No events</span>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import { useNotificationStore } from '@/stores/notification'

interface Props {
  events: string[]
}

const props = withDefaults(defineProps<Props>(), {
  events: () => [],
})

const notificationStore = useNotificationStore()

interface ParsedEvent {
  timestamp: string
  message: string
}

const parsedEvents = computed((): ParsedEvent[] => {
  return props.events.map((event) => {
    // Events are typically formatted as: "TIMESTAMP: message"
    const colonIndex = event.indexOf(':')
    if (colonIndex !== -1) {
      return {
        timestamp: event.substring(0, colonIndex).trim(),
        message: event.substring(colonIndex + 1).trim(),
      }
    }
    // If no colon found, treat entire string as message
    return {
      timestamp: '',
      message: event,
    }
  })
})

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
