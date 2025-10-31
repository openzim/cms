<!-- View showing a single zimfarm notification -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && zimfarmNotification">
      <v-table>
        <tbody>
          <tr>
            <th class="text-left" style="width: 200px">Id</th>
            <td>
              <code>{{ zimfarmNotification.id }}</code>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Status</th>
            <td>
              <ZimfarmNotificationStatus :zimfarm-notification="zimfarmNotification" />
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Book Id</th>
            <td>
              <code>{{ zimfarmNotification.book_id || 'None' }}</code>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Received</th>
            <td>
              <v-tooltip location="bottom">
                <template #activator="{ props }">
                  <code v-bind="props">
                    {{ fromNow(zimfarmNotification.received_at) }}
                  </code>
                </template>
                <span>{{ formatDt(zimfarmNotification.received_at) }}</span>
              </v-tooltip>
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">
              Events
              <v-btn
                size="small"
                variant="outlined"
                class="ml-2"
                @click="copyToClipboard(zimfarmNotification.events.join('\n'))"
              >
                <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                Copy
              </v-btn>
            </th>
            <td class="py-2">
              <pre v-for="event in zimfarmNotification.events" :key="event">{{ event }}</pre>
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">
              Content
              <v-btn
                size="small"
                variant="outlined"
                class="ml-2"
                @click="copyToClipboard(JSON.stringify(zimfarmNotification.content, null, 2))"
              >
                <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                Copy
              </v-btn>
            </th>
            <td class="py-2">
              <pre>{{ JSON.stringify(zimfarmNotification.content, null, 2) }}</pre>
            </td>
          </tr>
        </tbody>
      </v-table>
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
import ZimfarmNotificationStatus from '@/components/ZimfarmNotificationStatus.vue'

const loadingStore = useLoadingStore()
const zimfarmNotificationStore = useZimfarmNotificationStore()
const notificationStore = useNotificationStore()

const error = ref<string | null>(null)
const zimfarmNotification = ref<ZimfarmNotification | null>(null)
const dataLoaded = ref(false)

interface Props {
  id: string
}

const props = withDefaults(defineProps<Props>(), {})

const loadData = async () => {
  loadingStore.startLoading('Fetching zimfarm notification...')

  const data = await zimfarmNotificationStore.fetchZimfarmNotification(props.id)
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
