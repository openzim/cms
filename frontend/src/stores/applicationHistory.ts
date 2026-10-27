import { useAuthStore } from '@/stores/auth'
import type { Application, ApplicationHistory } from '@/types/application'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useApplicationHistoryStore = defineStore('applicationHistory', () => {
  const history = ref<ApplicationHistory[]>([])
  const errors = ref<string[]>([])
  const lastRevertedApplication = ref<Application | null>(null)
  const paginator = ref<Paginator>({
    page: 1,
    page_size: 20,
    skip: 0,
    limit: 20,
    count: 0,
  })

  const authStore = useAuthStore()

  const fetchHistory = async (name: string, store: string, limit: number, skip: number) => {
    const service = await authStore.getApiService('applications')
    try {
      const response = await service.get<null, ListResponse<ApplicationHistory>>(
        `/${name}/${store}/history`,
        { params: { limit, skip } },
      )
      const existingIds = new Set(history.value.map((entry) => entry.id))
      history.value = [
        ...history.value,
        ...response.items.filter((item) => !existingIds.has(item.id)),
      ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      paginator.value = response.meta
      errors.value = []
      return history.value
    } catch (_error) {
      console.error('Failed to fetch application history', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const fetchHistoryEntry = async (name: string, store: string, historyId: string) => {
    const service = await authStore.getApiService('applications')
    try {
      const response = await service.get<null, ApplicationHistory>(
        `/${name}/${store}/history/${historyId}`,
      )
      const existingIds = new Set(history.value.map((entry) => entry.id))
      if (!existingIds.has(response.id)) {
        history.value = [...history.value, response].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
      }
      errors.value = []
      return response
    } catch (_error) {
      console.error('Failed to fetch application history entry', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const revertToHistory = async (
    name: string,
    store: string,
    historyId: string,
    comment?: string,
  ) => {
    const service = await authStore.getApiService('applications')
    try {
      const data = { comment: comment ? comment : null }
      const response = await service.patch<{ comment?: string } | null, Application>(
        `/${name}/${store}/revert/${historyId}`,
        data,
      )
      lastRevertedApplication.value = response
      errors.value = []
      return response
    } catch (_error) {
      console.error(`Failed to revert to application history entry ${historyId}`, _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const clearHistory = () => {
    history.value = []
    errors.value = []
    lastRevertedApplication.value = null
    paginator.value = {
      page: 1,
      page_size: 20,
      skip: 0,
      limit: 20,
      count: 0,
    }
  }

  return {
    history,
    paginator,
    errors,
    lastRevertedApplication,
    fetchHistory,
    fetchHistoryEntry,
    clearHistory,
    revertToHistory,
  }
})
