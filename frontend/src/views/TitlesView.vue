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
        v-if="canCreateTitle"
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
  <TitlesTable
    v-if="ready"
    :headers="headers"
    :titles="titles"
    :paginator="paginator"
    :loading="loadingStore.isLoading"
    :loading-text="loadingStore.loadingText"
    :errors="errors"
    :filters="filters"
    :selected-schedules="selectedTitles"
    :show-selection="true"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
    @selection-changed="handleSelectionChanged"
  />
  <div v-else class="d-flex align-center justify-center" style="height: 60vh">
    <v-progress-circular indeterminate size="70" width="7" color="primary" />
  </div>

  <CreateTitleDialog v-model="showCreateDialog" @created="handleTitleCreated" />
</template>

<script setup lang="ts">
import CreateTitleDialog from '@/components/CreateTitleDialog.vue'
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

// Methods
async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching titles...')
  }
  await titleStore.fetchTitles(
    limit,
    skip,
    filters.value.name || undefined,
    filters.value.collection_name || undefined,
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

async function handleFiltersChange(newFilters: typeof filters.value) {
  filters.value = newFilters
  updateUrl()
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
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  if (filters.value.name) {
    query.name = filters.value.name
  }
  if (filters.value.collection_name) {
    query.collection_name = filters.value.collection_name
  }

  router.push({
    name: 'titles',
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

// Lifecycle
onMounted(async () => {
  await collectionsStore.fetchCollections(100)
  // Load filters from URL
  loadFiltersFromUrl()
  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, true)
  }, 60000)

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
