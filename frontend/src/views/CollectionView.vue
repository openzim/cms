<template>
  <v-container>
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && collection">
      <v-tabs
        v-model="currentTab"
        class="mb-4"
        color="primary"
        slider-color="primary"
        show-arrows
        :grow="!smAndDown"
      >
        <v-tab
          base-color="primary"
          value="details"
          :to="{
            name: 'collection-detail',
            params: { id: collection.name },
          }"
        >
          <v-icon class="mr-2">mdi-information</v-icon>
          Info
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditCollection"
          value="history"
          :to="{
            name: 'collection-detail-tab',
            params: { id: collection.name, selectedTab: 'history' },
          }"
        >
          <v-icon class="mr-2">mdi-history</v-icon>
          History
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditCollection"
          value="edit"
          :to="{
            name: 'collection-detail-tab',
            params: { id: collection.name, selectedTab: 'edit' },
          }"
        >
          <v-icon class="mr-2">mdi-pencil</v-icon>
          Edit
        </v-tab>
      </v-tabs>

      <v-window v-model="currentTab">
        <v-window-item value="details">
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
                <div class="text-subtitle-2">Article Count Change Threshold</div>
              </v-col>
              <v-col cols="12" md="9">
                <span v-if="collection.article_count_change_threshold">{{
                  collection.article_count_change_threshold
                }}</span>
                <span v-else class="text-grey">Not set</span>
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Media Count Change Threshold</div>
              </v-col>
              <v-col cols="12" md="9">
                <span v-if="collection.media_count_change_threshold">{{
                  collection.media_count_change_threshold
                }}</span>
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
        </v-window-item>

        <v-window-item value="history">
          <CollectionHistory
            v-if="canEditCollection"
            :history="collectionHistoryStore.history"
            :has-more="canLoadMoreHistory"
            :loading="loadingHistory"
            :paginator="collectionHistoryStore.paginator"
            :collection-name="collection.name"
            @load="loadHistory"
            @revert="handleRevert"
          />
        </v-window-item>

        <v-window-item value="edit">
          <div v-if="canEditCollection" class="pa-4">
            <v-card flat>
              <div class="d-flex flex-column flex-sm-row justify-end ga-2 px-4 pt-4">
                <v-btn
                  :color="updating || !hasChanges ? undefined : 'default'"
                  variant="outlined"
                  @click="handleReset"
                  :disabled="updating || !hasChanges"
                >
                  <v-icon class="mr-2">mdi-restore</v-icon>
                  Reset
                </v-btn>
                <v-btn
                  :color="!formValid || updating || !hasChanges ? undefined : 'primary'"
                  variant="elevated"
                  @click="handleUpdate"
                  :loading="updating"
                  :disabled="!formValid || updating || !hasChanges"
                >
                  <v-icon class="mr-2">mdi-content-save</v-icon>
                  Save Changes
                </v-btn>
              </div>

              <v-card-text>
                <CollectionForm
                  ref="collectionFormRef"
                  :collection="collection"
                  @update:valid="formValid = $event"
                  @update:has-changes="hasChanges = $event"
                />

                <v-alert v-if="updateError" type="error" class="mt-4" density="compact">
                  {{ updateError }}
                </v-alert>
              </v-card-text>

              <div class="d-flex flex-column flex-sm-row justify-end ga-2 px-4 pb-4">
                <v-btn
                  :color="updating || !hasChanges ? undefined : 'default'"
                  variant="outlined"
                  @click="handleReset"
                  :disabled="updating || !hasChanges"
                >
                  <v-icon class="mr-2">mdi-restore</v-icon>
                  Reset
                </v-btn>
                <v-btn
                  :color="!formValid || updating || !hasChanges ? undefined : 'primary'"
                  variant="elevated"
                  @click="handleUpdate"
                  :loading="updating"
                  :disabled="!formValid || updating || !hasChanges"
                >
                  <v-icon class="mr-2">mdi-content-save</v-icon>
                  Save Changes
                </v-btn>
              </div>
            </v-card>
          </div>
        </v-window-item>
      </v-window>
    </div>

    <!-- Collection Update Confirmation Dialog -->
    <ConfirmDialog
      v-model="showConfirmDialog"
      title="Confirm Collection Update"
      confirm-text="Save Changes"
      cancel-text="Cancel"
      confirm-color="primary"
      icon="mdi-pencil"
      icon-color="primary"
      :max-width="600"
      :loading="updating"
      @confirm="handleConfirmUpdate"
      @cancel="handleCancelUpdate"
    >
      <template #content>
        <div class="mb-4">
          <h3 class="text-h6 mb-2">Changes Summary</h3>
          <p class="text-body-2 text-medium-emphasis mb-3">
            Please review the changes below and optionally add a comment describing what you've
            modified.
          </p>
        </div>

        <div class="mb-4">
          <DiffViewer :differences="enhancedCollectionDifferences" />
        </div>

        <div>
          <v-textarea
            v-model.trim="pendingComment"
            label="Comment (optional)"
            variant="outlined"
            auto-grow
            rows="3"
            persistent-hint
          />
        </div>
      </template>
    </ConfirmDialog>
  </v-container>
