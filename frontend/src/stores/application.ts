import { useAuthStore } from '@/stores/auth'
import type { Application, ApplicationCreate, ApplicationUpdate } from '@/types/application'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useApplicationStore = defineStore('application', () => {
  const errors = ref<string[]>([])
  const applications = ref<Application[]>([])
  const paginator = ref<Paginator>({
    page: 1,
    page_size: 50,
    skip: 0,
    limit: 50,
    count: 0,
  })
  const authStore = useAuthStore()

  const clearErrors = () => {
    errors.value = []
  }

  const fetchApplications = async (
    limit: number = paginator.value.limit,
    skip = 0,
    name?: string,
    store?: string,
  ) => {
    const service = await authStore.getApiService('applications')
    try {
      const params: Record<string, string | number> = { limit, skip }
      if (name) params.name = name
      if (store) params.store = store
      const response = await service.get<null, ListResponse<Application>>('', { params })
      applications.value = response.items
      paginator.value = response.meta
      errors.value = []
      return applications.value
    } catch (_error) {
      console.error('Failed to fetch applications', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const fetchApplication = async (name: string, store: string) => {
    const service = await authStore.getApiService('applications')
    try {
      const response = await service.get<null, Application>(`/${name}/${store}`)
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to fetch application', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const createApplication = async (payload: ApplicationCreate) => {
    const service = await authStore.getApiService('applications')
    try {
      const response = await service.post<ApplicationCreate, Application>('', payload)
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to create application', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const updateApplication = async (name: string, store: string, payload: ApplicationUpdate) => {
    const service = await authStore.getApiService('applications')
    try {
      const response = await service.patch<ApplicationUpdate, Application>(
        `/${name}/${store}`,
        payload,
      )
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to update application', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const deleteApplication = async (name: string, store: string) => {
    const service = await authStore.getApiService('applications')
    try {
      await service.delete<null, void>(`/${name}/${store}`)
      errors.value = []
      return true
    } catch (_error) {
      console.error('Failed to delete application', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return false
    }
  }

  return {
    errors,
    applications,
    clearErrors,
    paginator,
    fetchApplications,
    fetchApplication,
    createApplication,
    updateApplication,
    deleteApplication,
  }
})
