<!-- View showing a single title -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && title">
      <v-tabs
        v-model="currentTab"
        class="mb-4"
        color="primary"
        slider-color="primary"
        :grow="!smAndDown"
        show-arrows
      >
        <v-tab
          base-color="primary"
          value="details"
          :to="{
            name: 'title-detail',
            params: { id: title.name },
          }"
        >
          <v-icon class="mr-2">mdi-information</v-icon>
          Info
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditTitle"
          value="history"
          :to="{
            name: 'title-detail-tab',
            params: { id: title.name, selectedTab: 'history' },
          }"
        >
          <v-icon class="mr-2">mdi-history</v-icon>
          History
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditTitle"
          value="edit"
          :to="{
            name: 'title-detail-tab',
            params: { id: title.name, selectedTab: 'edit' },
          }"
        >
          <v-icon class="mr-2">mdi-pencil</v-icon>
          Edit
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canArchiveTitle"
          value="archive"
          :to="{
            name: 'title-detail-tab',
            params: { id: title.name, selectedTab: 'archive' },
          }"
        >
          <v-icon class="mr-2">{{
            title?.archived ? 'mdi-archive-arrow-up' : 'mdi-archive'
          }}</v-icon>
          {{ title?.archived ? 'Restore' : 'Archive' }}
        </v-tab>
      </v-tabs>

      <v-window v-model="currentTab">
        <!-- Details Tab -->
        <v-window-item value="details">
          <v-card flat>
            <v-card-text class="pa-0">
              <div class="ml-4 mr-4 mt-2 mb-2">
                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Id</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <code>{{ title.id }}</code>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Name</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    {{ title.name }}
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Collections</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div v-if="title.collections && title.collections.length > 0">
                      <div
                        v-for="tc in title.collections"
                        :key="`collection-${tc.collection_id}`"
                        class="mb-2"
                      >
                        {{ tc.collection_name }}: {{ tc.path }}
                      </div>
                    </div>
                    <span v-else class="text-grey"
                      >This title is not published in any collection</span
                    >
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Maturity</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    {{ title.maturity }}
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Expected Flavours</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div v-if="title.flavours && title.flavours.length > 0">
                      <v-chip
                        v-for="tf in title.flavours"
                        :key="tf.flavour"
                        size="small"
                        variant="outlined"
                        color="primary"
                        class="mr-2 mb-1"
                      >
                        {{ tf.flavour }}
                      </v-chip>
                    </div>
                    <span v-else class="text-grey">No flavours set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Title</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.title">{{ title.title }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Description</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.description">{{ title.description }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Long Description</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.long_description" style="white-space: pre-wrap">{{
                      title.long_description
                    }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Creator</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.creator">{{ title.creator }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Publisher</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.publisher">{{ title.publisher }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Language</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.language">{{ title.language }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">License</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.license">{{ title.license }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Source</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.source">{{ title.source }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Relation</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="title.relation">{{ title.relation }}</span>
                    <span v-else class="text-grey">Not set</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Illustration</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div v-if="title.illustration_48x48_at_1">
                      <v-img
                        :src="getIllustrationSrc"
                        max-width="48"
                        max-height="48"
                        alt="Title illustration"
                      />
                    </div>
                    <span v-else class="text-grey">No illustration</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Events</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <EventsList :events="title.events" />
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Books</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <BookTable
                      v-if="title.books.length > 0"
                      :headers="bookHeaders"
                      :books="sortedBooks"
                      :is-server-side="false"
                      :show-urls="true"
                      :zim-urls="zimUrls"
                      :loading-urls="loadingUrls"
                    />
                    <span v-else class="text-grey">No books</span>
                  </v-col>
                </v-row>
              </div>
            </v-card-text>
          </v-card>
        </v-window-item>

        <v-window-item value="history">
          <TitleHistory
            v-if="canEditTitle"
            :history="titleHistoryStore.history"
            :has-more="canLoadMoreHistory"
            :loading="loadingHistory"
            :paginator="titleHistoryStore.paginator"
            :title-name="title.name"
            @load="loadHistory"
            @revert="handleRevert"
          />
        </v-window-item>

        <!-- Edit Tab -->
        <v-window-item value="edit">
          <div v-if="canEditTitle" class="pa-4">
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
                <TitleForm
                  ref="titleFormRef"
                  :title="title"
                  :latest-book="latestBook"
                  @update:valid="formValid = $event"
                  @update:has-changes="hasChanges = $event"
                />
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

        <!-- Archive Tab -->
        <v-window-item value="archive">
          <div v-if="canArchiveTitle" class="pa-4">
            <ArchiveTitle
              :name="title.name"
              :is-archived="title?.archived || false"
              @archive-title="archiveTitle"
              @restore-title="restoreTitle"
            />
          </div>
        </v-window-item>
      </v-window>
    </div>

    <!-- Title Update Confirmation Dialog -->
    <ConfirmDialog
      v-model="showConfirmDialog"
      title="Confirm Title Update"
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
          <DiffViewer :differences="enhancedTitleDifferences" />
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
import BookTable from '@/components/BookTable.vue'
import EventsList from '@/components/EventsList.vue'
import ArchiveTitle from '@/components/ArchiveTitle.vue'
import TitleForm from '@/components/TitleForm.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useBookStore } from '@/stores/book'
import { useAuthStore } from '@/stores/auth'
import { useTitleHistoryStore } from '@/stores/titleHistory'
import type { Title, TitleUpdate } from '@/types/title'
import type { Book, ZimUrl } from '@/types/book'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'
import TitleHistory from '@/components/TitleHistory.vue'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'

const router = useRouter()

const loadingStore = useLoadingStore()
const titleStore = useTitleStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()
const titleHistoryStore = useTitleHistoryStore()

const { smAndDown } = useDisplay()

const error = ref<string | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)
const loadingUrls = ref(false)
const loadingHistory = ref<boolean>(false)
const zimUrls = ref<Record<string, ZimUrl[]>>({})
const latestBook = ref<Book | null>(null)

// Edit form state
const titleFormRef = ref<InstanceType<typeof TitleForm>>()
const formValid = ref(false)
const hasChanges = ref(false)
const updating = ref(false)

// Confirmation dialog state
const showConfirmDialog = ref(false)
const pendingComment = ref('')
const pendingUpdatePayload = ref<Partial<TitleUpdate> | null>(null)

const titleDifferences = computed(() => {
  if (!(title.value && pendingUpdatePayload.value)) return undefined

  const currentTitle = JSON.parse(JSON.stringify(title.value))
  const updatedTitle = JSON.parse(JSON.stringify({ ...title.value, ...pendingUpdatePayload.value }))

  return diff(currentTitle, updatedTitle)
})

const enhancedTitleDifferences = computed((): EnhancedDiff[] | undefined => {
  if (!titleDifferences.value) {
    return undefined
  }
  return titleDifferences.value.map((diff) => {
    const enhanced: EnhancedDiff = { ...diff }
    if (diff.path?.includes('illustration_48x48_at_1')) {
      enhanced.isBlob = true
    }
    return enhanced
  })
})

interface Props {
  id: string
  selectedTab?: string
}

const props = withDefaults(defineProps<Props>(), {
  selectedTab: 'details',
})

const bookHeaders = [
  { title: 'Name', value: 'name', sortable: false },
  { title: 'Flavour', value: 'flavour', sortable: false },
  { title: 'Status', value: 'status', sortable: false },
  { title: 'Date', value: 'date', sortable: false },
  { title: 'Deletion Date', value: 'deletion_date', sortable: false },
  { title: 'URLs', value: 'urls', sortable: false },
]

const canEditTitle = computed(
  () => authStore.hasPermission('title', 'update') && title.value && !title.value.archived,
)

const canArchiveTitle = computed(() => authStore.hasPermission('title', 'archive'))

// History-related computed properties
const canLoadMoreHistory = computed(() => {
  const { skip, limit, count } = titleHistoryStore.paginator
  return skip + limit < count
})

// Helper to convert raw base64 to data URL
const getIllustrationSrc = computed(() => {
  if (!title.value?.illustration_48x48_at_1) return ''

  const illustration = title.value.illustration_48x48_at_1

  if (illustration.startsWith('data:')) {
    return illustration
  }

  return `data:image/png;base64,${illustration}`
})

const currentTab = ref(props.selectedTab)

const sortedBooks = computed(() => {
  if (!title.value?.books) return []
  return [...title.value.books].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

const loadLatestBook = async () => {
  if (!title.value?.books || title.value.books.length === 0) {
    latestBook.value = null
    return
  }

  const latestBookId = sortedBooks.value[0]?.id
  if (!latestBookId) {
    latestBook.value = null
    return
  }

  try {
    const book = await bookStore.fetchBook(latestBookId, true)
    latestBook.value = book
  } catch (err) {
    console.error('Failed to fetch latest book', err)
    latestBook.value = null
  }
}

// History-related methods
const loadHistory = async ({ limit, skip }: { limit: number; skip: number }) => {
  if (skip > 0 && !canLoadMoreHistory.value) return

  loadingHistory.value = true
  try {
    const response = await titleHistoryStore.fetchHistory(props.id, limit, skip)
    if (!response) {
      notificationStore.showError(`Failed to ${skip > 0 ? 'load more' : 'load'} history items`)
    }
  } catch (error) {
    console.error('Failed to load history items', error)
  } finally {
    loadingHistory.value = false
  }
}

const loadData = async (
  forceReload: boolean = false,
  fetchHistory: boolean = false,
  fetchZimUrls: boolean = false,
) => {
  loadingStore.startLoading('Fetching title...')

  const data = await titleStore.fetchTitleById(props.id, forceReload)

  if (fetchHistory) {
    titleHistoryStore.clearHistory()
    await loadHistory({ limit: titleHistoryStore.paginator.limit, skip: 0 })
  }

  if (data) {
    error.value = null
    title.value = data
    dataLoaded.value = true
  } else {
    error.value = 'Failed to load title'
    notificationStore.showErrors(titleStore.errors)
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }

  if (fetchZimUrls && title.value?.books && title.value.books.length > 0) {
    loadZimUrls()
  }
}

const loadZimUrls = async () => {
  if (!title.value?.books || title.value.books.length === 0) return

  loadingUrls.value = true
  const bookIds = title.value.books.map((book) => book.id)

  const response = await bookStore.fetchZimUrls(bookIds)
  if (response?.urls) {
    zimUrls.value = response.urls
  } else {
    notificationStore.showErrors(bookStore.errors)
  }

  loadingUrls.value = false
}

const archiveTitle = async () => {
  const response = await titleStore.archiveTitle(props.id)
  if (response) {
    notificationStore.showSuccess(`Title <code>${props.id}</code> has been archived.`)
    // Refresh the title data to update the archive status
    await loadData(true)
    // Switch to info tab after archiving
    currentTab.value = 'details'
  } else {
    notificationStore.showErrors(titleStore.errors)
  }
}

const restoreTitle = async () => {
  const response = await titleStore.restoreTitle(props.id)
  if (response) {
    notificationStore.showSuccess(`Title <code>${props.id}</code> has been restored.`)
    // Refresh the title data to update the archive status
    await loadData(true)
    // Switch to info tab after restoring
    currentTab.value = 'details'
  } else {
    notificationStore.showErrors(titleStore.errors)
  }
}

const handleUpdate = async () => {
  if (!formValid.value || !title.value) return

  try {
    const updatePayload = titleFormRef.value?.getUpdatePayload()

    if (!updatePayload) {
      throw new Error('Failed to get update payload')
    }

    // Check if there are any changes
    const currentTitle = JSON.parse(JSON.stringify(title.value))
    const updatedTitle = JSON.parse(JSON.stringify({ ...title.value, ...updatePayload }))
    const differences = diff(currentTitle, updatedTitle)

    if (!differences || differences.length === 0) {
      notificationStore.showInfo('No changes detected')
      return
    }
    pendingUpdatePayload.value = updatePayload
    pendingComment.value = ''
    showConfirmDialog.value = true
  } catch (err) {
    console.error('Failed to prepare update', err)
    notificationStore.showError('Failed to prepare update')
  }
}

const handleConfirmUpdate = async () => {
  if (!title.value || !pendingUpdatePayload.value) return

  updating.value = true

  try {
    // Add comment to the payload if provided
    const payloadWithComment = {
      ...pendingUpdatePayload.value,
      comment: pendingComment.value || undefined,
    }

    const response = await titleStore.updateTitle(title.value.id, payloadWithComment)
    if (!response) {
      notificationStore.showErrors(titleStore.errors)
      showConfirmDialog.value = false
      return
    }

    notificationStore.showSuccess('Title updated successfully!')
    showConfirmDialog.value = false

    pendingUpdatePayload.value = null
    pendingComment.value = ''

    // If the name changed, navigate to the new URL
    if (response.name !== props.id) {
      await router.push({ name: 'title-detail', params: { id: response.name } })
    }

    await loadData(true)
    currentTab.value = 'details'
  } catch (err) {
    console.error('Failed to update title', err)
    notificationStore.showError('Failed to update title')
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
  if (!title.value) return
  titleFormRef.value?.resetFormToTitle(title.value)
}

const handleRevert = async () => {
  // Reload title data after revert
  await loadData(true, true)
}

onMounted(async () => {
  await loadData(true, props.selectedTab === 'history', props.selectedTab === 'details')

  // Redirect to details if trying to access restricted tabs without permission
  if (props.selectedTab !== 'details' && !canEditTitle.value) {
    router.push({ name: 'title-detail', params: { id: props.id } })
    return
  }

  if (props.selectedTab === 'edit' && title.value) {
    await titleFormRef.value?.fetchCollections()
    await loadLatestBook()
    titleFormRef.value?.resetFormToTitle(title.value)
  }
})

onUnmounted(() => {
  // Clear recipe history to prevent accumulation of history items
  titleHistoryStore.clearHistory()
})

// Watch for tab changes
watch(
  () => props.selectedTab,
  async (newTab) => {
    currentTab.value = newTab

    await loadData(newTab == 'edit', newTab === 'history', newTab === 'details')

    if (newTab === 'edit' && title.value) {
      await titleFormRef.value?.fetchCollections()
      await loadLatestBook()
      titleFormRef.value?.resetFormToTitle(title.value)
    }
  },
)

// Watch for title id changes (when navigating to a different title)
watch(
  () => props.id,
  async () => {
    // Reset the current tab to details when switching title
    // Clear current data and reload the new title
    title.value = null
    currentTab.value = 'details'
  },
)
</script>
