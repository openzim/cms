<template>
  <div v-if="(canPublish && enabled) || publications.length > 0" class="mb-4">
    <div class="d-flex align-center flex-wrap ga-2 mb-2">
      <span class="text-title-small">{{ storeLabel(store) }} publications</span>
      <v-spacer />
      <v-btn
        v-if="canPublish"
        size="small"
        color="primary"
        variant="tonal"
        :prepend-icon="store === 'android' ? 'mdi-android' : 'mdi-apple'"
        :loading="publishing"
        :disabled="!enabled || publishing || hasOngoing"
        @click="triggerPublication"
      >
        Publish to {{ storeLabel(store) }}
      </v-btn>
    </div>

    <v-alert
      v-if="canPublish && !enabled"
      type="info"
      density="compact"
      variant="tonal"
      class="mb-2"
    >
      This application is not enabled for publication.
    </v-alert>

    <v-alert v-if="errors.length > 0" type="error" density="compact" variant="tonal" class="mb-2">
      {{ errors.join(', ') }}
    </v-alert>

    <div v-if="publications.length > 0" class="d-flex flex-column ga-2">
      <v-card
        v-for="publication in publications"
        :key="publication.id"
        variant="outlined"
        density="compact"
      >
        <div class="d-flex flex-wrap align-center ga-2 pa-2">
          <v-chip size="small" variant="tonal" :color="statusColor(publication.status)">
            <v-progress-circular
              v-if="isOngoing(publication)"
              indeterminate
              size="12"
              width="2"
              class="mr-1"
            />
            {{ statusLabel(publication.status) }}
          </v-chip>
          <span class="text-body-medium">v{{ publication.content_version }}</span>
          <span class="text-body-small text-medium-emphasis">
            {{ formatDt(publication.created_at, 'ff') }}
          </span>
          <span v-if="publication.requested_by" class="text-body-small text-medium-emphasis">
            by {{ publication.requested_by }}
          </span>
          <v-spacer />
          <v-btn
            v-if="publication.release_url"
            size="x-small"
            variant="text"
            :href="publication.release_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            Release
          </v-btn>
          <v-btn
            size="x-small"
            variant="text"
            :href="workflowUrl(publication)"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ publication.run_url ? 'Workflow run' : 'Actions' }}
          </v-btn>
        </div>
        <div v-if="publication.error" class="px-2 pb-2 text-body-small text-error">
          {{ publication.error }}
        </div>
      </v-card>
    </div>
    <span v-else class="text-body-small text-medium-emphasis">No publications yet.</span>
  </div>
</template>

<script setup lang="ts">
import { usePublicationStore } from '@/stores/publication'
import { useNotificationStore } from '@/stores/notification'
import type {
  ApplicationPublication,
  PublicationStatus,
  PublicationStore,
} from '@/types/publication'
import { formatDt, storeLabel } from '@/utils/format'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

interface Props {
  titleId: string
  flavour: string
  name: string
  store: PublicationStore
  enabled: boolean
  canPublish: boolean
}

const props = defineProps<Props>()

const POLL_INTERVAL_MS = 10_000

const publicationStore = usePublicationStore()
const notificationStore = useNotificationStore()
const publications = ref<ApplicationPublication[]>([])
const errors = ref<string[]>([])
const publishing = ref(false)

let pollTimer: ReturnType<typeof setTimeout> | null = null
let loadId = 0
let unmounted = false

const isOngoing = (publication: ApplicationPublication) =>
  publication.status === 'pending' || publication.status === 'running'

const hasOngoing = computed(() => publications.value.some(isOngoing))

const statusLabel = (status: PublicationStatus) => {
  switch (status) {
    case 'pending':
      return 'Queued'
    case 'running':
      return 'Running'
    case 'success':
      return 'Succeeded'
    case 'failure':
      return 'Failed'
    case 'cancelled':
      return 'Cancelled'
    default:
      return status
  }
}

const statusColor = (status: PublicationStatus) => {
  switch (status) {
    case 'success':
      return 'success'
    case 'failure':
      return 'error'
    case 'cancelled':
      return 'grey'
    case 'running':
      return 'info'
    default:
      return 'warning'
  }
}

const workflowUrl = (publication: ApplicationPublication) =>
  publication.run_url ?? `https://github.com/${publication.repository}/actions`

const load = async (refresh: boolean) => {
  if (!props.name) return
  const currentLoad = ++loadId
  const result = await publicationStore.fetchPublications(props.name, props.store, refresh)
  if (currentLoad !== loadId) return
  errors.value = publicationStore.errors
  if (result !== null) {
    publications.value = result
  }
}

const stopPolling = () => {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

const schedulePoll = () => {
  stopPolling()
  if (unmounted || !hasOngoing.value) return
  pollTimer = setTimeout(async () => {
    pollTimer = null
    await load(true)
    schedulePoll()
  }, POLL_INTERVAL_MS)
}

onMounted(async () => {
  await load(true)
  schedulePoll()
})

watch(
  () => [props.name, props.store],
  async () => {
    stopPolling()
    await load(true)
    schedulePoll()
  },
)

onUnmounted(() => {
  unmounted = true
  stopPolling()
})

const triggerPublication = async () => {
  publishing.value = true
  try {
    const result = await publicationStore.publish(props.titleId, {
      flavour: props.flavour,
      store: props.store,
    })
    if (result) {
      await load(true)
      schedulePoll()
    } else {
      notificationStore.showErrors(publicationStore.errors)
    }
  } finally {
    publishing.value = false
  }
}
</script>
