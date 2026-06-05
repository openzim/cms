<!-- View showing a single book -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && book">
      <div
        class="d-flex flex-md-row flex-column justify-md-end ga-2"
        v-if="
          canMoveBook ||
          canDeleteBook ||
          canRecoverBook ||
          canAddBookToTitle ||
          canCreateTitleFromBook
        "
      >
        <v-btn v-if="canMoveBook" color="primary" prepend-icon="mdi-truck" @click="openMoveDialog">
          Move Book
        </v-btn>
        <v-btn
          v-if="canRecoverBook"
          color="success"
          prepend-icon="mdi-restore"
          @click="openRecoverDialog"
        >
          Recover Book
        </v-btn>
        <v-btn
          v-if="canDeleteBook"
          color="error"
          prepend-icon="mdi-delete"
          @click="openDeleteDialog"
        >
          Delete Book
        </v-btn>
        <v-btn
          v-if="canCreateTitleFromBook"
          color="primary"
          prepend-icon="mdi-plus-circle"
          @click="openCreateTitleDialog"
        >
          Create New Title
        </v-btn>
        <v-btn
          v-if="canAddBookToTitle"
          color="warning"
          prepend-icon="mdi-link-plus"
          @click="openAddToTitleDialog"
        >
          Add to Title
        </v-btn>
      </div>

      <v-alert
        v-if="book.has_flavour_mismatch"
        type="warning"
        variant="tonal"
        class="mb-4"
        icon="mdi-alert"
      >
        <div class="d-flex align-center ga-2">
          <div class="flex-grow-1">
            <div class="font-weight-bold mb-1">Flavour Mismatch</div>
            <div>
              This book's flavour is not in the list of flavours expected by the title. Consider
              updating the book flavour or title expected flavours to maintain consistency.
            </div>
          </div>
          <v-btn
            v-if="canEditBook"
            variant="outlined"
            color="warning"
            size="small"
            @click="currentTab = 'edit'"
          >
            Edit Book
          </v-btn>
          <v-btn
            v-if="canEditBookTitle"
            variant="outlined"
            color="warning"
            size="small"
            :to="{
              name: 'title-detail-tab',
              params: { id: book.title_id, selectedTab: 'edit' },
            }"
          >
            Edit Title
          </v-btn>
        </div>
      </v-alert>

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
          value="info"
          :to="{
            name: 'book-detail',
            params: { id: book.id },
          }"
        >
          <v-icon class="mr-2">mdi-information</v-icon>
          Info
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditBook"
          value="history"
          :to="{
            name: 'book-detail-tab',
            params: { id: book.id, selectedTab: 'history' },
          }"
        >
          <v-icon class="mr-2">mdi-history</v-icon>
          History
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditBook"
          value="edit"
          :to="{
            name: 'book-detail-tab',
            params: { id: book.id, selectedTab: 'edit' },
          }"
        >
          <v-icon class="mr-2">mdi-pencil</v-icon>
          Edit
        </v-tab>
      </v-tabs>

      <v-window v-model="currentTab">
        <!-- Info Tab -->
        <v-window-item value="info">
          <v-card flat>
            <v-card-text class="pa-0">
              <div class="ml-4 mr-4 mt-2 mb-2">
                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Id</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <code>{{ book.id }}</code>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Title Id</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <router-link
                      v-if="book.title_id"
                      :to="{ name: 'title-detail', params: { id: book.title_id } }"
                    >
                      {{ book.title_id }}
                    </router-link>
                    <span v-else class="text-grey">None</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Status</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <BookStatus :book="book" force-row />
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Created</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <v-tooltip location="bottom">
                      <template #activator="{ props }">
                        <span v-bind="props">
                          {{ fromNow(book.created_at) }}
                        </span>
                      </template>
                      <span>{{ formatDt(book.created_at) }}</span>
                    </v-tooltip>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Name</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="book.name">{{ book.name }}</span>
                    <span v-else class="text-grey">-</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Flavour</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div>
                      <span v-if="book.flavour">{{ book.flavour }}</span>
                      <span v-else class="text-grey">-</span>
                      <v-tooltip v-if="book.has_flavour_mismatch" location="top">
                        <template #activator="{ props: tooltipProps }">
                          <v-icon v-bind="tooltipProps" color="warning" size="small" class="ml-2">
                            mdi-alert
                          </v-icon>
                        </template>
                        <span>Book flavour does not match title flavours</span>
                      </v-tooltip>
                    </div>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Date</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <span v-if="book.date">{{ book.date }}</span>
                    <span v-else class="text-grey">-</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">URLs</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <ZimUrlButtons :urls="zimUrls" :loading="loadingUrls" />
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Article Count</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    {{ book.article_count.toLocaleString() }}
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Media Count</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    {{ book.media_count.toLocaleString() }}
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Size</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    {{ formatBytes(book.size) }}
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">
                      ZIM Metadata
                      <v-btn
                        size="small"
                        variant="outlined"
                        class="ml-2"
                        @click="copyToClipboard(JSON.stringify(book.zim_metadata, null, 2))"
                      >
                        <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                        Copy
                      </v-btn>
                    </div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div class="overflow-y-auto overflow-x-auto" style="max-height: 400px">
                      <pre>{{ JSON.stringify(book.zim_metadata, null, 2) }}</pre>
                    </div>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">
                      Zimcheck Result
                      <v-btn
                        size="small"
                        variant="outlined"
                        class="ml-2"
                        @click="copyToClipboard(JSON.stringify(book.zimcheck_result, null, 2))"
                      >
                        <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                        Copy
                      </v-btn>
                    </div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div class="overflow-y-auto overflow-x-auto" style="max-height: 400px">
                      <pre>{{ JSON.stringify(book.zimcheck_result, null, 2) }}</pre>
                    </div>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Current Locations</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <v-data-table
                      v-if="book.current_locations.length > 0"
                      :headers="locationHeaders"
                      :items="book.current_locations"
                      :items-per-page="-1"
                      :mobile="smAndDown"
                      density="compact"
                      hide-default-footer
                    >
                      <template #[`item.filename`]="{ item }">
                        <code>{{ item.filename }}</code>
                      </template>
                    </v-data-table>
                    <span v-else class="text-grey">No current locations</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Target Locations</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <v-data-table
                      v-if="book.target_locations.length > 0"
                      :headers="locationHeaders"
                      :items="book.target_locations"
                      :items-per-page="-1"
                      :mobile="smAndDown"
                      density="compact"
                      hide-default-footer
                    >
                      <template #[`item.filename`]="{ item }">
                        <code>{{ item.filename }}</code>
                      </template>
                    </v-data-table>
                    <span v-else class="text-grey">No target locations</span>
                  </v-col>
                </v-row>
                <v-divider class="my-2"></v-divider>

                <v-row no-gutters class="py-2">
                  <v-col cols="12" md="3">
                    <div class="text-subtitle-2">Events</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <EventsList :events="book.events" />
                  </v-col>
                </v-row>
              </div>
            </v-card-text>
          </v-card>
        </v-window-item>

        <!-- Edit Tab -->
        <v-window-item value="edit">
          <div v-if="canEditBook" class="pa-4">
            <EditBookForm
              :book="book"
              :loading="updatingBook"
              :flavour-options="flavours"
              :loading-flavours="loadingFlavours"
              @submit="handleUpdateBook"
            />
          </div>
        </v-window-item>

        <!-- History Tab -->
        <v-window-item value="history">
          <BookHistory
            v-if="canEditBook"
            :history="bookHistoryStore.history"
            :has-more="canLoadMoreHistory"
            :loading="loadingHistory"
            :paginator="bookHistoryStore.paginator"
            :book-id="book.id"
            @load="loadHistory"
            @revert="handleRevert"
          />
        </v-window-item>
      </v-window>
    </div>

    <MoveBookDialog v-model="moveDialogOpen" :book="book" @moved="handleBookMoved" />
    <RecoverBookDialog v-model="recoverDialogOpen" :book="book" @recovered="handleBookRecovered" />
    <DeleteBookDialog v-model="deleteDialogOpen" :book="book" @deleted="handleBookDeleted" />
    <TitleSelectDialog
      v-if="book && book.name"
      v-model="addToTitleDialogOpen"
      :book-name="book.name"
      @title-selected="handleTitleSelected"
    />
    <TitleFormDialog
      v-model="createTitleDialogOpen"
      :title="titleDataFromBook"
      @created="handleTitleCreated"
    />

    <ConfirmDialog
      v-model="showConfirmDialog"
      title="Confirm Book Update"
      confirm-text="Save Changes"
      cancel-text="Cancel"
      confirm-color="primary"
      icon="mdi-pencil"
      icon-color="primary"
      :max-width="600"
      :loading="updatingBook"
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
          <DiffViewer :differences="enhancedBookDifferences" />
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
import BookStatus from '@/components/BookStatus.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DeleteBookDialog from '@/components/DeleteBookDialog.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import EditBookForm from '@/components/EditBookForm.vue'
import EventsList from '@/components/EventsList.vue'
import MoveBookDialog from '@/components/MoveBookDialog.vue'
import RecoverBookDialog from '@/components/RecoverBookDialog.vue'
import TitleSelectDialog from '@/components/TitleSelectDialog.vue'
import TitleFormDialog from '@/components/TitleFormDialog.vue'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'
import BookHistory from '@/components/BookHistory.vue'
import { useAuthStore } from '@/stores/auth'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useBookStore } from '@/stores/book'
import { useTitleStore } from '@/stores/title'
import { useBookHistoryStore } from '@/stores/bookHistory'
import type { Book, ZimUrl } from '@/types/book'
import type { Title } from '@/types/title'
import { formatDt, fromNow } from '@/utils/format'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'

