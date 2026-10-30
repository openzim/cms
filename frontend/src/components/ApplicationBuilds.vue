<template>
  <div v-if="(canBuild && enabled) || builds.length > 0" class="mb-4">
    <div class="d-flex align-center flex-wrap ga-2 mb-2">
      <span class="text-title-small">{{ storeLabel(store) }} builds</span>
    </div>

    <v-alert v-if="canBuild && !enabled" type="info" density="compact" variant="tonal" class="mb-2">
      This application is not enabled for build.
    </v-alert>

    <v-alert v-if="errors.length > 0" type="error" density="compact" variant="tonal" class="mb-2">
      {{ errors.join(', ') }}
    </v-alert>

    <div v-if="builds.length > 0" class="d-flex flex-column ga-2">
      <v-card v-for="build in builds" :key="build.id" variant="outlined" density="compact">
        <div class="d-flex flex-wrap align-center ga-2 px-2 pt-2">
          <v-chip size="small" variant="tonal" :color="statusColor(build.status)">
            <v-progress-circular
              v-if="isOngoing(build)"
              indeterminate
              size="12"
              width="2"
              class="mr-1"
            />
            {{ statusLabel(build.status) }}
          </v-chip>
          <span class="text-body-medium">v{{ build.content_version }}</span>
          <span class="text-body-small text-medium-emphasis">
            {{ formatDt(build.created_at, 'ff') }}
          </span>
          <span v-if="build.requested_by" class="text-body-small text-medium-emphasis">
            by {{ build.requested_by }}
          </span>

          <div class="d-flex flex-wrap align-center ga-1 ms-auto">
            <v-btn
              v-if="build.pr_url"
              size="x-small"
              variant="text"
              :href="build.pr_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              Pull request
            </v-btn>
            <v-btn
              v-if="build.release_url"
              size="x-small"
              variant="text"
              :href="build.release_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              Release
            </v-btn>
            <v-btn
              size="x-small"
              variant="text"
              :href="workflowUrl(build)"
              target="_blank"
              rel="noopener noreferrer"
            >
              {{ build.run_url ? 'Workflow run' : 'Actions' }}
            </v-btn>
            <v-btn
              v-if="build.events.length > 0 || build.phase"
              size="x-small"
              variant="text"
              :icon="isExpanded(build.id) ? 'mdi-chevron-up' : 'mdi-chevron-down'"
              :aria-label="isExpanded(build.id) ? 'Hide build details' : 'Show build details'"
              :aria-expanded="isExpanded(build.id)"
              :aria-controls="`build-details-${build.id}`"
              @click="toggleExpanded(build.id)"
            />
          </div>
        </div>

        <v-expand-transition>
          <div v-if="isExpanded(build.id)" :id="`build-details-${build.id}`" class="px-2 pb-2">
            <EventsList v-if="build.events.length > 0" :events="build.events" />
            <div v-if="build.phase" class="d-flex align-center ga-2">
              <v-progress-circular indeterminate size="12" width="2" />
              <span class="text-body-small">{{ phaseLabel(build.phase) }}</span>
              <span v-if="build.phase_started_at" class="text-body-small text-medium-emphasis">
                since {{ formatDt(build.phase_started_at, 'ff') }}
              </span>
            </div>
          </div>
        </v-expand-transition>

        <div v-if="build.error" class="px-2 pb-2 text-body-small text-error">
          {{ build.error }}
        </div>
      </v-card>
    </div>
    <span v-else class="text-body-small text-medium-emphasis">No builds yet.</span>

    <v-dialog v-model="showDuplicateDialog" max-width="520">
      <v-card>
        <v-card-title class="text-headline-small pa-4">Content already built</v-card-title>
        <v-card-text>
          <p>
            Version <strong>{{ duplicateBuild?.content_version }}</strong> was already built
            successfully
            <span v-if="duplicateBuild"> on {{ formatDt(duplicateBuild.created_at, 'ff') }} </span>
            .
          </p>
          <p class="mt-2">Do you want to build it again?</p>
          <v-btn
            v-if="duplicateBuild?.release_url"
            size="small"
            variant="text"
            :href="duplicateBuild.release_url"
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
          <v-btn color="primary" variant="elevated" @click="confirmDuplicateBuild">
            Build anyway
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { useAppBuildStore } from '@/stores/appBuild'
import { useNotificationStore } from '@/stores/notification'
import type {
  ApplicationBuild,
  AppBuildPhase,
  AppBuildStatus,
  ApplicationStore,
} from '@/types/appBuild'
import EventsList from '@/components/EventsList.vue'
import { formatDt, storeLabel } from '@/utils/format'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

interface Props {
  titleId: string
  flavour: string
  name: string
  store: ApplicationStore
  enabled: boolean
  canBuild: boolean
}

const props = defineProps<Props>()

const POLL_INTERVAL_MS = 10_000

const appBuildStore = useAppBuildStore()
const notificationStore = useNotificationStore()
const builds = ref<ApplicationBuild[]>([])
const errors = ref<string[]>([])
const building = ref(false)
const showDuplicateDialog = ref(false)
const duplicateBuild = ref<ApplicationBuild | null>(null)
const expandedBuilds = ref<Set<string>>(new Set())

const isExpanded = (id: string) => expandedBuilds.value.has(id)

const toggleExpanded = (id: string) => {
  const next = new Set(expandedBuilds.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedBuilds.value = next
}

let pollTimer: ReturnType<typeof setTimeout> | null = null
let loadId = 0
let unmounted = false

const isOngoing = (build: ApplicationBuild) =>
  build.status === 'pending' || build.status === 'running'

const hasOngoing = computed(() => builds.value.some(isOngoing))

const statusLabel = (status: AppBuildStatus) => {
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

const statusColor = (status: AppBuildStatus) => {
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

const phaseLabel = (phase: AppBuildPhase) => {
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
    case 'uploaded':
      return `Uploaded to ${storeLabel(props.store)}; awaiting review`
    default:
      return phase
  }
}

const workflowUrl = (build: ApplicationBuild) =>
  build.run_url ?? `https://github.com/${build.repository}/actions`

const load = async () => {
  if (!props.name) return
  const currentLoad = ++loadId
  const result = await appBuildStore.fetchBuilds(props.name, props.store)
  if (currentLoad !== loadId) return
  errors.value = appBuildStore.errors
  if (result !== null) {
    builds.value = result
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

const build = async () => {
  const result = await appBuildStore.build(props.titleId, {
    flavour: props.flavour,
    store: props.store,
  })
  if (result) {
    await load()
    schedulePoll()
  } else {
    notificationStore.showErrors(appBuildStore.errors)
  }
}

const triggerBuild = async () => {
  building.value = true
  try {
    const check = await appBuildStore.checkBuild(props.name, props.store)
    if (check === null) {
      notificationStore.showErrors(appBuildStore.errors)
      return
    }
    if (check.built) {
      duplicateBuild.value = check.app_build
      showDuplicateDialog.value = true
      return
    }
    await build()
  } finally {
    building.value = false
  }
}

const confirmDuplicateBuild = async () => {
  showDuplicateDialog.value = false
  building.value = true
  try {
    await build()
  } finally {
    building.value = false
  }
}

defineExpose({ build: triggerBuild, building, hasOngoing })
</script>
