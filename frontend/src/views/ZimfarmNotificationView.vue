<!-- View showing a single zimfarm notification -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && zimfarmNotification">
      <v-card flat>
        <v-card-text class="pa-0">
          <div class="ml-4 mr-4 mt-2 mb-2">
            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Id</div>
              </v-col>
              <v-col cols="12" md="9">
                <code>{{ zimfarmNotification.id }}</code>
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Status</div>
              </v-col>
              <v-col cols="12" md="9">
                <ZimfarmNotificationStatus :zimfarm-notification="zimfarmNotification" />
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Book Id</div>
              </v-col>
              <v-col cols="12" md="9">
                <code>{{ zimfarmNotification.book_id || 'None' }}</code>
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Received</div>
              </v-col>
              <v-col cols="12" md="9">
                <v-tooltip location="bottom">
                  <template #activator="{ props }">
                    <code v-bind="props">
                      {{ fromNow(zimfarmNotification.received_at) }}
                    </code>
                  </template>
                  <span>{{ formatDt(zimfarmNotification.received_at) }}</span>
                </v-tooltip>
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Events</div>
              </v-col>
              <v-col cols="12" md="9">
                <EventsList :events="zimfarmNotification.events" />
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Content</div>
              </v-col>
              <v-col cols="12" md="9">
                <v-btn
                  size="small"
                  variant="outlined"
                  class="mb-2"
                  @click="copyToClipboard(JSON.stringify(zimfarmNotification.content, null, 2))"
                >
                  <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                  Copy
                </v-btn>
                <div class="overflow-y-auto overflow-x-auto" style="max-height: 400px">
                  <pre>{{ JSON.stringify(zimfarmNotification.content, null, 2) }}</pre>
                </div>
              </v-col>
            </v-row>
          </div>
        </v-card-text>
      </v-card>
    </div>
  </v-container>
</template>

<script setup lang="ts">
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useZimfarmNotificationStore } from '@/stores/zimfarmNotification'
import type { ZimfarmNotification } from '@/types/zimfarmNotification'
import { onMounted, ref } from 'vue'
import { formatDt, fromNow } from '@/utils/format'
import EventsList from '@/components/EventsList.vue'
import ZimfarmNotificationStatus from '@/components/ZimfarmNotificationStatus.vue'

const loadingStore = useLoadingStore()
const zimfarmNotificationStore = useZimfarmNotificationStore()
const notificationStore = useNotificationStore()

const error = ref<string | null>(null)
const zimfarmNotification = ref<ZimfarmNotification | null>(null)
const dataLoaded = ref(false)

interface Props {
  id: string
  taskId: string
}

const props = withDefaults(defineProps<Props>(), {})

const loadData = async () => {
  loadingStore.startLoading('Fetching zimfarm notification...')

  const data = await zimfarmNotificationStore.fetchZimfarmNotification(props.id, props.taskId)
  if (data) {
    error.value = null
    zimfarmNotification.value = data
    dataLoaded.value = true
  } else {
    error.value = 'Failed to load zimfarm notification'
    for (const err of zimfarmNotificationStore.errors) {
      notificationStore.showError(err)
    }
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

onMounted(async () => {
  await loadData()
})

const copyToClipboard = async (log: string) => {
  try {
    await navigator.clipboard.writeText('```\n' + log + '\n```\n')
    notificationStore.showSuccess(`Copied to Clipboard!`)
  } catch {
    notificationStore.showError(`Unable to copy to clipboard 😞. Please copy it manually.`)
  }
}
</script>