const { smAndDown } = useDisplay()

const loadingStore = useLoadingStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()
const titleStore = useTitleStore()
const bookHistoryStore = useBookHistoryStore()

const error = ref<string | null>(null)
const book = ref<Book | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)
const loadingUrls = ref(false)
const zimUrls = ref<ZimUrl[]>([])
const moveDialogOpen = ref(false)
const recoverDialogOpen = ref(false)
const deleteDialogOpen = ref(false)
const addToTitleDialogOpen = ref(false)
const createTitleDialogOpen = ref(false)
const updatingBook = ref(false)
const updateError = ref('')
const flavours = ref<string[]>([])
const loadingFlavours = ref(false)
const loadingHistory = ref(false)

const showConfirmDialog = ref(false)
const pendingComment = ref('')
const pendingUpdatePayload = ref<{ flavour: string } | null>(null)

interface Props {
  id: string
  selectedTab?: string
}

const props = withDefaults(defineProps<Props>(), {
  selectedTab: 'info',
})

const currentTab = ref(props.selectedTab)

const bookDifferences = computed(() => {
  if (!(book.value && pendingUpdatePayload.value)) return undefined

  const currentBook = JSON.parse(
    JSON.stringify({ name: book.value.name, flavour: book.value.flavour }),
  )
  const updatedBook = JSON.parse(JSON.stringify({ ...currentBook, ...pendingUpdatePayload.value }))

  return diff(currentBook, updatedBook)
})

