import type { ListResponse } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { OfflinerDefinitionFlag, OfflinerDefinitionSpec } from '@/types/zimfarm/offliner'
import { translateErrors } from '@/utils/errors'
import { useAuthStore } from '@/stores/auth'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useZimfarmOfflinerStore = defineStore('zimfarmOffliner', () => {
  const offliners = ref<string[]>([])
  const errors = ref<string[]>([])

  const authStore = useAuthStore()

  const fetchOffliners = async (limit: number = 100) => {
    if (offliners.value.length > 0) {
      return offliners.value
    }
    const apiService = await authStore.getZimfarmApiService('offliners')
    try {
      const response = await apiService.get<null, ListResponse<string>>('', { params: { limit } })
      offliners.value = response.items
      errors.value = []
      return offliners.value
    } catch (_error) {
      console.error('Failed to fetch offliners', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const fetchOfflinerDefinitionFlag = async (offliner: string, version: string) => {
    const apiService = await authStore.getZimfarmApiService('offliners')

    try {
      const response = await apiService.get<null, OfflinerDefinitionFlag>(`/${offliner}/${version}`)
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to fetch offliner definition flags', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const fetchOfflinerDefinitionSpec = async (offliner: string, version: string) => {
    const apiService = await authStore.getZimfarmApiService('offliners')

    try {
      const response = await apiService.get<null, OfflinerDefinitionSpec>(
        `/${offliner}/${version}/spec`,
      )
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to fetch offliner definition spec', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  return {
    // state
    offliners,
    errors,
    // actions
    fetchOffliners,
    fetchOfflinerDefinitionFlag,
    fetchOfflinerDefinitionSpec,
  }
})
