import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { CollectionLight } from '@/types/collections'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useCollectionsStore = defineStore('collection', () => {
  const errors = ref<string[]>([])
  const collections = ref<CollectionLight[]>([])
  const defaultLimit = ref<number>(Number(localStorage.getItem('collections-table-limit') || 20))
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchCollections = async (limit: number = 20, skip: number = 0) => {
    const service = await authStore.getApiService('collections')
    try {
      const response = await service.get<null, ListResponse<CollectionLight>>('', {
        params: { skip, limit },
      })
      collections.value = response.items
      paginator.value = response.meta
      errors.value = []
      return collections.value
    } catch (_error) {
      console.error('Failed to fetch collections', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('colle-table-limit', limit.toString())
  }

  return {
    // State
    defaultLimit,
    collections,
    paginator,
    errors,
    // Actions
    fetchCollections,
    savePaginatorLimit,
  }
})