const enhancedBookDifferences = computed((): EnhancedDiff[] | undefined => {
  if (!bookDifferences.value) {
    return undefined
  }
  return bookDifferences.value as EnhancedDiff[]
})

const locationHeaders = [
  { title: 'Warehouse', value: 'warehouse_name', sortable: false },
  { title: 'Folder', value: 'path', sortable: false },
  { title: 'Filename', value: 'filename', sortable: false },
]

const canEditBook = computed(() => {
  if (!book.value) return false
  return (
    authStore.hasPermission('book', 'update') &&
    !book.value.title_archived &&
    book.value.location_kind != 'deleted'
  )
})

const canMoveBook = computed(() => {
  if (!book.value) return false

  return (
    authStore.hasPermission('book', 'update') &&
    ['staging', 'prod'].includes(book.value.location_kind) &&
    book.value.current_locations.length > 0 &&
    !book.value.has_error &&
    !book.value.needs_file_operation &&
    !book.value.needs_processing &&
    !book.value.title_archived
  )
})

const canDeleteBook = computed(() => {
  if (!book.value) return false
  return (
    authStore.hasPermission('book', 'delete') &&
    ['staging', 'prod', 'quarantine'].includes(book.value.location_kind) &&
    !book.value.needs_file_operation &&
    !book.value.needs_processing
  )
})

const canEditBookTitle = computed(() => {
  if (!book.value) return false

  return (
    authStore.hasPermission('title', 'update') && book.value.title_id && !book.value.title_archived
  )
})

