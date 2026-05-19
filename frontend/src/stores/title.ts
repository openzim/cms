import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { Title, TitleCreate, TitleLight, TitleUpdate } from '@/types/title'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTitleStore = defineStore('title', () => {
  const title = ref<Title | null>(null)
  const errors = ref<string[]>([])
  const titles = ref<TitleLight[]>([])
  const defaultLimit = ref<number>(Number(localStorage.getItem('titles-table-limit') || 20))
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchTitleById = async (titleId: string, forceReload: boolean = false) => {
    const service = await authStore.getApiService('titles')
    // Check if we already have the title and don't need to force reload
    if (!forceReload && title.value && title.value.id === titleId) {
      return title.value
    }

    try {
      errors.value = []
      // Clear current title until we receive the right one
      title.value = null

      const response = await service.get<null, Title>(`/${titleId}`)
      title.value = response
    } catch (_error) {
      console.error('Failed to load title', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
    return title.value
  }

  const fetchTitles = async (
    limit: number,
    skip: number,
    name: string | undefined,
    collection_name: string | undefined,
    archived: boolean = false,
  ) => {
    const service = await authStore.getApiService('titles')
    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        name,
        collection_name,
        archived: archived || undefined,
      }).filter(([, value]) => !!value),
    )
    try {
      const response = await service.get<null, ListResponse<TitleLight>>('', {
        params: cleanedParams,
      })
      titles.value = response.items
      paginator.value = response.meta
      errors.value = []
      return titles.value
    } catch (_error) {
      console.error('Failed to fetch titles', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const countTitles = async (
    name: string | undefined,
    collection_name: string | undefined,
    archived: boolean = false,
  ): Promise<number> => {
    const service = await authStore.getApiService('titles')
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit: 1,
        skip: 0,
        name,
        collection_name,
        archived: archived || undefined,
      }).filter(([, value]) => !!value),
    )
    try {
      const response = await service.get<null, ListResponse<TitleLight>>('', {
        params: cleanedParams,
      })
      return response.meta.count
    } catch (_error) {
      console.error('Failed to count titles', _error)
      return 0
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('limit-table-limit', limit.toString())
  }

  const createTitle = async (titleData: TitleCreate) => {
    const service = await authStore.getApiService('titles')
    try {
      errors.value = []
      const response = await service.post<TitleCreate, TitleLight>('', titleData)
      return response
    } catch (_error) {
      console.error('Failed to create title', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      throw _error
    }
  }

  const updateTitle = async (titleId: string, titleData: Partial<TitleUpdate>) => {
    const service = await authStore.getApiService('titles')
    try {
      errors.value = []
      const response = await service.patch<TitleUpdate, TitleLight>(`/${titleId}`, titleData)
      return response
    } catch (_error) {
      console.error('Failed to update title', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      throw _error
    }
  }

  const archiveTitle = async (titleName: string) => {
    const service = await authStore.getApiService('titles')
    try {
      await service.patch<null, TitleLight>(`/${titleName}/archive`)
      return true
    } catch (_error) {
      console.error('Failed to archive title', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return false
    }
  }

  const restoreTitle = async (titleName: string) => {
    const service = await authStore.getApiService('titles')
    try {
      await service.patch<null, TitleLight>(`/${titleName}/restore`)
      return true
    } catch (_error) {
      console.error('Failed to restore title', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return false
    }
  }

  const archiveTitles = async (titleNames: string[]) => {
    const service = await authStore.getApiService('titles')
    try {
      await service.post<{ title_names: string[] }, null>('/archive', {
        title_names: titleNames,
      })
      return true
    } catch (_error) {
      console.error('Failed to archive titles', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return false
    }
  }

  const restoreTitles = async (titleNames: string[]) => {
    const service = await authStore.getApiService('titles')
    try {
      await service.post<{ title_names: string[] }, null>('/restore', {
        title_names: titleNames,
      })
      return true
    } catch (_error) {
      console.error('Failed to restore titles', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return false
    }
  }

  return {
    // State
    title,
    titles,
    defaultLimit,
    paginator,
    errors,
    // Actions
    fetchTitleById,
    fetchTitles,
    countTitles,
    savePaginatorLimit,
    createTitle,
    updateTitle,
    archiveTitle,
    restoreTitle,
    archiveTitles,
    restoreTitles,
  }
})
