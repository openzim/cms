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

    <TitleUploadsTable
      :headers="headers"
      :title-uploads="titleUploads"
      :paginator="paginator"
      :loading="loading"
      :loading-text="loadingText"
      :errors="titleUploadStore.errors"
      @limit-changed="handleLimitChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import TitleUploadsTable from '@/components/TitleUploadsTable.vue'
import { useTitleUploadStore } from '@/stores/titleUpload'
import { useNotificationStore } from '@/stores/notification'
import type { TitleUploadLight } from '@/types/titleUpload'

interface Props {
  titleId: string
}

const props = defineProps<Props>()

const router = useRouter()
const route = useRoute()
const titleUploadStore = useTitleUploadStore()
const notificationStore = useNotificationStore()

// Reactive data
const titleUploads = ref<TitleUploadLight[]>([])
const filterStatus = ref<string | null>(null)
const loading = ref(false)
const loadingText = ref('Fetching title uploads...')

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
  page_size: titleUploadStore.defaultLimit,
  skip: 0,
  limit: titleUploadStore.defaultLimit,
  count: 0,
})

const headers = [
  { title: 'Upload', key: 'id', sortable: false },
  { title: 'Requested By', key: 'requested_by', sortable: false },
]

const intervalId = ref<number | null>(null)

// Maps a user-facing status filter to the list of API statuses to query
const statusGroupMap: Record<string, string[]> = {
  requested: ['requested'],
  started: ['started'],
  running: ['scraper_running'],
  succeeded: ['succeeded'],
  failed: ['failed'],
  canceled: ['canceled'],
}

const loadTitleUploads = async (limit: number, skip: number, hideLoading: boolean = false) => {
  if (!hideLoading) {
    loading.value = true
    loadingText.value = 'Fetching title uploads...'
  }

  const status = filterStatus.value ? statusGroupMap[filterStatus.value] : null
  const response = await titleUploadStore.fetchTitleUploads(limit, skip, props.titleId, status)

  if (response) {
    titleUploads.value = response
    paginator.value = { ...titleUploadStore.paginator }
    titleUploadStore.savePaginatorLimit(limit)
  } else {
    for (const error of titleUploadStore.errors) {
      notificationStore.showError(error)
    }
  }
  loading.value = false
}

const handleLimitChange = async (newLimit: number) => {
  titleUploadStore.savePaginatorLimit(newLimit)
  if (paginator.value.page != 1) {
    paginator.value = {
      ...paginator.value,
      limit: newLimit,
      page: 1,
      skip: 0,
    }
  } else {
    await loadTitleUploads(newLimit, 0)
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

const refresh = async () => {
  await loadTitleUploads(paginator.value.limit, paginator.value.skip)
}

defineExpose({
  refresh,
})

onMounted(async () => {
  intervalId.value = window.setInterval(async () => {
    await loadTitleUploads(paginator.value.limit, paginator.value.skip, true)
  }, 60000)
})

onBeforeUnmount(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
})

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
    await loadTitleUploads(paginator.value.limit, newSkip)
  },
  { deep: true, immediate: true },
)
</script>
