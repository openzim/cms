import { useAuthStore } from '@/stores/auth'
import type { ListResponse } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { ApplicationPublication, PublicationCreate } from '@/types/publication'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePublicationStore = defineStore('publication', () => {
  const errors = ref<string[]>([])
  const authStore = useAuthStore()

  const fetchPublications = async (
    name: string,
    store: string,
    refresh = false,
  ): Promise<ApplicationPublication[] | null> => {
    const service = await authStore.getApiService('publications')
    try {
      const params: Record<string, string | number> = {
        name,
        store,
        limit: 200,
      }
      if (refresh) {
        params.refresh = 'true'
      }
      const response = await service.get<null, ListResponse<ApplicationPublication>>('', {
        params,
      })
      errors.value = []
      return response.items
    } catch (_error) {
      console.error('Failed to fetch publications', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const publish = async (
    titleId: string,
    payload: PublicationCreate,
  ): Promise<ApplicationPublication | null> => {
    const service = await authStore.getApiService('publications')
    try {
      const response = await service.post<
        PublicationCreate & { title_identifier: string },
        ApplicationPublication
      >('', { ...payload, title_identifier: titleId })
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to trigger publication', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  return { errors, fetchPublications, publish }
})