const canRecoverBook = computed(() => {
  if (!book.value) return false

  const hasFutureDeletionDate = book.value.deletion_date
    ? new Date(book.value.deletion_date) > new Date()
    : false

  return (
    authStore.hasPermission('book', 'update') &&
    book.value.location_kind === 'to_delete' &&
    book.value.needs_file_operation &&
    !book.value.needs_processing &&
    hasFutureDeletionDate &&
    !book.value.title_archived
  )
})

const canAddBookToTitle = computed(() => {
  if (!book.value) return false
  return (
    authStore.hasPermission('book', 'update') &&
    book.value.location_kind == 'quarantine' &&
    book.value.title_id === null &&
    !!book.value.name
  )
})

const canCreateTitleFromBook = computed(() => {
  if (!book.value) return false
  return (
    authStore.hasPermission('title', 'create') &&
    book.value.location_kind == 'quarantine' &&
    book.value.title_id === null &&
    !!book.value.name
  )
})

const titleDataFromBook = computed<Title | null>(() => {
  if (!book.value) return null

  const metadata = book.value.zim_metadata as Record<string, unknown>

  // Create a Title object with data from the book
  return {
    id: '', // Will be assigned on creation
    name: book.value.name || '',
    maturity: 'unstable',
    archived: false,
    collection_titles: [],
    title: (metadata.Title as string | null | undefined) || null,
    creator: (metadata.Creator as string | null | undefined) || null,
    publisher: (metadata.Publisher as string | null | undefined) || null,
    description: (metadata.Description as string | null | undefined) || null,
    language: (metadata.Language as string | null | undefined) || null,
    illustration_48x48_at_1:
      (metadata['Illustration_48x48@1'] as string | null | undefined) || null,
    long_description: (metadata.LongDescription as string | null | undefined) || null,
    license: (metadata.License as string | null | undefined) || null,
    relation: (metadata.Relation as string | null | undefined) || null,
    source: (metadata.Source as string | null | undefined) || null,
    flavours: book.value.flavour ? [book.value.flavour] : [],
    events: [],
    books: [],
    collections: [],
  }
})

const canLoadMoreHistory = computed(() => {
  const { skip, limit, count } = bookHistoryStore.paginator
  return skip + limit < count
})

const loadTitleData = async () => {
  if (!book.value?.title_id) {
    title.value = null
    return
  }

  const data = await titleStore.fetchTitleById(book.value.title_id, false)
  if (data) {
    title.value = data
  } else {
    title.value = null
  }
}

const loadData = async (
  forceReload: boolean = false,
  fetchHistory: boolean = false,
  fetchZimUrls: boolean = false,
) => {
  loadingStore.startLoading('Fetching book...')

  const data = await bookStore.fetchBook(props.id, forceReload)

  if (fetchHistory) {
    bookHistoryStore.clearHistory()
    await loadHistory({ limit: bookHistoryStore.paginator.limit, skip: 0 })
  }

  if (data) {
    error.value = null
    book.value = data
    dataLoaded.value = true
    await loadTitleData()
  } else {
    error.value = 'Failed to load book'
    for (const err of bookStore.errors) {
      notificationStore.showError(err)
    }
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }

  if (fetchZimUrls && book.value) {
    loadZimUrls()
  }
}

const loadZimUrls = async () => {
  if (!book.value) return

  loadingUrls.value = true

  const response = await bookStore.fetchZimUrls([book.value.id])
  if (response?.urls && response.urls[book.value.id]) {
    zimUrls.value = response.urls[book.value.id]
  } else {
    for (const err of bookStore.errors) {
      notificationStore.showError(err)
    }
  }

  loadingUrls.value = false
}

onMounted(async () => {
  await loadData(true, props.selectedTab === 'history', true)
})

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText('```\n' + text + '\n```\n')
    notificationStore.showSuccess(`Copied to Clipboard!`)
  } catch {
    notificationStore.showError(`Unable to copy to clipboard 😞. Please copy it manually.`)
  }
}

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const openMoveDialog = () => {
  moveDialogOpen.value = true
}

const handleBookMoved = async () => {
  notificationStore.showSuccess('Book moved successfully!')
  await loadData()
}

const openRecoverDialog = () => {
  recoverDialogOpen.value = true
}

const handleBookRecovered = async () => {
  notificationStore.showSuccess('Book recovered successfully!')
  await loadData()
}

const openDeleteDialog = () => {
  deleteDialogOpen.value = true
}

const handleBookDeleted = async () => {
  notificationStore.showSuccess('Book deleted successfully!')
  await loadData(true)
}

