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
            <th class="text-left" style="width: 200px">Collections</th>
            <td>
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
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Maturity</th>
            <td>
              {{ title.maturity }}
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

    <EditTitleDialog v-model="editDialogOpen" :title="title" @updated="handleTitleUpdated" />
  </v-container>
</template>

<script setup lang="ts">
import EditTitleDialog from '@/components/EditTitleDialog.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useAuthStore } from '@/stores/auth'
import type { Title } from '@/types/title'
import { formatDt, fromNow } from '@/utils/format'
import { computed, onMounted, ref } from 'vue'

const loadingStore = useLoadingStore()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

const error = ref<string | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)
const editDialogOpen = ref(false)

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

const openEditDialog = () => {
  editDialogOpen.value = true
}

const handleTitleUpdated = async () => {
  notificationStore.showSuccess('Title updated successfully!')
  await loadData(true)
}
</script>
