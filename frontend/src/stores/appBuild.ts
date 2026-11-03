import { useAuthStore } from '@/stores/auth'
import type { ListResponse } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { ApplicationBuild, AppBuildCheck, AppBuildCreate } from '@/types/appBuild'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppBuildStore = defineStore('appBuild', () => {
  const errors = ref<string[]>([])
  const authStore = useAuthStore()

  const fetchBuilds = async (name: string, store: string): Promise<ApplicationBuild[] | null> => {
    const service = await authStore.getApiService('app-builds')
    try {
      const response = await service.get<null, ListResponse<ApplicationBuild>>('', {
        params: { name, store, limit: 200 },
      })
      errors.value = []
      return response.items
    } catch (_error) {
      console.error('Failed to fetch builds', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const checkBuild = async (name: string, store: string): Promise<AppBuildCheck | null> => {
    const service = await authStore.getApiService('app-builds')
    try {
      const response = await service.get<null, AppBuildCheck>('/check', {
        params: { name, store },
      })
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to check build', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const build = async (
    titleId: string,
    payload: AppBuildCreate,
  ): Promise<ApplicationBuild | null> => {
    const service = await authStore.getApiService('app-builds')
    try {
      const response = await service.post<
        AppBuildCreate & { title_identifier: string },
        ApplicationBuild
      >('', { ...payload, title_identifier: titleId })
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to trigger build', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  return { errors, fetchBuilds, checkBuild, build }
})
