<template>
  <div>
    <v-card class="mb-4" flat>
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" sm="6">
            <v-select
              v-model="filterStatus"
              :items="statusFilterOptions"
              label="Status"
              variant="outlined"
              density="compact"
              clearable
              hide-details
              @update:model-value="handleFilterChange"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <TasksTable
      :headers="headers"
      :tasks="tasks"
      :paginator="paginator"
      :loading="loading"
      :loading-text="loadingText"
      :errors="requestedTaskStore.errors"
      @limit-changed="handleLimitChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import TasksTable from '@/components/TasksTable.vue'
import { useRequestedTaskStore } from '@/stores/requestedTask'
import { useNotificationStore } from '@/stores/notification'
import type { RequestedTaskLight } from '@/types/requestedTask'

interface Props {
  collectionId: string
}

const props = defineProps<Props>()

const router = useRouter()
const route = useRoute()
const requestedTaskStore = useRequestedTaskStore()
const notificationStore = useNotificationStore()

// Reactive data
const tasks = ref<RequestedTaskLight[]>([])
const filterStatus = ref<string | null>(null)
const loading = ref(false)
const loadingText = ref('Fetching tasks...')

const statusFilterOptions = [
  { title: 'All', value: null },
  { title: 'Requested', value: 'requested' },
  { title: 'Started', value: 'started' },
  { title: 'Running', value: 'running' },
  { title: 'Succeeded', value: 'succeeded' },
  { title: 'Failed', value: 'failed' },
  { title: 'Canceled', value: 'canceled' },
]

const paginator = ref({
  page: Number(route.query.page) || 1,
  page_size: requestedTaskStore.defaultLimit,
  skip: 0,
  limit: requestedTaskStore.defaultLimit,
  count: 0,
})

const headers = [
  { title: 'ID', key: 'id', sortable: false },
  { title: 'Status', key: 'status', sortable: false },
  { title: 'Requested By', key: 'requested_by', sortable: false },

  { title: 'Zimfarm', key: 'zimfarm_link', sortable: false },
]

// Maps a user-facing status filter to the list of API statuses to query
const statusGroupMap: Record<string, string[]> = {
  requested: ['requested'],
  started: ['started'],
  running: ['scraper_running'],
  succeeded: ['succeeded'],
  failed: ['failed'],
  canceled: ['canceled'],
}

const loadTasks = async (limit: number, skip: number) => {
  loading.value = true
  loadingText.value = 'Fetching tasks...'

  const status = filterStatus.value ? statusGroupMap[filterStatus.value] : null
  const response = await requestedTaskStore.fetchTasks(limit, skip, props.collectionId, status)

  if (response) {
    tasks.value = response
    paginator.value = { ...requestedTaskStore.paginator }
    requestedTaskStore.savePaginatorLimit(limit)
  } else {
    for (const error of requestedTaskStore.errors) {
      notificationStore.showError(error)
    }
  }
  loading.value = false
}

const handleLimitChange = async (newLimit: number) => {
  requestedTaskStore.savePaginatorLimit(newLimit)
  if (paginator.value.page != 1) {
    paginator.value = {
      ...paginator.value,
      limit: newLimit,
      page: 1,
      skip: 0,
    }
  } else {
    await loadTasks(newLimit, 0)
  }
}

const handleFilterChange = async () => {
  const query: Record<string, string> = {}
  if (filterStatus.value) {
    query.status = filterStatus.value
  }
  router.push({
    query: Object.keys(query).length > 0 ? query : undefined,
  })
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
    // Sync status from URL
    if (query.status && typeof query.status === 'string') {
      filterStatus.value = query.status
    } else {
      filterStatus.value = null
    }
    const newSkip = (page - 1) * paginator.value.limit
    await loadTasks(paginator.value.limit, newSkip)
  },
  { deep: true, immediate: true },
)
</script>
