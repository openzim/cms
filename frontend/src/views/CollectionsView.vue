<template>
  <div>
    <v-card class="mb-4" flat>
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" sm="8">
            <v-text-field
              v-model="searchCollection"
              label="Search collection"
              placeholder="Enter collection name to search"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @blur="handleSearchChange"
              @keyup.enter="handleSearchChange"
              @click:clear="handleSearchChange"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-btn
              v-if="canCreateCollections"
              color="primary"
              variant="elevated"
              block
              @click="showCreateDialog = true"
            >
              <v-icon class="mr-2">mdi-plus</v-icon>
              Create Collection
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <CollectionsTable
      :headers="headers"
      :collections="collections"
      :paginator="paginator"
      :loading="loadingStore.isLoading"
      :loading-text="loadingStore.loadingText"
      :errors="collectionStore.errors"
      @limit-changed="handleLimitChange"
    />

    <CollectionFormDialog v-model="showCreateDialog" @created="handleCollectionCreated" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import CollectionFormDialog from '@/components/CollectionFormDialog.vue'
import CollectionsTable from '@/components/CollectionsTable.vue'
import { useAuthStore } from '@/stores/auth'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useCollectionsStore } from '@/stores/collections'
import type { CollectionLight } from '@/types/collections'

// Router and stores
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()
const collectionStore = useCollectionsStore()

// Reactive data
const collections = ref<CollectionLight[]>([])
const searchCollection = ref<string>('')
const showCreateDialog = ref(false)

const paginator = ref({
  page: Number(route.query.page) || 1,
  page_size: collectionStore.defaultLimit,
  skip: 0,
  limit: collectionStore.defaultLimit,
  count: 0,
})

// Permissions
const canCreateCollections = computed(() => authStore.hasPermission('collection', 'create'))

// Table headers
const headers = [
  { title: 'Name', key: 'name', sortable: false },
  { title: 'Paths', key: 'paths', sortable: false },
]

// Methods
const handleCollectionCreated = async (name: string) => {
  notificationStore.showSuccess(`Collection "${name}" has been created.`)
  await loadData(paginator.value.limit, paginator.value.skip)
}

const loadData = async (limit: number, skip: number) => {
  loadingStore.startLoading('Fetching collections...')

  const response = await collectionStore.fetchCollections(
    limit,
    skip,
    searchCollection.value || undefined,
  )

  if (response) {
    collections.value = response
    paginator.value = { ...collectionStore.paginator }
    collectionStore.savePaginatorLimit(limit)
  } else {
    for (const error of collectionStore.errors) {
      notificationStore.showError(error)
    }
  }
  loadingStore.stopLoading()
}

const handleLimitChange = async (newLimit: number) => {
  collectionStore.savePaginatorLimit(newLimit)
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

const handleSearchChange = async () => {
  const query: Record<string, string> = {}
  if (searchCollection.value) {
    query.name = searchCollection.value
  }
  router.push({
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

// Lifecycle

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
    // Sync search from URL
    if (query.name && typeof query.name === 'string') {
      searchCollection.value = query.name
    } else {
      searchCollection.value = ''
    }
    const newSkip = (page - 1) * paginator.value.limit
    await loadData(paginator.value.limit, newSkip)
  },
  { deep: true, immediate: true },
)
</script>
