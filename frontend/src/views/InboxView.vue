<!-- Pipeline View showing a list of tasks -->

<template>
  <TabsList :active-tab="activeTab" :tab-options="tabOptions" @tab-changed="handleTabChange" />
  <ZimfarmNotificationFilters
    v-if="activeTab == 'zimfarm_notifications'"
    :filters="filters"
    @filters-changed="handleFiltersChange"
  />
  <ZimfarmNotificationTable
    v-show="ready && activeTab == 'zimfarm_notifications'"
    :headers="headers"
    :zimfarm-notifications="zimfarmNotifications"
    :paginator="paginator"
    :loading="loadingStore.isLoading"
    :loading-text="loadingStore.loadingText"
    :errors="errors"
    :filters="filters"
    :selected-zimfarm-notifications="selectedZimfarmNotifications"
    :show-selection="true"
    :show-filters="true"
    @limit-changed="handleLimitChange"
    @load-data="loadData"
    @clear-filters="clearFilters"
    @selection-changed="handleSelectionChanged"
  />
  <div v-if="!ready" class="d-flex align-center justify-center" style="height: 60vh">
    <v-progress-circular indeterminate size="70" width="7" color="primary" />
  </div>
</template>

<script setup lang="ts">
import TabsList from '@/components/TabsList.vue'
import ZimfarmNotificationFilters from '@/components/ZimfarmNotificationFilters.vue'
import ZimfarmNotificationTable from '@/components/ZimfarmNotificationTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useZimfarmNotificationStore } from '@/stores/zimfarmNotification'
import type { ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

// Define headers for the table
const headers = computed(() => {
  switch (activeTab.value) {
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

const paginator = computed(() => {
  switch (activeTab.value) {
    case 'zimfarm_notifications':
      return zimfarmNotificationStore.paginator
    default:
      return zimfarmNotificationStore.paginator
  }
})

// Filter options
const tabOptions = [
  { value: 'books', label: 'BOOKS' },
  { value: 'zimfarm_notifications', label: 'ZIMFARM NOTIFICATIONS' },
]

const props = withDefaults(
  defineProps<{
    activeTab?: string
  }>(),
  {
    activeTab: new URLSearchParams(window.location.search).get('tab') || 'books',
  },
)

const ready = ref<boolean>(false)
const zimfarmNotifications = ref<ZimfarmNotificationLight[]>([])
const errors = ref<string[]>([])
const filters = ref({
  id: '',
})
const intervalId = ref<number | null>(null)
const selectedZimfarmNotifications = ref<string[]>([])

const router = useRouter()

const zimfarmNotificationStore = useZimfarmNotificationStore()
const loadingStore = useLoadingStore()

const activeTab = ref(props.activeTab)

const handleTabChange = (newTab: string) => {
  activeTab.value = newTab

  // Navigate to the new tab route
  router.push({
    query: {
      ...router.currentRoute.value.query,
      tab: newTab,
    },
  })
}

async function handleLimitChange(newLimit: number) {
  switch (activeTab.value) {
    case 'zimfarm_notifications':
      zimfarmNotificationStore.savePaginatorLimit(newLimit)
      break
  }
}

async function clearFilters() {
  filters.value = {
    id: '',
  }
  await loadData(paginator.value.limit, 0)
}

async function handleFiltersChange(newFilters: typeof filters.value) {
  filters.value = newFilters
  await loadData(paginator.value.limit, 0)
}

function handleSelectionChanged(newSelection: string[]) {
  switch (activeTab.value) {
    case 'zimfarm_notifications':
      selectedZimfarmNotifications.value = newSelection
  }
}

// Watch for filter changes and load data
watch(activeTab, async (newTab) => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
  await loadData(paginator.value.limit, paginator.value.skip, newTab)
  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, activeTab.value, true)
  }, 60000)
})

async function loadData(limit: number, skip: number, tab?: string, hideLoading: boolean = false) {
  if (!tab) {
    tab = activeTab.value
  }

  ready.value = false
  zimfarmNotifications.value = []

  switch (tab) {
    case 'zimfarm_notifications':
      if (!hideLoading) {
        loadingStore.startLoading('Fetching zimfarm notifications...')
      }
      await zimfarmNotificationStore.fetchZimfarmNotifications(
        limit,
        skip,
        false,
        undefined,
        undefined,
        undefined,
        undefined,
        filters.value.id || undefined,
      )
      zimfarmNotifications.value = zimfarmNotificationStore.zimfarmNotifications
      errors.value = zimfarmNotificationStore.errors
      zimfarmNotificationStore.savePaginatorLimit(limit)
      break
    case 'books':
      break
    default:
      throw new Error(`Invalid filter: ${tab}`)
  }

  ready.value = true
  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

onMounted(async () => {
  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, activeTab.value, true)
  }, 60000)
})

onBeforeUnmount(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
})
</script>
