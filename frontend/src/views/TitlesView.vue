<!-- View showing all titles -->

<template>
  <TitlesFilter v-if="ready" :filters="filters" @filters-changed="handleFiltersChange" />
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
    :show-filters="true"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
    @clear-filters="clearFilters"
    @selection-changed="handleSelectionChanged"
  />
  <div v-else class="d-flex align-center justify-center" style="height: 60vh">
    <v-progress-circular indeterminate size="70" width="7" color="primary" />
  </div>
</template>

<script setup lang="ts">
import TitlesFilter from '@/components/TitlesFilter.vue'
import TitlesTable from '@/components/TitlesTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import type { TitleLight } from '@/types/title'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

// Props

// Define headers for the table
const headers = [
  { title: 'Name', value: 'name' },
  { title: 'Category', value: 'category' },
  { title: 'Language', value: 'language' },
  { title: 'Offliner', value: 'offliner' },
  { title: 'Requested', value: 'requested' },
  { title: 'Last Task', value: 'last_task' },
]

// Reactive state
const titles = ref<TitleLight[]>([])
const paginator = computed(() => titleStore.paginator)

const ready = ref<boolean>(false)

const errors = ref<string[]>([])

const filters = ref({
  name: '',
})
const intervalId = ref<number | null>(null)
const selectedTitles = ref<string[]>([])

// Stores
const router = useRouter()
const titleStore = useTitleStore()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()

// Methods
async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching titles...')
  }
  await titleStore.fetchTitles(limit, skip, filters.value.name || undefined)

  titles.value = titleStore.titles
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
  await loadData(paginator.value.limit, 0)
}

async function handleLimitChange(newLimit: number) {
  titleStore.savePaginatorLimit(newLimit)
}

async function clearFilters() {
  filters.value = {
    name: '',
  }
  updateUrl()
  await loadData(paginator.value.limit, 0)
}

function handleSelectionChanged(newSelection: string[]) {
  selectedTitles.value = newSelection
}

function updateUrl() {
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  if (filters.value.name) {
    query.name = filters.value.name
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
}

// Lifecycle
onMounted(async () => {
  // Load filters from URL
  loadFiltersFromUrl()

  await loadData(paginator.value.limit, paginator.value.skip, true)

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
</script>
