import type { Config } from '@/config'
import constants from '@/constants'
import httpRequest from '@/utils/httpRequest'
import { defineStore } from 'pinia'
import { inject, ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const errors = ref<string[]>([])

  const config = inject<Config>(constants.config)

  if (!config) {
    throw new Error('Config is not defined')
  }

  const getApiService = async (baseURL: string) => {
    return httpRequest({
      baseURL: `${config.CMS_API}/${baseURL}`,
    })
  }

  return {
    // State
    errors,

    // Computed

    // Methods
    getApiService,
  }
})
