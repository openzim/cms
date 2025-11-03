<!-- View showing a single book -->

<template>
  <v-container>
    <!-- Loading state when data hasn't been loaded yet -->
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && book">
      <v-table>
        <tbody>
          <tr>
            <th class="text-left" style="width: 200px">Id</th>
            <td>
              <code>{{ book.id }}</code>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Title Id</th>
            <td>
              <code v-if="book.title_id">{{ book.title_id }}</code>
              <span v-else class="text-grey">None</span>
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Article Count</th>
            <td>
              {{ book.article_count.toLocaleString() }}
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Media Count</th>
            <td>
              {{ book.media_count.toLocaleString() }}
            </td>
          </tr>
          <tr>
            <th class="text-left" style="width: 200px">Size</th>
            <td>
              {{ formatBytes(book.size) }}
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">
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
            </th>
            <td class="py-2">
              <pre>{{ JSON.stringify(book.zim_metadata, null, 2) }}</pre>
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">
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
            </th>
            <td class="py-2">
              <pre>{{ JSON.stringify(book.zimcheck_result, null, 2) }}</pre>
            </td>
          </tr>
          <tr>
            <th class="text-left pa-4 align-top">
              Events
              <v-btn
                size="small"
                variant="outlined"
                class="ml-2"
                @click="copyToClipboard(book.events.join('\n'))"
              >
                <v-icon size="small" class="mr-1">mdi-content-copy</v-icon>
                Copy
              </v-btn>
            </th>
            <td class="py-2">
              <pre v-for="event in book.events" :key="event">{{ event }}</pre>
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
import { useBookStore } from '@/stores/book'
import type { Book } from '@/types/book'
import { onMounted, ref } from 'vue'

const loadingStore = useLoadingStore()
const bookStore = useBookStore()
const notificationStore = useNotificationStore()

const error = ref<string | null>(null)
const book = ref<Book | null>(null)
const dataLoaded = ref(false)

interface Props {
  id: string
}

const props = withDefaults(defineProps<Props>(), {})

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
