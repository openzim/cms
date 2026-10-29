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
            v-if="publication.pr_url"
            size="x-small"
            variant="text"
            :href="publication.pr_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            Pull request
          </v-btn>
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
          <v-btn
            v-if="publication.events.length > 0 || publication.phase"
            size="x-small"
            variant="text"
            :icon="isExpanded(publication.id) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
            :aria-label="
              isExpanded(publication.id) ? 'Hide publication details' : 'Show publication details'
            "
            :aria-expanded="isExpanded(publication.id)"
            :aria-controls="`publication-details-${publication.id}`"
            @click="toggleExpanded(publication.id)"
          />
        </div>

        <v-expand-transition>
          <div
            v-if="isExpanded(publication.id)"
            :id="`publication-details-${publication.id}`"
            class="px-2 pb-2"
          >
            <EventsList v-if="publication.events.length > 0" :events="publication.events" />
            <div v-if="publication.phase" class="d-flex align-center ga-2">
              <v-progress-circular indeterminate size="12" width="2" />
              <span class="text-body-small">{{ phaseLabel(publication.phase) }}</span>
              <span
                v-if="publication.phase_started_at"
                class="text-body-small text-medium-emphasis"
              >
                since {{ formatDt(publication.phase_started_at, 'ff') }}
              </span>
            </div>
          </div>
        </v-expand-transition>

        <div v-if="publication.error" class="px-2 pb-2 text-body-small text-error">
          {{ publication.error }}
        </div>
      </v-card>
    </div>
    <span v-else class="text-body-small text-medium-emphasis">No publications yet.</span>

    <v-dialog v-model="showDuplicateDialog" max-width="520">
      <v-card>
        <v-card-title class="text-headline-small pa-4">Content already published</v-card-title>
        <v-card-text>
          <p>
            Version <strong>{{ duplicatePublication?.content_version }}</strong> was already
            published successfully
            <span v-if="duplicatePublication">
              on {{ formatDt(duplicatePublication.created_at, 'ff') }}
            </span>
            .
          </p>
          <p class="mt-2">Do you want to publish it again?</p>
          <v-btn
            v-if="duplicatePublication?.release_url"
            size="small"
            variant="text"
            :href="duplicatePublication.release_url"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-2"
          >
            View previous release
          </v-btn>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" @click="showDuplicateDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="elevated" @click="confirmDuplicatePublication">
            Publish anyway
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { usePublicationStore } from '@/stores/publication'
import { useNotificationStore } from '@/stores/notification'
import type {
  ApplicationPublication,
  PublicationPhase,
  PublicationStatus,
  PublicationStore,
} from '@/types/publication'
import EventsList from '@/components/EventsList.vue'
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
const showDuplicateDialog = ref(false)
const duplicatePublication = ref<ApplicationPublication | null>(null)
const expandedPublications = ref<Set<string>>(new Set())

const isExpanded = (id: string) => expandedPublications.value.has(id)

const toggleExpanded = (id: string) => {
  const next = new Set(expandedPublications.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedPublications.value = next
}

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

const phaseLabel = (phase: PublicationPhase) => {
  switch (phase) {
    case 'requested':
      return 'Preparing configuration changes'
    case 'checks':
      return 'Waiting for pull request checks'
    case 'merge':
      return 'Merging pull request'
    case 'release':
      return 'Creating release'
    case 'building':
      return `Building and uploading to ${storeLabel(props.store)}`
    case 'store':
      return `Waiting for ${storeLabel(props.store)} review`
    default:
      return phase
  }
}

const workflowUrl = (publication: ApplicationPublication) =>
  publication.run_url ?? `https://github.com/${publication.repository}/actions`

const load = async () => {
  if (!props.name) return
  const currentLoad = ++loadId
  const result = await publicationStore.fetchPublications(props.name, props.store)
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
    await load()
    schedulePoll()
  }, POLL_INTERVAL_MS)
}

onMounted(async () => {
  await load()
  schedulePoll()
})

watch(
  () => [props.name, props.store],
  async () => {
    stopPolling()
    await load()
    schedulePoll()
  },
)

onUnmounted(() => {
  unmounted = true
  stopPolling()
})

const publish = async () => {
  const result = await publicationStore.publish(props.titleId, {
    flavour: props.flavour,
    store: props.store,
  })
  if (result) {
    await load()
    schedulePoll()
  } else {
    notificationStore.showErrors(publicationStore.errors)
  }
}

const triggerPublication = async () => {
  publishing.value = true
  try {
    const check = await publicationStore.checkPublication(props.name, props.store)
    if (check === null) {
      notificationStore.showErrors(publicationStore.errors)
      return
    }
    if (check.published) {
      duplicatePublication.value = check.publication
      showDuplicateDialog.value = true
      return
    }
    await publish()
  } finally {
    publishing.value = false
  }
}

const confirmDuplicatePublication = async () => {
  showDuplicateDialog.value = false
  publishing.value = true
  try {
    await publish()
  } finally {
    publishing.value = false
  }
}
</script>
