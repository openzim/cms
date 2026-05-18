import { useAuthStore } from '@/stores/auth'
import type { ListResponse } from '@/types/base'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useWarehouseStore = defineStore('warehouse', () => {
  const warehouses = ref<string[]>([])
  const error = ref<Error | null>(null)

  const authStore = useAuthStore()

  const fetchWarehouses = async (limit: number = 100) => {
    try {
      const service = await authStore.getApiService('warehouses')
      const response = await service.get<null, ListResponse<string>>('', { params: { limit } })
      warehouses.value = response.items
      return warehouses.value
    } catch (_error) {
      console.error('Failed to fetch warehouses', _error)
      error.value = _error as Error
      return null
    }
  }

  return {
    warehouses,
    error,
    fetchWarehouses,
  }
})
