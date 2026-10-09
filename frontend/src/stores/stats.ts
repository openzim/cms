import { useAuthStore } from '@/stores/auth'
import type { ListResponse } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { TitleFlavourDownloads } from '@/types/stats'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useStatsStore = defineStore('stats', () => {
  const errors = ref<string[]>([])
  const authStore = useAuthStore()

  const fetchTitleDownloads = async (
    titleId: string,
    from?: string,
    to?: string,
  ): Promise<TitleFlavourDownloads[]> => {
    const service = await authStore.getApiService('stats')
    const cleanedParams = Object.fromEntries(
      Object.entries({ from, to }).filter(([, value]) => value !== undefined),
    )
    try {
      const response = await service.get<null, ListResponse<TitleFlavourDownloads>>(
        `/titles/${titleId}/downloads`,
        { params: cleanedParams },
      )
      errors.value = []
      return response.items
    } catch (_error) {
      console.error('Failed to fetch title download stats', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return []
    }
  }

  return {
    // State
    errors,
    // Actions
    fetchTitleDownloads,
  }
})
