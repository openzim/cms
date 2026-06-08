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
import type { BookLight } from '@/types/book'
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
    id: '',
    name: '',
    flavour: '',
    needs_attention: 'no',
    location_kind: '',
  }
  if (query.id && typeof query.id === 'string') {
    derived.id = query.id
  }

  if (query.name && typeof query.name === 'string') {
    derived.name = query.name
  }

  if (query.flavour && typeof query.flavour === 'string') {
    derived.flavour = query.flavour
  }

  if (query.needs_attention && typeof query.needs_attention === 'string') {
    derived.needs_attention = query.needs_attention
  }

  if (query.location_kind && typeof query.location_kind === 'string') {
    derived.location_kind = query.location_kind
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

async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching books...')
    books.value = []
  }

  // Convert needs_attention filter to boolean or undefined
  let needsAttention: boolean | undefined = undefined
  if (bookFilters.value.needs_attention === 'yes') {
    needsAttention = true
  } else if (bookFilters.value.needs_attention === 'no') {
    needsAttention = false
  }
  // 'all' or empty string maps to undefined

  // Fetch books with the selected filters
  await bookStore.fetchBooks(
    limit,
    skip,
    needsAttention,
    bookFilters.value.id || undefined,
    bookFilters.value.location_kind ? [bookFilters.value.location_kind] : undefined,
    undefined, // flag not used in this view
    bookFilters.value.name || undefined,
    bookFilters.value.flavour || undefined,
    props.hasBackup, // pass the hasBackup prop to filter by backup status
  )

  books.value = bookStore.books
  errors.value = bookStore.errors
  bookStore.savePaginatorLimit(limit)
  paginator.value = { ...bookStore.paginator }

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

function updateUrlFilters(sourceFilters: typeof bookFilters.value) {
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  if (sourceFilters.id) {
    query.id = sourceFilters.id
  }

  if (sourceFilters.name) {
    query.name = sourceFilters.name
  }

  if (sourceFilters.flavour) {
    query.flavour = sourceFilters.flavour
  }

  if (sourceFilters.needs_attention) {
    query.needs_attention = sourceFilters.needs_attention
  }

  if (sourceFilters.location_kind) {
    query.location_kind = sourceFilters.location_kind
  }

  router.push({
    name: props.routeName,
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

async function clearFilters() {
  updateUrlFilters({ id: '', name: '', flavour: '', needs_attention: '', location_kind: '' })
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
      currentFilters.id || undefined,
      currentFilters.location_kind ? [currentFilters.location_kind] : undefined,
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

  if (currentFilters.id) query.id = currentFilters.id
  if (currentFilters.name) query.name = currentFilters.name
  if (currentFilters.flavour) query.flavour = currentFilters.flavour
  if (currentFilters.location_kind) query.location_kind = currentFilters.location_kind

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
