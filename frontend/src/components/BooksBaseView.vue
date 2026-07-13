<template>
  <div>
    <BooksViewFilters
      :filters="bookFilters"
      :flavour-options="flavours"
      :loading-flavours="loadingFlavours"
      @filters-changed="handleBookFiltersChange"
      @clear-filters="clearFilters"
    />
    <BookTable
      :headers="headers"
      :books="books"
      :paginator="paginator"
      :loading="loadingStore.isLoading"
      :loading-text="loadingStore.loadingText"
      :errors="errors"
      :offliners="offlinerStore.offliners"
      display-mode="card"
      :show-urls="true"
      :zim-urls="zimUrls"
      :loading-urls="loadingUrls"
      @limit-changed="handleLimitChange"
      @load-data="loadData"
    />
    <div v-if="!hasBackup && canAccessBackups" class="pa-0 mt-4">
      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            variant="outlined"
            size="small"
            :loading="loadingBackupCount"
            @click="navigateToBackups"
          >
            <v-icon size="small" class="mr-2">mdi-content-copy</v-icon>
            {{ backupCountText }}
          </v-btn>
        </template>
        <span>{{ backupTooltipText }}</span>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import BooksViewFilters from '@/components/BooksViewFilters.vue'
import BookTable from '@/components/BookTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useBookStore } from '@/stores/book'
import { useAuthStore } from '@/stores/auth'
import { useZimfarmOfflinerStore } from '@/stores/zimfarm/offliner'
import type { BookLight, ZimUrl } from '@/types/book'
import type { Paginator } from '@/types/base'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

interface Props {
  routeName: string
  hasBackup?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  hasBackup: undefined,
  showBackupFilter: false,
})

const router = useRouter()
const route = useRoute()

const bookStore = useBookStore()
const loadingStore = useLoadingStore()
const authStore = useAuthStore()
const offlinerStore = useZimfarmOfflinerStore()

const flavours = ref<string[]>([])
const loadingFlavours = ref(false)
const backupCount = ref(0)
const loadingBackupCount = ref(false)

// Define headers for the table
const headers = [
  { title: 'Name', value: 'name' },
  { title: 'Flavour', value: 'flavour' },
  { title: 'Status', value: 'status' },
  { title: 'Date', value: 'date' },
  { title: 'Deletion Date', value: 'deletion_date' },
]

const defaultLimit = computed(() => bookStore.defaultLimit)

const books = ref<BookLight[]>([])
const zimUrls = ref<Record<string, ZimUrl[]>>({})
const loadingUrls = ref(false)
const paginator = ref<Paginator>({
  page: Number(route.query.page) || 1,
  page_size: defaultLimit.value,
  skip: 0,
  limit: defaultLimit.value,
  count: 0,
})
const errors = ref<string[]>([])

const bookFilters = computed(() => {
  const query = router.currentRoute.value.query
  const derived = {
    name: '',
    flavour: '',
    status: 'active',
  }

  if (query.name && typeof query.name === 'string') {
    derived.name = query.name
  }

  if (query.flavour && typeof query.flavour === 'string') {
    derived.flavour = query.flavour
  }

  if (query.status && typeof query.status === 'string') {
    derived.status = query.status
  }

  return derived
})

const intervalId = ref<number | null>(null)

const canAccessBackups = computed(() => authStore.hasPermission('book', 'update'))

const backupCountText = computed(() => {
  if (loadingBackupCount.value) {
    return 'Loading...'
  }
  const count = backupCount.value
  return `BACKUPS (${count})`
})

const backupTooltipText = computed(() => {
  const count = backupCount.value
  return count === 1 ? '1 matching backup book' : `${count} matching backup books`
})

function statusToLocationKinds(status: string): string[] | undefined {
  switch (status) {
    case 'active':
      return ['quarantine', 'staging', 'prod']
    case 'quarantine':
      return ['quarantine']
    case 'staging':
      return ['staging']
    case 'prod':
      return ['prod']
    case 'to_delete':
      return ['to_delete']
    case 'deleted':
      return ['deleted']
    case 'all':
      return undefined
    default:
      return ['quarantine', 'staging', 'prod']
  }
}

