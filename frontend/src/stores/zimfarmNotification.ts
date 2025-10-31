import constants from '@/constants'
import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { ZimfarmNotification, ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { inject, ref } from 'vue'
import type { VueCookies } from 'vue-cookies'

export const useZimfarmNotificationStore = defineStore('zimfarm-notification', () => {
  const $cookies = inject<VueCookies>('$cookies')
  const zimfarmNotification = ref<ZimfarmNotification | null>(null)
  const errors = ref<string[]>([])
  const zimfarmNotifications = ref<ZimfarmNotificationLight[]>([])
  const limit = Number($cookies?.get('zimfarm-notifications-table-limit') || 20)
  const paginator = ref<Paginator>({
    page: 1,
    page_size: limit,
    skip: 0,
    limit: limit,
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
    has_errored: boolean | undefined = undefined,
    is_processed: boolean | undefined = undefined,
    received_after: string | undefined = undefined,
    received_before: string | undefined = undefined,
  ) => {
    const service = await authStore.getApiService('zimfarm-notifications')
    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        has_book,
        has_errored,
        is_processed,
        received_after,
        received_before,
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
    $cookies?.set('zimfarm-notifications-table-limit', limit, constants.COOKIE_LIFETIME_EXPIRY)
  }

  return {
    // State
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
