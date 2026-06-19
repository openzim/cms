<template>
  <div>
    <RecipesFilter
      :filters="recipeFilters"
      @filters-changed="handleRecipeFiltersChange"
      @clear-filters="clearFilters"
    />
    <RecipesTable
      :headers="headers"
      :recipes="recipes"
      :paginator="paginator"
      :loading="loadingStore.isLoading"
      :loading-text="loadingStore.loadingText"
      :errors="errors"
      @limit-changed="handleLimitChange"
      @load-data="loadData"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'

import RecipesFilter from '@/components/RecipesFilter.vue'
import RecipesTable from '@/components/RecipesTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useZimfarmRecipeStore } from '@/stores/zimfarmRecipe'
import type { ZimfarmRecipeLight } from '@/types/zimfarmRecipe'

// Router and stores
const router = useRouter()
const route = useRoute()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()
const zimfarmRecipeStore = useZimfarmRecipeStore()

// Reactive data
const recipes = ref<ZimfarmRecipeLight[]>([])
const defaultLimit = computed(() => zimfarmRecipeStore.defaultLimit)
const errors = ref<string[]>([])

const paginator = ref({
  page: Number(route.query.page) || 1,
  page_size: defaultLimit,
  skip: 0,
  limit: defaultLimit,
  count: 0,
})

// Table headers
const headers = [
  { title: 'Id', key: 'id', sortable: false },
  { title: 'Name', key: 'name', sortable: false },
]

const recipeFilters = computed(() => {
  const query = router.currentRoute.value.query
  const derived = {
    name: '',
  }

  if (query.name && typeof query.name === 'string') {
    derived.name = query.name
  }

  return derived
})

const intervalId = ref<number | null>(null)

const loadData = async (limit: number, skip: number, hideLoading: boolean = false) => {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching recipes...')
    recipes.value = []
  }

  const response = await zimfarmRecipeStore.fetchZimfarmRecipes(
    limit,
    skip,
    recipeFilters.value.name || undefined,
  )

  if (response) {
    recipes.value = response
    paginator.value = { ...zimfarmRecipeStore.paginator }
    zimfarmRecipeStore.savePaginatorLimit(limit)
  } else {
    notificationStore.showErrors(zimfarmRecipeStore.errors)
  }
  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

const handleLimitChange = async (newLimit: number) => {
  zimfarmRecipeStore.savePaginatorLimit(newLimit)

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

function updateUrlFilters(sourceFilters: typeof recipeFilters.value) {
  // create query object from selected filters
  const query: Record<string, string | string[]> = {}

  if (sourceFilters.name) {
    query.name = sourceFilters.name
  }

  router.push({
    name: 'recipes',
    query: Object.keys(query).length > 0 ? query : undefined,
  })
}

async function clearFilters() {
  updateUrlFilters({ name: '' })
}

async function handleRecipeFiltersChange(newFilters: typeof recipeFilters.value) {
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
  { deep: true, immediate: true },
)

onMounted(async () => {
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
