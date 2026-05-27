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
                    <div class="text-subtitle-2">Flavours</div>
                  </v-col>
                  <v-col cols="12" md="9">
                    <div v-if="title.flavours && title.flavours.length > 0">
                      <v-chip
                        v-for="flavour in title.flavours"
                        :key="flavour"
                        size="small"
                        variant="outlined"
                        color="primary"
                        class="mr-2 mb-1"
                      >
                        {{ flavour }}
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
  </v-container>
</template>

<script setup lang="ts">
import BookTable from '@/components/BookTable.vue'
import EventsList from '@/components/EventsList.vue'
import ArchiveTitle from '@/components/ArchiveTitle.vue'
import TitleForm from '@/components/TitleForm.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useBookStore } from '@/stores/book'
import { useAuthStore } from '@/stores/auth'
import type { Title } from '@/types/title'
import type { Book, ZimUrl } from '@/types/book'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'

const router = useRouter()

const loadingStore = useLoadingStore()
const titleStore = useTitleStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

const { smAndDown } = useDisplay()

const error = ref<string | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)
const loadingUrls = ref(false)
const zimUrls = ref<Record<string, ZimUrl[]>>({})
const latestBook = ref<Book | null>(null)

// Edit form state
const titleFormRef = ref<InstanceType<typeof TitleForm>>()
const formValid = ref(false)
const hasChanges = ref(false)
const updating = ref(false)
const updateError = ref('')

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

const loadData = async (forceReload: boolean = false) => {
  loadingStore.startLoading('Fetching title...')

  const data = await titleStore.fetchTitleById(props.id, forceReload)
  if (data) {
    error.value = null
    title.value = data
    dataLoaded.value = true
  } else {
    error.value = 'Failed to load title'
    for (const err of titleStore.errors) {
      notificationStore.showError(err)
    }
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }

  if (title.value?.books && title.value.books.length > 0) {
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
    for (const err of bookStore.errors) {
      notificationStore.showError(err)
    }
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
    for (const error of titleStore.errors) {
      notificationStore.showError(error)
    }
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
    for (const error of titleStore.errors) {
      notificationStore.showError(error)
    }
  }
}

const handleUpdate = async () => {
  if (!formValid.value || !title.value) return

  updating.value = true
  updateError.value = ''

  try {
    const updatePayload = titleFormRef.value?.getUpdatePayload()

    if (!updatePayload) {
      throw new Error('Failed to get update payload')
    }

    const response = await titleStore.updateTitle(title.value.id, updatePayload)
    if (!response) {
      updateError.value = titleStore.errors.join(', ') || 'Failed to update title'
      return
    }
    notificationStore.showSuccess('Title updated successfully!')

    // If the name changed, navigate to the new URL
    if (response.name !== props.id) {
      await router.push({ name: 'title-detail', params: { id: response.name } })
    }

    await loadData(true)
    currentTab.value = 'details'
  } catch (err) {
    console.error('Failed to update title', err)
    updateError.value = titleStore.errors.join(', ') || 'Failed to update title'
  } finally {
    updating.value = false
  }
}

const handleReset = () => {
  if (!title.value) return
  titleFormRef.value?.resetFormToTitle(title.value)
}

onMounted(async () => {
  await loadData(true)
  if (props.selectedTab === 'edit' && title.value) {
    await titleFormRef.value?.fetchCollections()
    await titleFormRef.value?.fetchFlavours()
    await loadLatestBook()
    titleFormRef.value?.resetFormToTitle(title.value)
  }
})

// Watch for tab changes
watch(
  () => props.selectedTab,
  async (newTab) => {
    currentTab.value = newTab

    if (!title.value || newTab != 'archive') {
      await loadData(true)
    }

    if (newTab === 'edit' && title.value) {
      await titleFormRef.value?.fetchCollections()
      await titleFormRef.value?.fetchFlavours()
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