async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching books...')
    books.value = []
    zimUrls.value = {}
  }

  // Fetch books with the selected filters
  await bookStore.fetchBooks(
    limit,
    skip,
    undefined,
    undefined,
    statusToLocationKinds(bookFilters.value.status),
    undefined, // flag not used in this view
    bookFilters.value.name || undefined,
    bookFilters.value.flavour || undefined,
    props.hasBackup, // pass the hasBackup prop to filter by backup status
  )

  books.value = bookStore.books
  errors.value = bookStore.errors
  bookStore.savePaginatorLimit(limit)
  paginator.value = { ...bookStore.paginator }
  await loadZimUrls()

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

async function handleLimitChange(newLimit: number) {
  bookStore.savePaginatorLimit(newLimit)

  if (paginator.value.page != 1) {
    paginator.value = {
      ...paginator.value,
      limit: newLimit,
      page: 1,
      skip: 0,
    }
  } else {
    await loadData(newLimit, 0)
  }
}

async function loadZimUrls() {
  if (!books.value || books.value.length === 0) return

  loadingUrls.value = true
  const bookIds = books.value.map((book) => book.id)

  const response = await bookStore.fetchZimUrls(bookIds)
  if (response?.urls) {
    zimUrls.value = response.urls
  } else {
    console.error('Failed to fetch zim URLs for books')
  }

  loadingUrls.value = false
}

function updateUrlFilters(sourceFilters: typeof bookFilters.value) {
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  if (sourceFilters.name) {
    query.name = sourceFilters.name
  }

  if (sourceFilters.flavour) {
    query.flavour = sourceFilters.flavour
  }

  if (sourceFilters.status && sourceFilters.status !== 'active') {
    query.status = sourceFilters.status
  }

  router.push({
    name: props.routeName,
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

async function clearFilters() {
  updateUrlFilters({ name: '', flavour: '', status: 'active' })
}

async function handleBookFiltersChange(newFilters: typeof bookFilters.value) {
  updateUrlFilters(newFilters)
}

async function fetchBackupCount() {
  if (!canAccessBackups.value || props.hasBackup) return

  loadingBackupCount.value = true
  try {
    const currentFilters = bookFilters.value
    backupCount.value = await bookStore.countBooks(
      undefined,
      undefined,
      statusToLocationKinds(currentFilters.status),
      undefined,
      currentFilters.name || undefined,
      currentFilters.flavour || undefined,
      true,
    )
  } catch (error) {
    console.error('Failed to fetch backup count', error)
    backupCount.value = 0
  } finally {
    loadingBackupCount.value = false
  }
}

function navigateToBackups() {
  const currentFilters = bookFilters.value
  const query: Record<string, string> = { needs_attention: 'all' }

  if (currentFilters.name) query.name = currentFilters.name
  if (currentFilters.flavour) query.flavour = currentFilters.flavour
  if (currentFilters.status !== 'active') query.status = currentFilters.status

  router.push({
    name: 'backup-books',
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

watch(
  () => router.currentRoute.value.query,
  async () => {
    const query = router.currentRoute.value.query
    let page = 1
    if (query.page && typeof query.page === 'string') {
      const parsedPage = parseInt(query.page, 10)
      if (!isNaN(parsedPage) && parsedPage > 1) {
        page = parsedPage
      }
    }
    const newSkip = (page - 1) * paginator.value.limit
    await loadData(paginator.value.limit, newSkip)
    // Fetch backup count when filters change
    if (!props.hasBackup) {
      await fetchBackupCount()
    }
  },
  { deep: true, immediate: true },
)

onMounted(async () => {
  await offlinerStore.fetchOffliners()
  loadingFlavours.value = true
  const fetchedFlavours = await bookStore.fetchBookFlavours()
  if (fetchedFlavours) {
    flavours.value = fetchedFlavours
  }
  loadingFlavours.value = false
  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, true)
    if (!props.hasBackup) {
      await fetchBackupCount()
    }
  }, 60000)
})

onBeforeUnmount(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
})
</script>
