import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { CollectionLight, Collection, CollectionUpdate } from '@/types/collections'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useCollectionsStore = defineStore('collection', () => {
  const errors = ref<string[]>([])
  const collection = ref<Collection | null>(null)
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

  const fetchCollections = async (limit: number = 20, skip: number = 0, name?: string) => {
    const service = await authStore.getApiService('collections')
    // filter out undefined/falsy string values
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        name,
      }).filter(([, value]) => !!value || value === 0),
    )
    try {
      const response = await service.get<null, ListResponse<CollectionLight>>('', {
        params: cleanedParams,
      })
      errors.value = []
      collections.value = response.items
      paginator.value = response.meta
      return collections.value
    } catch (_error) {
      console.error('Failed to fetch collections', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      collections.value = []
      paginator.value = {
        page: 1,
        page_size: defaultLimit.value,
        skip: 0,
        limit: defaultLimit.value,
        count: 0,
      }
      return null
    }
  }

  const fetchCollection = async (name: string, forceReload: boolean = false) => {
    const service = await authStore.getApiService('collections')
    if (!forceReload && collection.value && collection.value.name == name) {
      return collection.value
    }
    try {
      const response = await service.get<null, Collection>(`/${name}`)
      errors.value = []
      collection.value = null
      collection.value = response
    } catch (_error) {
      console.error('Failed to fetch collection', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }

    return collection.value
  }

  const createCollection = async (payload: {
    name: string
    warehouse_name: string
    download_base_url?: string
    view_base_url?: string
    article_count_increase_threshold?: number
    article_count_decrease_threshold?: number
    media_count_increase_threshold?: number
    media_count_decrease_threshold?: number
  }) => {
    const service = await authStore.getApiService('collections')
    try {
      const response = await service.post<
        {
          name: string
          warehouse_name: string
          download_base_url?: string
          view_base_url?: string
          article_count_increase_threshold?: number
          article_count_decrease_threshold?: number
          media_count_increase_threshold?: number
          media_count_decrease_threshold?: number
        },
        Collection
      >('', payload)
      errors.value = []
      return response
    } catch (error) {
      console.error('Failed to create collection', error)
      errors.value = translateErrors(error as ErrorResponse)
      return null
    }
  }

  const updateCollection = async (
    collectionId: string,
    collectionData: Partial<CollectionUpdate>,
  ) => {
    const service = await authStore.getApiService('collections')
    try {
      errors.value = []
      const response = await service.patch<CollectionUpdate, Collection>(
        `/${collectionId}`,
        collectionData,
      )
      return response
    } catch (_error) {
      console.error('Failed to update collection', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      throw _error
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
    fetchCollection,
    updateCollection,
    createCollection,
    savePaginatorLimit,
  }
})
