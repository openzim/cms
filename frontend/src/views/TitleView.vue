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
            <th class="text-left" style="width: 200px">Dev Warehouse Path</th>
            <td>
              <span v-if="devWarehousePath">
                {{ devWarehousePath.warehouse_name }}: {{ devWarehousePath.folder_name }}
              </span>
              <span v-else class="text-grey">None</span>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Prod Warehouse Path</th>
            <td>
              <span v-if="prodWarehousePath">
                {{ prodWarehousePath.warehouse_name }}: {{ prodWarehousePath.folder_name }}
              </span>
              <span v-else class="text-grey">None</span>
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
              <pre v-if="title.events.length > 0" v-for="event in title.events" :key="event">{{
                event
              }}</pre>
              <span v-else class="text-grey">No events</span>
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">Books</th>
            <td class="py-2">
              <div v-if="title.books.length > 0">
                <div v-for="book in title.books" :key="book.id" class="mb-2">
                  <router-link :to="{ name: 'book-detail', params: { id: book.id } }">
                    <code>{{ book.id }}</code>
                  </router-link>
                  - Status: {{ book.status }}
                </div>
              </div>
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
import { useWarehousePathStore } from '@/stores/warehousePath'
import type { Title } from '@/types/title'
import type { WarehousePath } from '@/types/warehousePath'
import { computed, onMounted, ref } from 'vue'

const loadingStore = useLoadingStore()
const titleStore = useTitleStore()
const warehousePathStore = useWarehousePathStore()
const notificationStore = useNotificationStore()

const error = ref<string | null>(null)
const title = ref<Title | null>(null)
const dataLoaded = ref(false)

interface Props {
  id: string
}

const props = withDefaults(defineProps<Props>(), {})

const devWarehousePath = computed<WarehousePath | undefined>(() => {
  if (!title.value?.dev_warehouse_path_id) return undefined
  return warehousePathStore.warehousePaths.find(
    (wp) => wp.path_id === title.value!.dev_warehouse_path_id,
  )
})

const prodWarehousePath = computed<WarehousePath | undefined>(() => {
  if (!title.value?.prod_warehouse_path_id) return undefined
  return warehousePathStore.warehousePaths.find(
    (wp) => wp.path_id === title.value!.prod_warehouse_path_id,
  )
})

const loadData = async () => {
  loadingStore.startLoading('Fetching title...')

  // Fetch warehouse paths first
  await warehousePathStore.fetchWarehousePaths()

  // Then fetch the title
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
