<!-- View showing a single book -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && book">
      <div>
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
            <BookStatus :book="book" />
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
    </div>
  </v-container>
</template>

<script setup lang="ts">
import BookStatus from '@/components/BookStatus.vue'
import EventsList from '@/components/EventsList.vue'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useBookStore } from '@/stores/book'
import type { Book, ZimUrl } from '@/types/book'
import { formatDt, fromNow } from '@/utils/format'
import { onMounted, ref } from 'vue'
import { useDisplay } from 'vuetify'

const { smAndDown } = useDisplay()

const loadingStore = useLoadingStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()

const error = ref<string | null>(null)
const book = ref<Book | null>(null)
const dataLoaded = ref(false)
const loadingUrls = ref(false)
const zimUrls = ref<ZimUrl[]>([])

interface Props {
  id: string
}

const props = withDefaults(defineProps<Props>(), {})

const locationHeaders = [
  { title: 'Warehouse', value: 'warehouse_name', sortable: false },
  { title: 'Folder', value: 'path', sortable: false },
  { title: 'Filename', value: 'filename', sortable: false },
]

const loadData = async () => {
  loadingStore.startLoading('Fetching book...')

  const data = await bookStore.fetchBook(props.id)
  if (data) {
    error.value = null
    book.value = data
    dataLoaded.value = true
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
  await loadData()
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
</script>
