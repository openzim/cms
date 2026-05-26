<template>
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
</template>

<script setup lang="ts">
import BooksViewFilters from '@/components/BooksViewFilters.vue'
import BookTable from '@/components/BookTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useBookStore } from '@/stores/book'
import type { BookLight } from '@/types/book'
import type { Paginator } from '@/types/base'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const bookStore = useBookStore()
const loadingStore = useLoadingStore()

const flavours = ref<string[]>([])
const loadingFlavours = ref(false)

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
    needs_attention: '',
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
    name: route.name,
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

async function clearFilters() {
  updateUrlFilters({ id: '', name: '', flavour: '', needs_attention: '', location_kind: '' })
}

async function handleBookFiltersChange(newFilters: typeof bookFilters.value) {
  updateUrlFilters(newFilters)
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
  },
  { deep: true, immediate: false },
)

onMounted(async () => {
  loadingFlavours.value = true
  const fetchedFlavours = await bookStore.fetchBookFlavours()
  if (fetchedFlavours) {
    flavours.value = fetchedFlavours
  }
  loadingFlavours.value = false

  // Set default needs_attention to 'no' if not already set
  if (!route.query.needs_attention) {
    await router.replace({
      name: route.name ?? undefined,
      query: {
        ...route.query,
        needs_attention: 'no',
      },
    })
  } else {
    // Load data if needs_attention is already set
    const page = Number(route.query.page) || 1
    const newSkip = (page - 1) * paginator.value.limit
    await loadData(paginator.value.limit, newSkip)
  }

  intervalId.value = window.setInterval(async () => {
    await loadData(paginator.value.limit, paginator.value.skip, true)
  }, 60000)
})

onBeforeUnmount(() => {
  if (intervalId.value) {
    clearInterval(intervalId.value)
  }
})
</script>
