import type { ListResponse } from '@/types/base'
import type { Config } from '@/config'
import httpRequest from '@/utils/httpRequest'
import type { ErrorResponse } from '@/types/errors'
import constants from '@/constants'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { inject, ref } from 'vue'

export const useZimfarmOfflinerStore = defineStore('zimfarmOffliner', () => {
  const offliners = ref<string[]>([])
  const errors = ref<string[]>([])

  const config = inject<Config>(constants.config)

  if (!config) {
    throw new Error('Config is not defined')
  }

  const fetchOffliners = async (limit: number = 100) => {
    if (offliners.value.length > 0) {
      return offliners.value
    }
    const apiService = httpRequest({
      baseURL: `${config.ZIMFARM_API}/offliners`,
    })
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

  return {
    // state
    offliners,
    errors,
    // actions
    fetchOffliners,
  }
})
