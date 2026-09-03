import { useAuthStore } from '@/stores/auth'
import type { ErrorResponse } from '@/types/errors'
import { defineStore } from 'pinia'
import type { ListResponse, Paginator } from '@/types/base'
import type { TitleUploadLight } from '@/types/titleUpload'
import { translateErrors } from '@/utils/errors'
import { ref } from 'vue'

export const useTitleUploadStore = defineStore('title-uploads', () => {
  const errors = ref<string[]>([])
  const titleUploads = ref<TitleUploadLight[]>([])
  const defaultLimit = ref<number>(Number(localStorage.getItem('title-uploads-table-limit') || 20))
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchTitleUploads = async (
    limit: number,
    skip: number,
    title_id: string,
    status?: string[] | null,
  ) => {
    const service = await authStore.getApiService('title-uploads')
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        title_id,
        status,
      }).filter(
        ([name, value]) => !!value || (!['limit', 'skip'].includes(name) && value !== undefined),
      ),
    )
    try {
      const response = await service.get<null, ListResponse<TitleUploadLight>>('', {
        params: cleanedParams,
      })
      titleUploads.value = response.items
      paginator.value = response.meta
      errors.value = []
      return titleUploads.value
    } catch (_error) {
      console.error('Failed to fetch title uploads', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('title-uploads-table-limit', limit.toString())
    defaultLimit.value = limit
  }

  return {
    // State
    defaultLimit,
    titleUploads,
    paginator,
    errors,
    // Actions
    fetchTitleUploads,
    savePaginatorLimit,
  }
})
