<!-- Inbox View showing a list of books and zimfarm notifications -->

<template>
  <TabsList :active-tab="currentTab" :tab-options="tabOptions" @tab-changed="handleTabChange" />
  <BookFilters
    v-if="currentTab == 'books'"
    :filters="bookFilters"
    :location-kind-options="['quarantine', 'staging']"
    @filters-changed="handleBookFiltersChange"
    @clear-filters="clearFilters"
  />
  <ZimfarmNotificationFilters
    v-if="currentTab == 'zimfarm_notifications'"
    :filters="zimfarmFilters"
    @filters-changed="handleZimfarmFiltersChange"
    @clear-filters="clearFilters"
  />
  <BookTable
    v-show="currentTab == 'books'"
    :headers="headers"
    :books="books"
    :paginator="paginator"
    :loading="loadingStore.isLoading"
    :loading-text="loadingStore.loadingText"
    :errors="errors"
    :filters="bookFilters"
    :selected-books="selectedBooks"
    :show-selection="true"
    :show-filters="true"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
    @selection-changed="handleSelectionChanged"
  />
  <ZimfarmNotificationTable
    v-show="currentTab == 'zimfarm_notifications'"
    :headers="headers"
    :zimfarm-notifications="zimfarmNotifications"
    :paginator="paginator"
    :loading="loadingStore.isLoading"
    :loading-text="loadingStore.loadingText"
    :errors="errors"
    :filters="zimfarmFilters"
    :selected-zimfarm-notifications="selectedZimfarmNotifications"
    :show-selection="true"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
    @selection-changed="handleSelectionChanged"
  />
</template>

