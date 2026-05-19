<template>
  <TitlesFilter
    v-if="ready"
    :filters="filters"
    :collections="collectionNames"
    @filters-changed="handleFiltersChange"
    @clear-filters="clearFilters"
  >
    <template #actions>
      <v-btn
        v-if="!archived && canCreateTitle"
        color="primary"
        variant="elevated"
        block
        @click="showCreateDialog = true"
      >
        <v-icon class="mr-2">mdi-plus</v-icon>
        Create Title
      </v-btn>
    </template>
  </TitlesFilter>
  <template v-if="ready">
    <TitlesTable
      :headers="headers"
      :titles="titles"
      :paginator="paginator"
      :loading="loadingStore.isLoading"
      :loading-text="loadingStore.loadingText"
      :errors="errors"
      :filters="filters"
      :selected-titles="selectedTitles"
      :show-selection="props.showSelection"
      @limit-changed="handleLimitChange"
      @load-data="loadData"
      @selection-changed="handleSelectionChanged"
    >
      <template #actions>
        <slot
          name="actions"
          :selected-titles="selectedTitles"
          :restoring-text="restoringText"
          :handle-restore-titles="handleRestoreTitles"
          :archiving-text="archivingText"
          :handle-archive-titles="handleArchiveTitles"
        />
      </template>
    </TitlesTable>
    <div v-if="!archived && canAccessArchives" class="pa-0 mt-4">
      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            variant="outlined"
            size="small"
            :loading="loadingArchivedCount"
            @click="navigateToArchives"
          >
            <v-icon size="small" class="mr-2">mdi-archive</v-icon>
            {{ archivedCountText }}
          </v-btn>
        </template>
        <span>{{ archivedTooltipText }}</span>
      </v-tooltip>
    </div>
    <!-- Confirm Dialog for Restore Titles -->
    <ConfirmDialog
      v-model="showRestoreCommentDialog"
      title="Restore Titles"
      confirm-text="Restore"
      cancel-text="Cancel"
      confirm-color="success"
      message="Are you sure you want to restore the selected titles?"
      :max-width="600"
      icon="mdi-archive-arrow-up"
      icon-color="success"
      :loading="restoringText !== null"
      @confirm="handleRestoreConfirm"
      @cancel="handleRestoreCancel"
    />
    <!-- Confirm Dialog for Archive Titles -->
    <ConfirmDialog
      v-model="showArchiveDialog"
      title="Archive Titles"
      confirm-text="Archive"
      cancel-text="Cancel"
      confirm-color="warning"
      message="Are you sure you want to archive the selected titles?"
      :max-width="600"
      icon="mdi-archive"
      icon-color="warning"
      :loading="archivingText !== null"
      @confirm="handleArchiveConfirm"
      @cancel="handleArchiveCancel"
    />
  </template>

  <div v-else class="d-flex align-center justify-center" style="height: 60vh">
    <v-progress-circular indeterminate size="70" width="7" color="primary" />
  </div>

  <CreateTitleDialog v-if="!archived" v-model="showCreateDialog" @created="handleTitleCreated" />
</template>

<script setup lang="ts">
import CreateTitleDialog from '@/components/CreateTitleDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import TitlesFilter from '@/components/TitlesFilters.vue'
import TitlesTable from '@/components/TitlesTable.vue'
import { useAuthStore } from '@/stores/auth'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useCollectionsStore } from '@/stores/collections'
import type { TitleLight } from '@/types/title'
import type { Paginator } from '@/types/base'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

// Props
const props = withDefaults(
  defineProps<{
    routeName: string
    archived?: boolean
    showSelection?: boolean
  }>(),
  {
    archived: false,
    showSelection: false,
  },
)

// Define headers for the table
const headers = [
  { title: 'Name', value: 'name' },
  { title: 'Maturity', value: 'maturity' },
]

// Reactive state
const titles = ref<TitleLight[]>([])
const ready = ref<boolean>(false)
const errors = ref<string[]>([])
const filters = ref({
  name: '',
  collection_name: '',
})
const intervalId = ref<number | null>(null)
const selectedTitles = ref<string[]>([])
const showCreateDialog = ref(false)
const archivedCount = ref(0)
const loadingArchivedCount = ref(false)
const restoringText = ref<string | null>(null)
const showRestoreCommentDialog = ref<boolean>(false)
const archivingText = ref<string | null>(null)
const showArchiveDialog = ref<boolean>(false)

// Stores
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const titleStore = useTitleStore()
const collectionsStore = useCollectionsStore()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()

const collectionNames = computed(() => collectionsStore.collections.map((c) => c.name))

const paginator = ref<Paginator>({
  page: Number(route.query.page) || 1,
  page_size: titleStore.defaultLimit,
  skip: 0,
  limit: titleStore.defaultLimit,
  count: 0,
})

// Permissions
const canCreateTitle = computed(() => authStore.hasPermission('title', 'create'))
const canAccessArchives = computed(() => authStore.hasPermission('title', 'archive'))

const archivedCountText = computed(() => {
  if (loadingArchivedCount.value) {
    return 'Loading...'
  }
  const count = archivedCount.value
  return `ARCHIVES (${count})`
})

const archivedTooltipText = computed(() => {
  const count = archivedCount.value
  return count === 1 ? '1 matching archived title' : `${count} matching archived titles`
})

