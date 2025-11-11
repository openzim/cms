<!-- View showing a single title -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && title">
      <v-table>
        <tbody>
          <tr>
            <th class="text-left" style="width: 200px">Id</th>
            <td>
              <code>{{ title.id }}</code>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Name</th>
            <td>
              {{ title.name }}
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Producer</th>
            <td>
              <span v-if="title.producer_display_name && title.producer_display_url">
                <a :href="title.producer_display_url" target="_blank" rel="noopener noreferrer">
                  {{ title.producer_display_name }}
                </a>
                (<code>{{ title.producer_unique_id }}</code
                >)
              </span>
              <code v-else>{{ title.producer_unique_id }}</code>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Dev Warehouse Paths</th>
            <td>
              <div v-if="title.dev_warehouse_paths && title.dev_warehouse_paths.length > 0">
                <div
                  v-for="path in title.dev_warehouse_paths"
                  :key="`dev-${path.path_id}`"
                  class="mb-2"
                >
                  {{ path.warehouse_name }}: {{ path.folder_name }}
                </div>
              </div>
              <span v-else class="text-grey">No dev warehouse paths</span>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Prod Warehouse Paths</th>
            <td>
              <div v-if="title.prod_warehouse_paths && title.prod_warehouse_paths.length > 0">
                <div
                  v-for="path in title.prod_warehouse_paths"
                  :key="`prod-${path.path_id}`"
                  class="mb-2"
                >
                  {{ path.warehouse_name }}: {{ path.folder_name }}
                </div>
              </div>
              <span v-else class="text-grey">No prod warehouse paths</span>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">In Production</th>
            <td>
              {{ title.in_prod ? 'Yes' : 'No' }}
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">
              Events
              <v-btn
                v-if="title.events.length > 0"
                size="small"
                variant="outlined"
                class="ml-2"
                @click="copyToClipboard(title.events.join('\n'))"
              >
                <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                Copy
              </v-btn>
            </th>
            <td class="py-2">
              <pre v-for="event in title.events" :key="event">{{ event }}</pre>
              <span v-if="title.events.length == 0" class="text-grey">No events</span>
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">Books</th>
            <td class="py-2">
              <v-data-table
                v-if="title.books.length > 0"
                :headers="bookHeaders"
                :items="sortedBooks"
                :items-per-page="-1"
                density="compact"
                class="table-borderless"
                hide-default-footer
              >
                <template #[`item.id`]="{ item }">
                  <router-link :to="{ name: 'book-detail', params: { id: item.id } }">
                    <code>{{ item.id }}</code>
                  </router-link>
                </template>

                <template #[`item.created_at`]="{ item }">
                  <v-tooltip location="bottom">
                    <template #activator="{ props }">
                      <span v-bind="props">
                        {{ fromNow(item.created_at) }}
                      </span>
                    </template>
                    <span>{{ formatDt(item.created_at) }}</span>
                  </v-tooltip>
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
              </v-data-table>
              <span v-else class="text-grey">No books</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>
  </v-container>
</template>

<script setup lang="ts">
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import type { Title } from '@/types/title'
import { formatDt, fromNow } from '@/utils/format'
import { computed, onMounted, ref } from 'vue'

const loadingStore = useLoadingStore()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const error = ref<string | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)

interface Props {
  id: string
}

const props = withDefaults(defineProps<Props>(), {})

const bookHeaders = [
  { title: 'Created', value: 'created_at', sortable: true },
  { title: 'Name', value: 'name', sortable: true },
  { title: 'Flavour', value: 'flavour', sortable: true },
  { title: 'Date', value: 'date', sortable: true },
  { title: 'Status', value: 'status', sortable: true },
  { title: 'ID', value: 'id', sortable: false },
]

const sortedBooks = computed(() => {
  if (!title.value?.books) return []
  return [...title.value.books].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

const loadData = async () => {
  loadingStore.startLoading('Fetching title...')

  const data = await titleStore.fetchTitleById(props.id)
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
</script>
