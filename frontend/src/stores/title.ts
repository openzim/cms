import constants from '@/constants'
import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { Title, TitleCreate, TitleLight } from '@/types/title'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { inject, ref } from 'vue'
import type { VueCookies } from 'vue-cookies'

export const useTitleStore = defineStore('title', () => {
  const $cookies = inject<VueCookies>('$cookies')
  const title = ref<Title | null>(null)
  const errors = ref<string[]>([])
  const titles = ref<TitleLight[]>([])
  const limit = Number($cookies?.get('titles-table-limit') || 20)
  const paginator = ref<Paginator>({
    page: 1,
    page_size: limit,
    skip: 0,
    limit: limit,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchTitle = async (titleName: string, forceReload: boolean = false) => {
    const service = await authStore.getApiService('titles')
    // Check if we already have the title and don't need to force reload
    if (!forceReload && title.value && title.value.name === titleName) {
      return title.value
    }

    try {
      errors.value = []
      // Clear current title until we receive the right one
      title.value = null

      const response = await service.get<null, Title>(`/${titleName}`)
      title.value = response
    } catch (_error) {
      console.error('Failed to load title', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
    return title.value
  }

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

  const fetchTitles = async (limit: number, skip: number, name: string | undefined) => {
    const service = await authStore.getApiService('titles')
    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        name,
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

  const savePaginatorLimit = (limit: number) => {
    $cookies?.set('titles-table-limit', limit, constants.COOKIE_LIFETIME_EXPIRY)
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

  return {
    // State
    title,
    titles,
    paginator,
    errors,
    // Actions
    fetchTitle,
    fetchTitleById,
    fetchTitles,
    savePaginatorLimit,
    createTitle,
  }
})