// Methods
async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (props.archived && !canAccessArchives.value) return

  if (!hideLoading) {
    loadingStore.startLoading('Fetching titles...')
  }
  await titleStore.fetchTitles(
    limit,
    skip,
    filters.value.name || undefined,
    filters.value.collection_name || undefined,
    props.archived,
  )

  titles.value = titleStore.titles
  paginator.value = titleStore.paginator
  titleStore.savePaginatorLimit(limit)
  errors.value = titleStore.errors
  for (const error of errors.value) {
    notificationStore.showError(error)
  }
  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

async function fetchArchivedCount(currentFilters: typeof filters.value) {
  if (!canAccessArchives.value) return

  loadingArchivedCount.value = true
  try {
    archivedCount.value = await titleStore.countTitles(
      currentFilters.name || undefined,
      currentFilters.collection_name || undefined,
      true,
    )
  } catch (error) {
    console.error('Failed to fetch archived count', error)
    archivedCount.value = 0
  } finally {
    loadingArchivedCount.value = false
  }
}

async function handleRestoreTitles() {
  if (!props.archived) {
    return
  }

  // Show comment dialog first
  showRestoreCommentDialog.value = true
}

async function handleRestoreConfirm() {
  restoringText.value = 'Restoring titles...'
  if (errors.value.length > 0) {
    notificationStore.showError('Not restored!')
    notificationStore.showError(`Unable to restore titles: ${errors.value.join(', ')}`)
  } else {
    const titleNames = selectedTitles.value.filter((name) => !!name)
    if (titleNames.length > 0) {
      const success = await titleStore.restoreTitles(titleNames)
      if (success) {
        notificationStore.showSuccess(
          `Exactly ${titleNames.length} selected title${
            titleNames.length !== 1 ? 's' : ''
          } have been restored`,
        )
        // Clear selections after successful restore
        selectedTitles.value = []
        await loadData(paginator.value.limit, paginator.value.skip)
      } else {
        for (const error of titleStore.errors) {
          notificationStore.showError(error)
        }
      }
    }
  }
  restoringText.value = null
}

function handleRestoreCancel() {
  restoringText.value = null
}

async function handleArchiveTitles() {
  if (props.archived) {
    return
  }
  showArchiveDialog.value = true
}

async function handleArchiveConfirm() {
  archivingText.value = 'Archiving titles...'
  const titleNames = selectedTitles.value.filter((name) => !!name)
  if (titleNames.length > 0) {
    const success = await titleStore.archiveTitles(titleNames)
    if (success) {
      notificationStore.showSuccess(
        `${titleNames.length} selected title${
          titleNames.length !== 1 ? 's' : ''
        } have been archived`,
      )
      selectedTitles.value = []
      await loadData(paginator.value.limit, paginator.value.skip)
      fetchArchivedCount(filters.value)
    } else {
      for (const error of titleStore.errors) {
        notificationStore.showError(error)
      }
    }
  }
  archivingText.value = null
}

function handleArchiveCancel() {
  archivingText.value = null
}

async function handleFiltersChange(newFilters: typeof filters.value) {
  filters.value = newFilters
  updateUrl()
  if (!props.archived) {
    fetchArchivedCount(newFilters)
  }
}

async function handleLimitChange(newLimit: number) {
  titleStore.savePaginatorLimit(newLimit)
  if (paginator.value.page !== 1) {
    paginator.value = {
      ...paginator.value,
      limit: newLimit,
      page: 1,
      skip: 0,
    }
  } else {
    await loadData(newLimit, 0)
  }
}

async function clearFilters() {
  filters.value = {
    name: '',
    collection_name: '',
  }
  updateUrl()
}

function handleSelectionChanged(newSelection: string[]) {
  selectedTitles.value = newSelection
}

async function handleTitleCreated() {
  notificationStore.showSuccess('Title created successfully')
  await loadData(paginator.value.limit, paginator.value.skip)
}

function updateUrl() {
  const query: Record<string, string | string[]> = {}

  if (filters.value.name) {
    query.name = filters.value.name
  }
  if (filters.value.collection_name) {
    query.collection_name = filters.value.collection_name
  }

  router.push({
    name: props.routeName,
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

function loadFiltersFromUrl() {
  const query = router.currentRoute.value.query

  if (query.name && typeof query.name === 'string') {
    filters.value.name = query.name
  }
  if (query.collection_name && typeof query.collection_name === 'string') {
    filters.value.collection_name = query.collection_name
  }
}

function navigateToArchives() {
  const query: Record<string, string | string[]> = {}

  if (filters.value.name) {
    query.name = filters.value.name
  }
  if (filters.value.collection_name) {
    query.collection_name = filters.value.collection_name
  }
  router.push({
    name: 'archived-titles',
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

// Lifecycle
onMounted(async () => {
  await collectionsStore.fetchCollections(100)
  loadFiltersFromUrl()
  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, true)
  }, 60000)

  // Fetch archived count on mount for regular titles view
  if (!props.archived) {
    fetchArchivedCount(filters.value)
  }

  // Mark as ready to show content - the table will handle initial load via updateOptions
  ready.value = true
})

onBeforeUnmount(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
})

// Watch for route changes to update filters
watch(
  () => router.currentRoute.value.query,
  () => {
    loadFiltersFromUrl()
  },
  { deep: true, immediate: true },
)

watch(
  () => router.currentRoute.value.query,
  async () => {
    const query = router.currentRoute.value.query
    let page = 1
    if (query.page && typeof query.page === 'string') {
      const parsedPage = parseInt(query.page, 10)
      if (!isNaN(parsedPage) && parsedPage > 1) {
        page = parsedPage
      }
    }
    const newSkip = (page - 1) * paginator.value.limit
    await loadData(paginator.value.limit, newSkip)
  },
  { deep: true, immediate: true },
)
</script>
