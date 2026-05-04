<template>
  <v-container>
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && collection">
      <div class="d-flex justify-end mb-4" v-if="canEditCollection">
        <v-btn color="primary" prepend-icon="mdi-pencil" @click="openEditDialog">
          Edit Collection
        </v-btn>
      </div>
      <div>
        <v-row no-gutters class="py-2">
          <v-col cols="12" md="3">
            <div class="text-subtitle-2">Id</div>
          </v-col>
          <v-col cols="12" md="9">
            <code>{{ collection.id }}</code>
          </v-col>
        </v-row>
        <v-divider class="my-2"></v-divider>

        <v-row no-gutters class="py-2">
          <v-col cols="12" md="3">
            <div class="text-subtitle-2">Name</div>
          </v-col>
          <v-col cols="12" md="9">
            {{ collection.name }}
          </v-col>
        </v-row>
        <v-divider class="my-2"></v-divider>

        <v-row no-gutters class="py-2">
          <v-col cols="12" md="3">
            <div class="text-subtitle-2">Warehouse</div>
          </v-col>
          <v-col cols="12" md="9">
            {{ collection.warehouse }}
          </v-col>
        </v-row>
        <v-divider class="my-2"></v-divider>

        <v-row no-gutters class="py-2">
          <v-col cols="12" md="3">
            <div class="text-subtitle-2">Download Base URL</div>
          </v-col>
          <v-col cols="12" md="9">
            <span v-if="collection.download_base_url">{{ collection.download_base_url }}</span>
            <span v-else class="text-grey">Not set</span>
          </v-col>
        </v-row>
        <v-divider class="my-2"></v-divider>

        <v-row no-gutters class="py-2">
          <v-col cols="12" md="3">
            <div class="text-subtitle-2">View Base URL</div>
          </v-col>
          <v-col cols="12" md="9">
            <span v-if="collection.view_base_url">{{ collection.view_base_url }}</span>
            <span v-else class="text-grey">Not set</span>
          </v-col>
        </v-row>
        <v-divider class="my-2"></v-divider>

        <v-row no-gutters class="py-2">
          <v-col cols="12" md="3">
            <div class="text-subtitle-2">Titles</div>
          </v-col>
          <v-col cols="12" md="9">
            <router-link
              :to="{ name: 'titles', query: { collection_name: collection.name } }"
              class="text-decoration-none text-primary font-weight-medium"
            >
              View Titles
            </router-link>
          </v-col>
        </v-row>
      </div>
    </div>

    <EditCollectionDialog
      v-model="editDialogOpen"
      :collection="collection"
      @updated="handleCollectionUpdated"
    />
  </v-container>
</template>

<script setup lang="ts">
import EditCollectionDialog from '@/components/EditCollectionDialog.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useCollectionsStore } from '@/stores/collections'
import { useAuthStore } from '@/stores/auth'
import type { Collection } from '@/types/collections'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const loadingStore = useLoadingStore()
const collectionStore = useCollectionsStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

const error = ref<string | null>(null)
const collection = ref<Collection | null>(null)
const dataLoaded = ref(false)
const editDialogOpen = ref(false)

const canEditCollection = computed(() => authStore.hasPermission('collection', 'update'))

interface Props {
  id: string
}

const props = defineProps<Props>()

const loadData = async () => {
  loadingStore.startLoading('Fetching collection...')

  const data = await collectionStore.fetchCollection(props.id)
  if (data) {
    error.value = null
    collection.value = data
    dataLoaded.value = true
  } else {
    error.value = 'Failed to load collection'
    for (const err of collectionStore.errors) {
      notificationStore.showError(err)
    }
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

onMounted(async () => {
  await loadData()
})

const openEditDialog = () => {
  editDialogOpen.value = true
}

const handleCollectionUpdated = async (updatedCollection: { id: string; name: string }) => {
  notificationStore.showSuccess('Collection updated successfully!')

  // If the name changed, navigate to the new URL
  if (updatedCollection.name !== props.id) {
    await router.push({ name: 'collection-detail', params: { id: updatedCollection.name } })
  }
  await loadData()
}
</script>
