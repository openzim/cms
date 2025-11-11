import { useAuthStore } from '@/stores/auth'
import type { ErrorResponse } from '@/types/errors'
import type { WarehousePath } from '@/types/warehousePath'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useWarehousePathStore = defineStore('warehousePath', () => {
  const warehousePaths = ref<WarehousePath[]>([])
  const errors = ref<string[]>([])
  const authStore = useAuthStore()

  const defaultDevPath = computed(() => {
    return warehousePaths.value.find((wp) => wp.folder_name === '/.hidden/dev')
  })

  const warehousePathOptions = computed(() =>
    warehousePaths.value.map((wp) => ({
      displayText: `${wp.warehouse_name}: ${wp.folder_name}`,
      value: wp.path_id,
    })),
  )

  const fetchWarehousePaths = async () => {
    const service = await authStore.getApiService('warehouse-paths')
    try {
      errors.value = []
      warehousePaths.value = await service.get<null, WarehousePath[]>('')
    } catch (_error) {
      console.error('Failed to fetch warehouse paths', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
  }

  return {
    // State
    warehousePaths,
    errors,
    // Computed
    defaultDevPath,
    warehousePathOptions,
    // Actions
    fetchWarehousePaths,
  }
})
