import type { ErrorResponse } from '@/types/errors'
import type { Recipe, Blob, CreateBlob } from '@/types/zimfarm/recipe'
import { translateErrors } from '@/utils/errors'
import { useAuthStore } from '@/stores/auth'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useZimfarmRecipeStore = defineStore('zimfarmRecipe', () => {
  const errors = ref<string[]>([])
  const recipe = ref<Recipe | null>(null)

  const authStore = useAuthStore()

  const fetchRecipe = async (recipeId: string, forceReload: boolean = false) => {
    const service = await authStore.getZimfarmApiService('recipes')
    // Check if we already have the recipe and don't need to force reload
    if (!forceReload && recipe.value && recipe.value.id === recipeId) {
      return recipe.value
    }
    try {
      errors.value = []
      recipe.value = null
      const response = await service.get<null, Recipe>(`/${recipeId}`)
      recipe.value = response
      // generate artifacts_globs_str
      recipe.value.config.artifacts_globs_str = recipe.value.config.artifacts_globs?.join('\n')
    } catch (_error) {
      console.error('Failed to load recipe', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
    return recipe.value
  }

  const createBlob = async (recipeId: string, request: CreateBlob) => {
    try {
      const service = await authStore.getZimfarmApiService('blobs')
      const response = await service.post<CreateBlob, Blob>(`/${recipeId}`, request)
      return response
    } catch (_error) {
      console.error('Failed to create blob', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const updateRecipe = async (recipeId: string, payload: Record<string, unknown>) => {
    const service = await authStore.getZimfarmApiService('recipes')
    try {
      errors.value = []
      const response = await service.patch<Record<string, unknown>, Recipe>(`/${recipeId}`, payload)
      return response
    } catch (_error) {
      console.error('Failed to update recipe', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  return {
    // state
    recipe,
    errors,
    // actions
    fetchRecipe,
    updateRecipe,
    createBlob,
  }
})
