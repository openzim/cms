<!-- View showing a single title -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && title">
      <div class="d-flex justify-end mb-4" v-if="canEditTitle">
        <v-btn color="primary" prepend-icon="mdi-pencil" @click="openEditDialog">
          Edit Title
        </v-btn>
      </div>

      <div>
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
            <span v-else class="text-grey">This title is not published in any collection</span>
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
            <v-data-table
              v-if="title.books.length > 0"
              :headers="bookHeaders"
              :items="sortedBooks"
              :items-per-page="-1"
              :mobile="smAndDown"
              density="compact"
              hide-default-footer
            >
              <template #[`item.created_at`]="{ item }">
                <TimestampLink :id="item.id" :route="'book-detail'" :timestamp="item.created_at" />
              </template>

              <template #[`item.status`]="{ item }">
                <BookStatus :book="item" :icon-only="true" />
              </template>

              <template #[`item.name`]="{ item }">
                <span v-if="item.name">{{ item.name }}</span>
                <span v-else class="text-grey">-</span>
              </template>

              <template #[`item.date`]="{ item }">
                <span v-if="item.date">{{ item.date }}</span>
                <span v-else class="text-grey">-</span>
              </template>

              <template #[`item.flavour`]="{ item }">
                <span v-if="item.flavour">{{ item.flavour }}</span>
                <span v-else class="text-grey">-</span>
              </template>

              <template #[`item.urls`]="{ item }">
                <ZimUrlButtons
                  :urls="zimUrls[item.id]"
                  :loading="loadingUrls"
                  :compact="true"
                  empty-text=""
                />
              </template>
            </v-data-table>
            <span v-else class="text-grey">No books</span>
          </v-col>
        </v-row>
      </div>
    </div>

    <EditTitleDialog v-model="editDialogOpen" :title="title" @updated="handleTitleUpdated" />
  </v-container>
</template>

<script setup lang="ts">
import BookStatus from '@/components/BookStatus.vue'
import EditTitleDialog from '@/components/EditTitleDialog.vue'
import EventsList from '@/components/EventsList.vue'
import TimestampLink from '@/components/TimestampLink.vue'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useBookStore } from '@/stores/book'
import { useAuthStore } from '@/stores/auth'
import type { Title } from '@/types/title'
import type { ZimUrl } from '@/types/book'
import { computed, onMounted, ref } from 'vue'
import { useDisplay } from 'vuetify'
import { useRouter } from 'vue-router'

const { smAndDown } = useDisplay()
const router = useRouter()

const loadingStore = useLoadingStore()
const titleStore = useTitleStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

const error = ref<string | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)
const editDialogOpen = ref(false)
const loadingUrls = ref(false)
const zimUrls = ref<Record<string, ZimUrl[]>>({})

interface Props {
  id: string
}

const props = withDefaults(defineProps<Props>(), {})

const bookHeaders = [
  { title: 'Created', value: 'created_at', sortable: false },
  { title: 'Name', value: 'name', sortable: false },
  { title: 'Flavour', value: 'flavour', sortable: false },
  { title: 'Status', value: 'status', sortable: false },
  { title: 'Date', value: 'date', sortable: false },
  { title: 'URLs', value: 'urls', sortable: false },
]

const canEditTitle = computed(() => authStore.hasPermission('title', 'update'))

const sortedBooks = computed(() => {
  if (!title.value?.books) return []
  return [...title.value.books].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

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

onMounted(async () => {
  await loadData()
})

const openEditDialog = () => {
  editDialogOpen.value = true
}

const handleTitleUpdated = async (updatedTitle: { id: string; name: string }) => {
  notificationStore.showSuccess('Title updated successfully!')

  // If the name changed, navigate to the new URL
  if (updatedTitle.name !== props.id) {
    await router.push({ name: 'title-detail', params: { id: updatedTitle.name } })
  }
  await loadData(true)
}
</script>
