import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { ZimfarmNotification, ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useZimfarmNotificationStore = defineStore('zimfarm-notification', () => {
  const zimfarmNotification = ref<ZimfarmNotification | null>(null)
  const errors = ref<string[]>([])
  const zimfarmNotifications = ref<ZimfarmNotificationLight[]>([])
  const defaultLimit = ref<number>(
    Number(localStorage.getItem('zimfarm-notifications-table-limit') || 20),
  )
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchZimfarmNotification = async (
    zimfarmNotificationId: string,
    forceReload: boolean = false,
  ) => {
    const service = await authStore.getApiService('zimfarm-notifications')
    // Check if we already have the zimfarm notification and don't need to force reload
    if (
      !forceReload &&
      zimfarmNotification.value &&
      zimfarmNotification.value.id === zimfarmNotificationId
    ) {
      return zimfarmNotification.value
    }

    try {
      errors.value = []
      // Clear current zimfarm notification until we receive the right one
      zimfarmNotification.value = null

      const response = await service.get<null, ZimfarmNotification>(`/${zimfarmNotificationId}`)
      zimfarmNotification.value = response
    } catch (_error) {
      console.error('Failed to load zimfarm notification', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
    return zimfarmNotification.value
  }

  const fetchZimfarmNotifications = async (
    limit: number,
    skip: number,
    has_book: boolean | undefined = undefined,
    status: string | undefined = undefined,
    received_after: string | undefined = undefined,
    received_before: string | undefined = undefined,
    id: string | undefined = undefined,
  ) => {
    const service = await authStore.getApiService('zimfarm-notifications')
    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        has_book,
        status,
        received_after,
        received_before,
        id,
      }).filter(
        ([name, value]) => !!value || (!['limit', 'skip'].includes(name) && value !== undefined),
      ),
    )
    try {
      const response = await service.get<null, ListResponse<ZimfarmNotification>>('', {
        params: cleanedParams,
      })
      zimfarmNotifications.value = response.items
      paginator.value = response.meta
      errors.value = []
      return zimfarmNotifications.value
    } catch (_error) {
      console.error('Failed to fetch zimfarm notifications', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('zimfarm-notifications-table-limit', limit.toString())
  }

  return {
    // State
    defaultLimit,
    zimfarmNotification,
    zimfarmNotifications,
    paginator,
    errors,
    // Actions
    fetchZimfarmNotification,
    fetchZimfarmNotifications,
    savePaginatorLimit,
  }
})
