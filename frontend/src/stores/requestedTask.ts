import { useAuthStore } from '@/stores/auth'
import type { ErrorResponse } from '@/types/errors'
import { defineStore } from 'pinia'
import type { ListResponse, Paginator } from '@/types/base'
import type { RequestedTaskLight } from '@/types/requestedTask'
import { translateErrors } from '@/utils/errors'
import { ref } from 'vue'

export const useRequestedTaskStore = defineStore('requestedTask', () => {
  const errors = ref<string[]>([])
  const tasks = ref<RequestedTaskLight[]>([])
  const defaultLimit = ref<number>(Number(localStorage.getItem('tasks-table-limit') || 20))
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchTasks = async (
    limit: number,
    skip: number,
    collection_id?: string,
    status?: string[],
  ) => {
    const service = await authStore.getApiService('tasks')
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        collection_id,
        status,
      }).filter(
        ([name, value]) => !!value || (!['limit', 'skip'].includes(name) && value !== undefined),
      ),
    )
    try {
      const response = await service.get<null, ListResponse<RequestedTaskLight>>('', {
        params: cleanedParams,
      })
      tasks.value = response.items
      paginator.value = response.meta
      errors.value = []
      return tasks.value
    } catch (_error) {
      console.error('Failed to fetch task', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('tasks-table-limit', limit.toString())
    defaultLimit.value = limit
  }

  return {
    // State
    defaultLimit,
    tasks,
    paginator,
    errors,
    // Actions
    fetchTasks,
    savePaginatorLimit,
  }
})