</template>

<script setup lang="ts">
import CollectionHistory from '@/components/CollectionHistory.vue'
import CollectionForm from '@/components/CollectionForm.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useCollectionsStore } from '@/stores/collections'
import { useCollectionHistoryStore } from '@/stores/collectionHistory'
import { useAuthStore } from '@/stores/auth'
import type { Collection, CollectionUpdate } from '@/types/collections'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'

const { smAndDown } = useDisplay()

const router = useRouter()

const loadingStore = useLoadingStore()
const collectionStore = useCollectionsStore()
const collectionHistoryStore = useCollectionHistoryStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

const error = ref<string | null>(null)
const collection = ref<Collection | null>(null)
const dataLoaded = ref(false)
const loadingHistory = ref<boolean>(false)

const collectionFormRef = ref<InstanceType<typeof CollectionForm>>()
const formValid = ref(false)
const hasChanges = ref(false)
const updating = ref(false)
const updateError = ref('')

// Confirmation dialog state
const showConfirmDialog = ref(false)
const pendingComment = ref('')
const pendingUpdatePayload = ref<Partial<CollectionUpdate> | null>(null)

const canEditCollection = computed(() => authStore.hasPermission('collection', 'update'))

const canLoadMoreHistory = computed(() => {
  const { skip, limit, count } = collectionHistoryStore.paginator
  return skip + limit < count
})

const collectionDifferences = computed(() => {
  if (!collection.value || !pendingUpdatePayload.value) return undefined

  const currentCollection = JSON.parse(JSON.stringify(collection.value))
  const updatedCollection = JSON.parse(
    JSON.stringify({ ...collection.value, ...pendingUpdatePayload.value }),
  )
  return diff(currentCollection, updatedCollection)
})

const enhancedCollectionDifferences = computed(() => {
  if (!collectionDifferences.value) return undefined
  return collectionDifferences.value as EnhancedDiff[]
})

interface Props {
  id: string
  selectedTab?: string
}

const props = withDefaults(defineProps<Props>(), {
  selectedTab: 'details',
})

const currentTab = ref(props.selectedTab)

const loadHistory = async ({ limit, skip }: { limit: number; skip: number }) => {
  if (skip > 0 && !canLoadMoreHistory.value) return

  loadingHistory.value = true
  try {
    const response = await collectionHistoryStore.fetchHistory(props.id, limit, skip)
    if (!response) {
      notificationStore.showError(`Failed to ${skip > 0 ? 'load more' : 'load'} history items`)
    }
  } catch (error) {
    console.error('Failed to load history items', error)
  } finally {
    loadingHistory.value = false
  }
}

