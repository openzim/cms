<template>
  <div>
    <ApplicationsFilters
      :filters="filters"
      @filters-changed="handleFiltersChanged"
      @clear-filters="handleClearFilters"
    >
      <template #actions>
        <v-btn
          v-if="canCreateApplications"
          color="primary"
          variant="elevated"
          block
          @click="showCreateDialog = true"
        >
          <v-icon class="mr-2">mdi-plus</v-icon>
          Create Application
        </v-btn>
      </template>
    </ApplicationsFilters>

    <ApplicationsTable
      :headers="headers"
      :applications="applications"
      :paginator="paginator"
      :loading="loadingStore.isLoading"
      :loading-text="loadingStore.loadingText"
      :errors="applicationStore.errors"
      @limit-changed="handleLimitChange"
    />

    <CreateApplicationDialog v-model="showCreateDialog" @created="handleApplicationCreated" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ApplicationsFilters from '@/components/ApplicationsFilters.vue'
import ApplicationsTable from '@/components/ApplicationsTable.vue'
import CreateApplicationDialog from '@/components/CreateApplicationDialog.vue'
import { useApplicationStore } from '@/stores/application'
import { useAuthStore } from '@/stores/auth'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import type { Application } from '@/types/application'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const applicationStore = useApplicationStore()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()

const applications = ref<Application[]>([])
const filters = ref({ name: '', store: '' })
const showCreateDialog = ref(false)

const canCreateApplications = computed(() => authStore.hasPermission('application', 'create'))

const paginator = ref({
  page: Number(route.query.page) || 1,
  page_size: 50,
  skip: 0,
  limit: 50,
  count: 0,
})

const headers = [
  { title: 'Name', key: 'name', sortable: false },
  { title: 'Store', key: 'store', sortable: false },
  { title: 'Title', key: 'title_name', sortable: false },
  { title: 'Flavour', key: 'flavour', sortable: false },
  { title: 'Enabled', key: 'enabled', sortable: false },
]

const loadData = async (limit: number, skip: number) => {
  loadingStore.startLoading('Fetching applications...')

  const response = await applicationStore.fetchApplications(
    limit,
    skip,
    filters.value.name || undefined,
    filters.value.store || undefined,
  )

  if (response) {
    applications.value = response
    paginator.value = { ...applicationStore.paginator }
  } else {
    for (const error of applicationStore.errors) {
      notificationStore.showError(error)
    }
  }
  loadingStore.stopLoading()
}

const handleLimitChange = async (newLimit: number) => {
  if (paginator.value.page != 1) {
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

const handleFiltersChanged = (newFilters: { name: string; store: string }) => {
  filters.value = newFilters
  const query: Record<string, string> = {}
  if (newFilters.name) {
    query.name = newFilters.name
  }
  if (newFilters.store) {
    query.store = newFilters.store
  }
  router.push({
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

const handleClearFilters = () => {
  filters.value = { name: '', store: '' }
  router.push({ query: {} })
}

const handleApplicationCreated = (application: Application) => {
  notificationStore.showSuccess(`Application "${application.name}" has been created.`)
  router.push({
    name: 'app-detail',
    params: { id: application.id },
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
    filters.value = {
      name: query.name && typeof query.name === 'string' ? query.name : '',
      store: query.store && typeof query.store === 'string' ? query.store : '',
    }
    const newSkip = (page - 1) * paginator.value.limit
    await loadData(paginator.value.limit, newSkip)
  },
  { deep: true, immediate: true },
)
</script>
