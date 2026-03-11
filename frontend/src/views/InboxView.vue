<!-- Inbox View showing a list of books, zimfarm notifications, and events -->

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
  <EventFilters
    v-if="currentTab == 'events'"
    :filters="eventFilters"
    @filters-changed="handleEventFiltersChange"
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
    :show-filters="true"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
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
    @limit-changed="handleLimitChange"
    @load-data="loadData"
  />
  <EventTable
    v-show="currentTab == 'events'"
    :headers="headers"
    :events="events"
    :paginator="paginator"
    :loading="loadingStore.isLoading"
    :loading-text="loadingStore.loadingText"
    :errors="errors"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
  />
</template>

<script setup lang="ts">
import TabsList from '@/components/TabsList.vue'
import BookFilters from '@/components/BookFilters.vue'
import BookTable from '@/components/BookTable.vue'
import ZimfarmNotificationFilters from '@/components/ZimfarmNotificationFilters.vue'
import ZimfarmNotificationTable from '@/components/ZimfarmNotificationTable.vue'
import EventFilters from '@/components/EventFilters.vue'
import EventTable from '@/components/EventTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useBookStore } from '@/stores/book'
import { useZimfarmNotificationStore } from '@/stores/zimfarmNotification'
import { useEventStore } from '@/stores/event'
import type { BookLight } from '@/types/book'
import type { ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import type { EventLight } from '@/types/event'
import type { Paginator } from '@/types/base'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const bookStore = useBookStore()
const zimfarmNotificationStore = useZimfarmNotificationStore()
const eventStore = useEventStore()
const loadingStore = useLoadingStore()

// Filter options
const tabOptions = [
  { value: 'books', label: 'BOOKS' },
  { value: 'zimfarm_notifications', label: 'ZIMFARM NOTIFICATIONS' },
  { value: 'events', label: 'EVENTS' },
]

// Define headers for the table
const headers = computed(() => {
  switch (currentTab.value) {
    case 'books':
      return [
        { title: 'ID', value: 'id' },
        { title: 'Location', value: 'location_kind' },
        { title: 'Status', value: 'status' },
        { title: 'Deletion Date', value: 'deletion_date' },
      ]
    case 'zimfarm_notifications':
      return [
        { title: 'ID', value: 'id' },
        { title: 'Received', value: 'received_at' },
        { title: 'Status', value: 'status' },
      ]
    case 'events':
      return [
        { title: 'ID', value: 'id' },
        { title: 'Created', value: 'created_at' },
        { title: 'Topic', value: 'topic' },
      ]
    default:
      return []
  }
})

const currentTab = computed(() => {
  const tab = route.query.tab
  return (Array.isArray(tab) ? tab[0] : tab) || 'books'
})

const defaultLimit = computed(() => {
  switch (currentTab.value) {
    case 'books':
      return bookStore.defaultLimit
    case 'zimfarm_notifications':
      return zimfarmNotificationStore.defaultLimit
    case 'events':
      return eventStore.defaultLimit
    default:
      return 20
  }
})

const books = ref<BookLight[]>([])
const zimfarmNotifications = ref<ZimfarmNotificationLight[]>([])
const events = ref<EventLight[]>([])
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
    flag: '',
  }
  if (query.id && typeof query.id === 'string') {
    derived.id = query.id
  }

  if (query.location_kind && typeof query.location_kind === 'string') {
    derived.location_kind = query.location_kind
  }

  if (query.flag && typeof query.flag === 'string') {
    derived.flag = query.flag
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

const eventFilters = computed(() => {
  const query = router.currentRoute.value.query
  const derived = {
    topic: '',
  }
  if (query.topic && typeof query.topic === 'string') {
    derived.topic = query.topic
  }

  return derived
})

const intervalId = ref<number | null>(null)

const handleTabChange = (newTab: string) => {
  // Navigate to the new tab route
  router.push({
    query: {
      tab: newTab,
    },
  })
}

async function loadData(limit: number, skip: number, tab?: string, hideLoading: boolean = false) {
  if (!tab) {
    tab = currentTab.value
  }

  if (!hideLoading) {
    let loadingText = 'Fetching data...'
    switch (tab) {
      case 'books':
        loadingText = 'Fetching books...'
        break
      case 'zimfarm_notifications':
        loadingText = 'Fetching zimfarm notifications...'
        break
      case 'events':
        loadingText = 'Fetching events...'
        break
    }
    loadingStore.startLoading(loadingText)
    books.value = []
    zimfarmNotifications.value = []
    events.value = []
  }

  switch (tab) {
    case 'books':
      await bookStore.fetchBooks(
        limit,
        skip,
        true,
        bookFilters.value.id || undefined,
        bookFilters.value.location_kind ? [bookFilters.value.location_kind] : undefined,
        bookFilters.value.flag || undefined,
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
    case 'events':
      await eventStore.fetchEvents(limit, skip, eventFilters.value.topic || undefined)
      events.value = eventStore.events
      errors.value = eventStore.errors
      eventStore.savePaginatorLimit(limit)
      paginator.value = { ...eventStore.paginator }
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
    case 'events':
      eventStore.savePaginatorLimit(newLimit)
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
  sourceFilters: typeof bookFilters.value | typeof zimfarmFilters.value | typeof eventFilters.value,
) {
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  // Preserve the current tab
  if (currentTab.value) {
    query.tab = currentTab.value
  }

  if ('id' in sourceFilters && sourceFilters.id) {
    query.id = sourceFilters.id
  }

  if ('location_kind' in sourceFilters && sourceFilters.location_kind) {
    query.location_kind = sourceFilters.location_kind
  }

  if ('flag' in sourceFilters && sourceFilters.flag) {
    query.flag = sourceFilters.flag
  }

  if ('topic' in sourceFilters && sourceFilters.topic) {
    query.topic = sourceFilters.topic
  }

  router.push({
    name: route.name,
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

async function clearFilters() {
  switch (currentTab.value) {
    case 'books':
      updateUrlFilters({ id: '', location_kind: '', flag: '' })
      break
    case 'zimfarm_notifications':
      updateUrlFilters({ id: '' })
      break
    case 'events':
      updateUrlFilters({ topic: '' })
      break
  }
}

async function handleBookFiltersChange(newFilters: typeof bookFilters.value) {
  updateUrlFilters(newFilters)
}

async function handleZimfarmFiltersChange(newFilters: typeof zimfarmFilters.value) {
  updateUrlFilters(newFilters)
}

async function handleEventFiltersChange(newFilters: typeof eventFilters.value) {
  updateUrlFilters(newFilters)
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