<script setup lang="ts">
import TabsList from '@/components/TabsList.vue'
import BookFilters from '@/components/BookFilters.vue'
import BookTable from '@/components/BookTable.vue'
import ZimfarmNotificationFilters from '@/components/ZimfarmNotificationFilters.vue'
import ZimfarmNotificationTable from '@/components/ZimfarmNotificationTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useBookStore } from '@/stores/book'
import { useZimfarmNotificationStore } from '@/stores/zimfarmNotification'
import type { BookLight } from '@/types/book'
import type { ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import type { Paginator } from '@/types/base'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const bookStore = useBookStore()
const zimfarmNotificationStore = useZimfarmNotificationStore()
const loadingStore = useLoadingStore()

// Filter options
const tabOptions = [
  { value: 'books', label: 'BOOKS' },
  { value: 'zimfarm_notifications', label: 'ZIMFARM NOTIFICATIONS' },
]

// Define headers for the table
const headers = computed(() => {
  switch (currentTab.value) {
    case 'books':
      return [
        { title: 'ID', value: 'id' },
        { title: 'Location', value: 'location_kind' },
        { title: 'Status', value: 'status' },
      ]
    case 'zimfarm_notifications':
      return [
        { title: 'ID', value: 'id' },
        { title: 'Received', value: 'received_at' },
        { title: 'Status', value: 'status' },
      ]
    default:
      return []
  }
})

const currentTab = computed(() => {
  const tab = route.query.tab
  return (Array.isArray(tab) ? tab[0] : tab) || 'books'
})

const defaultLimit = computed(() =>
  currentTab.value == 'book' ? bookStore.defaultLimit : zimfarmNotificationStore.defaultLimit,
)

const books = ref<BookLight[]>([])
const zimfarmNotifications = ref<ZimfarmNotificationLight[]>([])
const paginator = ref<Paginator>({
  page: Number(route.query.page) || 1,
  page_size: defaultLimit.value,
  skip: 0,
  limit: defaultLimit.value,
  count: 0,
})
const errors = ref<string[]>([])

const bookFilters = computed(() => {
  const query = router.currentRoute.value.query
  const derived = {
    location_kind: '',
    id: '',
  }
  if (query.id && typeof query.id === 'string') {
    derived.id = query.id
  }

  if (query.location_kind && typeof query.location_kind === 'string') {
    derived.location_kind = query.location_kind
  }

  return derived
})

const zimfarmFilters = computed(() => {
  const query = router.currentRoute.value.query
  const derived = {
    id: '',
  }
  if (query.id && typeof query.id === 'string') {
    derived.id = query.id
  }

  return derived
})

const intervalId = ref<number | null>(null)
const selectedBooks = ref<string[]>([])
const selectedZimfarmNotifications = ref<string[]>([])

const handleTabChange = (newTab: string) => {
  // Navigate to the new tab route
  router.push({
    query: {
      tab: newTab,
    },
  })
}

// Clear selections when switching tabs
watch(currentTab, () => {
  selectedBooks.value = []
  selectedZimfarmNotifications.value = []
})

async function loadData(limit: number, skip: number, tab?: string, hideLoading: boolean = false) {
  if (!tab) {
    tab = currentTab.value
  }

  if (!hideLoading) {
    loadingStore.startLoading(
      tab === 'books' ? 'Fetching books...' : 'Fetching zimfarm notifications...',
    )
    books.value = []
    zimfarmNotifications.value = []
  }

  switch (tab) {
    case 'books':
      await bookStore.fetchBooks(
        limit,
        skip,
        false,
        bookFilters.value.id || undefined,
        bookFilters.value.location_kind || undefined,
      )
      books.value = bookStore.books
      errors.value = bookStore.errors
      bookStore.savePaginatorLimit(limit)
      paginator.value = { ...bookStore.paginator }
      break
    case 'zimfarm_notifications':
      await zimfarmNotificationStore.fetchZimfarmNotifications(
        limit,
        skip,
        false,
        undefined,
        undefined,
        undefined,
        zimfarmFilters.value.id || undefined,
      )
      zimfarmNotifications.value = zimfarmNotificationStore.zimfarmNotifications
      errors.value = zimfarmNotificationStore.errors
      zimfarmNotificationStore.savePaginatorLimit(limit)
      paginator.value = { ...zimfarmNotificationStore.paginator }
      break
    default:
      throw new Error(`Invalid tab: ${tab}`)
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

async function handleLimitChange(newLimit: number) {
  switch (currentTab.value) {
    case 'books':
      bookStore.savePaginatorLimit(newLimit)
      break
    case 'zimfarm_notifications':
      zimfarmNotificationStore.savePaginatorLimit(newLimit)
      break
  }

  if (paginator.value.page != 1) {
    paginator.value = {
      ...paginator.value,
      limit: newLimit,
      page: 1,
      skip: 0,
    }
  } else {
    await loadData(newLimit, 0, currentTab.value)
  }
}

function updateUrlFilters(
  sourceFilters: typeof bookFilters.value | typeof ZimfarmNotificationFilters.value,
) {
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  // Preserve the current tab
  if (currentTab.value) {
    query.tab = currentTab.value
  }

  if (sourceFilters.id) {
    query.id = sourceFilters.id
  }

  if (sourceFilters.location_kind) {
    query.location_kind = sourceFilters.location_kind
  }

  router.push({
    name: route.name,
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

async function clearFilters() {
  switch (currentTab.value) {
    case 'books':
      updateUrlFilters({ id: '', location_kind: '' })
      break
    case 'zimfarm_notifications':
      updateUrlFilters({ id: '' })
      break
  }
}

async function handleBookFiltersChange(newFilters: typeof bookFilters.value) {
  updateUrlFilters(newFilters)
}

async function handleZimfarmFiltersChange(newFilters: typeof zimfarmFilters.value) {
  updateUrlFilters(newFilters)
}

function handleSelectionChanged(newSelection: string[]) {
  switch (currentTab.value) {
    case 'books':
      selectedBooks.value = newSelection
      break
    case 'zimfarm_notifications':
      selectedZimfarmNotifications.value = newSelection
      break
  }
}

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

onMounted(async () => {
  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, currentTab.value, true)
  }, 60000)
})

onBeforeUnmount(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
})
</script>
