import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { ErrorResponse } from '@/types/errors'
import type { ZimfarmRecipeLight, ZimfarmRecipeUpdate, ZimfarmRecipe } from '@/types/zimfarmRecipe'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useZimfarmRecipeStore = defineStore('zimfarm-recipe', () => {
  const zimfarmRecipe = ref<ZimfarmRecipe | null>(null)
  const errors = ref<string[]>([])
  const zimfarmRecipes = ref<ZimfarmRecipeLight[]>([])
  const defaultLimit = ref<number>(
    Number(localStorage.getItem('zimfarm-recipes-table-limit') || 20),
  )
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchZimfarmRecipe = async (recipeId: string, forceReload: boolean = false) => {
    const service = await authStore.getApiService('recipes')
    if (!forceReload && zimfarmRecipe.value && zimfarmRecipe.value.id === recipeId) {
      return zimfarmRecipe.value
    }

    try {
      errors.value = []
      // Clear current book until we receive the right one
      zimfarmRecipe.value = null

      const response = await service.get<null, ZimfarmRecipe>(`/${recipeId}`)
      zimfarmRecipe.value = response
    } catch (_error) {
      console.error('Failed to load recipe', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
    return zimfarmRecipe.value
  }

  const fetchZimfarmRecipes = async (
    limit: number,
    skip: number,
    name: string | undefined = undefined,
  ) => {
    const service = await authStore.getApiService('recipes')
    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        name,
      }).filter(
        ([name, value]) => !!value || (!['limit', 'skip'].includes(name) && value !== undefined),
      ),
    )
    try {
      const response = await service.get<null, ListResponse<ZimfarmRecipeLight>>('', {
        params: cleanedParams,
      })
      zimfarmRecipes.value = response.items
      paginator.value = response.meta
      errors.value = []
      return zimfarmRecipes.value
    } catch (_error) {
      console.error('Failed to fetch zimfarm recipes', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const updateZimfarmRecipe = async (recipe: string, recipeData: ZimfarmRecipeUpdate) => {
    const service = await authStore.getApiService('recipes')
    try {
      errors.value = []
      await service.put<ZimfarmRecipeUpdate, null>(`/${recipe}`, recipeData)
      return true
    } catch (_error) {
      console.error('Failed to update recipe', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return false
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('zimfarm-recipes-table-limit', limit.toString())
  }

  return {
    // State
    defaultLimit,
    zimfarmRecipe,
    zimfarmRecipes,
    paginator,
    errors,
    // Actions
    fetchZimfarmRecipes,
    fetchZimfarmRecipe,
    savePaginatorLimit,
    updateZimfarmRecipe,
  }
})
