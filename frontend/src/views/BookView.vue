<!-- View showing a single book -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && book">
      <div class="d-flex justify-end mb-4" v-if="canMoveBook || canDeleteBook || canRecoverBook">
        <v-btn
          v-if="canMoveBook"
          color="primary"
          prepend-icon="mdi-truck"
          @click="openMoveDialog"
          class="mr-2"
        >
          Move Book
        </v-btn>
        <v-btn
          v-if="canRecoverBook"
          color="success"
          prepend-icon="mdi-restore"
          @click="openRecoverDialog"
          class="mr-2"
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
      </div>

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
          v-if="book.title_id && canSyncMetadata"
          value="sync"
          :to="{
            name: 'book-detail-tab',
            params: { id: book.id, selectedTab: 'sync' },
          }"
        >
          <v-icon class="mr-2">mdi-sync</v-icon>
          Sync Metadata
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
                    <span v-if="book.flavour">{{ book.flavour }}</span>
                    <span v-else class="text-grey">-</span>
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

        <!-- Sync Metadata Tab -->
        <v-window-item value="sync">
          <div class="pa-4">
            <BookToTitleMetadataSync :book="book" :title="title" @synced="handleMetadataSynced" />
          </div>
        </v-window-item>
      </v-window>
    </div>

    <MoveBookDialog v-model="moveDialogOpen" :book="book" @moved="handleBookMoved" />
    <RecoverBookDialog v-model="recoverDialogOpen" :book="book" @recovered="handleBookRecovered" />
    <DeleteBookDialog v-model="deleteDialogOpen" :book="book" @deleted="handleBookDeleted" />
  </v-container>
</template>

<script setup lang="ts">
import BookStatus from '@/components/BookStatus.vue'
import BookToTitleMetadataSync from '@/components/BookToTitleMetadataSync.vue'
import DeleteBookDialog from '@/components/DeleteBookDialog.vue'
import EventsList from '@/components/EventsList.vue'
import MoveBookDialog from '@/components/MoveBookDialog.vue'
import RecoverBookDialog from '@/components/RecoverBookDialog.vue'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'
import { useAuthStore } from '@/stores/auth'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useBookStore } from '@/stores/book'
import { useTitleStore } from '@/stores/title'
import type { Book, ZimUrl } from '@/types/book'
import type { Title } from '@/types/title'
import { formatDt, fromNow } from '@/utils/format'
import { computed, onMounted, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'

const { smAndDown } = useDisplay()

const loadingStore = useLoadingStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()
const titleStore = useTitleStore()

const error = ref<string | null>(null)
const book = ref<Book | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)
const loadingUrls = ref(false)
const zimUrls = ref<ZimUrl[]>([])
const moveDialogOpen = ref(false)
const recoverDialogOpen = ref(false)
const deleteDialogOpen = ref(false)

interface Props {
  id: string
  selectedTab?: string
}

const props = withDefaults(defineProps<Props>(), {
  selectedTab: 'info',
})

const currentTab = ref(props.selectedTab)

const locationHeaders = [
  { title: 'Warehouse', value: 'warehouse_name', sortable: false },
  { title: 'Folder', value: 'path', sortable: false },
  { title: 'Filename', value: 'filename', sortable: false },
]

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

const canSyncMetadata = computed(() => {
  // User needs permission to update titles
  // Title must exist and not be archived
  return (
    authStore.hasPermission('title', 'update') &&
    book.value?.title_id &&
    title.value &&
    !title.value.archived &&
    !book.value.title_archived
  )
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

const loadData = async (forceReload: boolean = false) => {
  loadingStore.startLoading('Fetching book...')

  const data = await bookStore.fetchBook(props.id, forceReload)
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

  if (book.value) {
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
  await loadData(true)
})

watch(
  () => props.selectedTab,
  (newTab) => {
    currentTab.value = newTab
  },
)

// Watch for book id changes (e.g. navigating between books without remounting)
watch(
  () => props.id,
  async () => {
    currentTab.value = 'info'
    await loadData(true)
  },
)

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
  await loadData()
}

const handleMetadataSynced = async () => {
  // Force reload to get fresh data from the server
  if (book.value?.title_id) {
    const data = await titleStore.fetchTitleById(book.value.title_id, true)
    if (data) {
      title.value = data
    }
  }
}
</script>