const openAddToTitleDialog = () => {
  addToTitleDialogOpen.value = true
}

const openCreateTitleDialog = () => {
  createTitleDialogOpen.value = true
}

const handleTitleSelected = async (titleName: string) => {
  if (!book.value || !book.value.name) return

  loadingStore.startLoading('Updating title name...')

  const response = await titleStore.updateTitle(titleName, {
    name: book.value.name,
    comment: `Updated title name to "${book.value.name}" from book`,
  })

  loadingStore.stopLoading()

  if (response) {
    notificationStore.showSuccess(`Title name updated to "${book.value.name}" successfully`)
    await loadData(true, currentTab.value == 'history', currentTab.value == 'info')
  } else {
    for (const error of titleStore.errors) {
      notificationStore.showError(error)
    }
  }
}

const handleTitleCreated = async () => {
  notificationStore.showSuccess('Title created successfully!')
  await loadData(true, currentTab.value == 'history', currentTab.value == 'info')
}

const handleUpdateBook = async (bookData: { flavour: string }) => {
  if (!book.value) return

  updateError.value = ''

  try {
    // Check if there are any changes
    const currentBook = JSON.parse(
      JSON.stringify({ name: book.value.name, flavour: book.value.flavour }),
    )
    const updatedBook = JSON.parse(JSON.stringify({ ...currentBook, ...bookData }))
    const differences = diff(currentBook, updatedBook)

    if (!differences || differences.length === 0) {
      notificationStore.showInfo('No changes detected')
      return
    }

    pendingUpdatePayload.value = bookData
    pendingComment.value = ''
    showConfirmDialog.value = true
  } catch (err) {
    console.error('Failed to prepare update', err)
    updateError.value = 'Failed to prepare update'
  }
}

const handleConfirmUpdate = async () => {
  if (!book.value || !pendingUpdatePayload.value) return

  updatingBook.value = true
  updateError.value = ''

  try {
    // Add comment to the payload if provided
    const payloadWithComment = {
      ...pendingUpdatePayload.value,
      comment: pendingComment.value || undefined,
    }

    const response = await bookStore.updateBook(props.id, payloadWithComment)
    if (!response) {
      updateError.value = bookStore.errors.join(', ') || 'Failed to update book'
      showConfirmDialog.value = false
      return
    }

    notificationStore.showSuccess('Book updated successfully!')
    showConfirmDialog.value = false

    pendingUpdatePayload.value = null
    pendingComment.value = ''

    book.value = response
    await loadData(true)
    currentTab.value = 'info'
  } catch (err) {
    console.error('Failed to update book', err)
    updateError.value = bookStore.errors.join(', ') || 'Failed to update book'
    showConfirmDialog.value = false
  } finally {
    updatingBook.value = false
  }
}

const handleCancelUpdate = () => {
  showConfirmDialog.value = false
  pendingUpdatePayload.value = null
  pendingComment.value = ''
  updatingBook.value = false
}

const loadHistory = async ({ limit, skip }: { limit: number; skip: number }) => {
  loadingHistory.value = true
  try {
    const response = await bookHistoryStore.fetchHistory(props.id, limit, skip)
    if (!response) {
      notificationStore.showError(`Failed to ${skip > 0 ? 'load more' : 'load'} history items`)
    }
  } catch (error) {
    console.error('Failed to load book history', error)
    notificationStore.showError('Failed to load book history')
  } finally {
    loadingHistory.value = false
  }
}

const handleRevert = async () => {
  // Reload book data and history after successful revert
  await loadData(true, true)
}

watch(
  () => props.selectedTab,
  async (newTab) => {
    currentTab.value = newTab

    await loadData(newTab == 'edit', newTab === 'history', newTab === 'info')

    if (newTab === 'edit' && book.value && flavours.value.length == 0) {
      loadingFlavours.value = true
      const fetchedFlavours = await bookStore.fetchBookFlavours()
      if (fetchedFlavours) {
        flavours.value = fetchedFlavours
      }
      loadingFlavours.value = false
    }
  },
)

watch(
  () => props.id,
  async () => {
    book.value = null
    currentTab.value = 'info'
    await loadData(true)
  },
)

onUnmounted(() => {
  // Clear book history to prevent accumulation of history items
  bookHistoryStore.clearHistory()
})
</script>