const loadData = async (forceReload: boolean = false, fetchHistory: boolean = false) => {
  loadingStore.startLoading('Fetching collection...')

  const data = await collectionStore.fetchCollection(props.id, forceReload)

  if (fetchHistory) {
    collectionHistoryStore.clearHistory()
    await loadHistory({ limit: collectionHistoryStore.paginator.limit, skip: 0 })
  }

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

const handleUpdate = async () => {
  if (!formValid.value || !collection.value) return

  updateError.value = ''

  try {
    const updatePayload = collectionFormRef.value?.getUpdatePayload()

    if (!updatePayload) {
      throw new Error('Failed to get update payload')
    }

    // Check if there are any changes
    const currentCollection = JSON.parse(JSON.stringify(collection.value))
    const updatedCollection = JSON.parse(JSON.stringify({ ...collection.value, ...updatePayload }))
    const differences = diff(currentCollection, updatedCollection)

    if (!differences || differences.length === 0) {
      notificationStore.showInfo('No changes detected')
      return
    }
    pendingUpdatePayload.value = updatePayload
    pendingComment.value = ''
    showConfirmDialog.value = true
  } catch (err) {
    console.error('Failed to prepare update', err)
    updateError.value = 'Failed to prepare update'
  }
}

const handleConfirmUpdate = async () => {
  if (!collection.value || !pendingUpdatePayload.value) return

  updating.value = true
  updateError.value = ''

  try {
    // Add comment to the payload if provided
    const payloadWithComment = {
      ...pendingUpdatePayload.value,
      comment: pendingComment.value || undefined,
    }

    const response = await collectionStore.updateCollection(collection.value.id, payloadWithComment)
    if (!response) {
      updateError.value = collectionStore.errors.join(', ') || 'Failed to update collection'
      showConfirmDialog.value = false
      return
    }

    notificationStore.showSuccess('Collection updated successfully!')
    showConfirmDialog.value = false

    pendingUpdatePayload.value = null
    pendingComment.value = ''

    // If the name changed, navigate to the new URL
    if (response.name !== props.id) {
      await router.push({ name: 'collection-detail', params: { id: response.name } })
    }

    await loadData(true)
    currentTab.value = 'details'
  } catch (err) {
    console.error('Failed to update collection', err)
    updateError.value = collectionStore.errors.join(', ') || 'Failed to update collection'
    showConfirmDialog.value = false
  } finally {
    updating.value = false
  }
}

const handleCancelUpdate = () => {
  showConfirmDialog.value = false
  pendingUpdatePayload.value = null
  pendingComment.value = ''
  updating.value = false
}

const handleReset = () => {
  collectionFormRef.value?.resetFormToCollection(collection.value!)
  updateError.value = ''
}

const handleRevert = async () => {
  await loadData(true, true)
}

onMounted(async () => {
  await loadData(true, props.selectedTab === 'history')

  // Redirect to details if trying to access restricted tabs without permission
  if (props.selectedTab !== 'details' && !canEditCollection.value) {
    router.push({ name: 'collection-detail', params: { id: props.id } })
    return
  }

  if (props.selectedTab === 'edit' && collection.value) {
    collectionFormRef.value?.resetFormToCollection(collection.value)
  }
})

onUnmounted(() => {
  // Clear collection history to prevent accumulation of history items
  collectionHistoryStore.clearHistory()
})

// Watch for tab changes
watch(
  () => props.selectedTab,
  async (newTab) => {
    currentTab.value = newTab
    await loadData(newTab === 'edit', newTab === 'history')

    if (newTab === 'edit' && collection.value) {
      collectionFormRef.value?.resetFormToCollection(collection.value)
    }
  },
)

// Watch for collection id changes (when navigating to a different collection)
watch(
  () => props.id,
  async () => {
    // Reset the current tab to details when switching collection
    // Clear current data and reload the new collection
    collection.value = null
    currentTab.value = 'details'
  },
)
</script>
