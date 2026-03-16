import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { EventLight } from '@/types/event'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEventStore = defineStore('event', () => {
  const errors = ref<string[]>([])
  const events = ref<EventLight[]>([])
  const defaultLimit = ref<number>(Number(localStorage.getItem('events-table-limit') || 20))
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchEvents = async (limit: number, skip: number, topic?: string) => {
    const service = await authStore.getApiService('events')
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        topic,
      }).filter(
        ([name, value]) => !!value || (!['limit', 'skip'].includes(name) && value !== undefined),
      ),
    )
    try {
      const response = await service.get<null, ListResponse<EventLight>>('', {
        params: cleanedParams,
      })
      events.value = response.items
      paginator.value = response.meta
      errors.value = []
      return events.value
    } catch (_error) {
      console.error('Failed to fetch events', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('events-table-limit', limit.toString())
  }

  return {
    // State
    defaultLimit,
    events,
    paginator,
    errors,
    // Actions
    fetchEvents,
    savePaginatorLimit,
  }
})
