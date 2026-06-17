<template>
  <v-dialog v-model="dialogModel" max-width="800" persistent>
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5">Select Recipe</span>
        <v-btn icon="mdi-close" variant="text" @click="closeDialog" />
      </v-card-title>

      <v-card-text class="pa-4">
        <RecipesFilter
          v-if="!loading"
          :filters="filters"
          @filters-changed="handleFiltersChange"
          @clear-filters="clearFilters"
        />

        <div v-if="recipes.length > 0" class="d-flex justify-end gap-2">
          <v-btn variant="text" @click="closeDialog"> Cancel </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :disabled="!selectedRecipeData"
            @click="confirmSelection"
          >
            Select Recipe
          </v-btn>
        </div>
        <RecipesTable
          v-if="!loading"
          :recipes="recipes"
          :paginator="paginator"
          :loading="loadingStore.isLoading"
          :loading-text="loadingStore.loadingText"
          :errors="errors"
          :selected-recipes="selectedRecipe"
          :show-selection="false"
          :disable-navigation="true"
          @limit-changed="handleLimitChange"
          @load-data="loadData"
          @selection-changed="handleSelectionChange"
          @row-clicked="handleRowClick"
        />
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4" v-if="recipes.length > 0">
        <v-spacer />
        <v-btn variant="text" @click="closeDialog"> Cancel </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :disabled="!selectedRecipeData"
          @click="confirmSelection"
        >
          Select Recipe
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import RecipesFilter from '@/components/RecipesFilter.vue'
import RecipesTable from '@/components/RecipesTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useZimfarmRecipeStore } from '@/stores/zimfarmRecipe'
import type { ZimfarmRecipeLight } from '@/types/zimfarmRecipe'
import type { Paginator } from '@/types/base'
import { computed, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  recipeSelected: [recipeId: string, recipeName: string]
}>()

const recipes = ref<ZimfarmRecipeLight[]>([])
const loading = ref<boolean>(true)
const errors = ref<string[]>([])
const filters = ref({
  name: '',
})
const selectedRecipe = ref<string[]>([])

const zimfarmRecipeStore = useZimfarmRecipeStore()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()

const paginator = ref<Paginator>({
  page: 1,
  page_size: zimfarmRecipeStore.defaultLimit,
  skip: 0,
  limit: zimfarmRecipeStore.defaultLimit,
  count: 0,
})

const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const selectedRecipeData = computed(() => {
  if (selectedRecipe.value.length === 0) return null
  return recipes.value.find((r) => r.id === selectedRecipe.value[0])
})

async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching recipes...')
  }

  await zimfarmRecipeStore.fetchZimfarmRecipes(limit, skip, filters.value.name || undefined)

  recipes.value = zimfarmRecipeStore.zimfarmRecipes
  paginator.value = zimfarmRecipeStore.paginator
  errors.value = zimfarmRecipeStore.errors

  for (const error of errors.value) {
    notificationStore.showError(error)
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

async function handleFiltersChange(newFilters: typeof filters.value) {
  filters.value = newFilters
  selectedRecipe.value = []
  await loadData(paginator.value.limit, 0)
}

async function handleLimitChange(newLimit: number) {
  await loadData(newLimit, 0)
}

async function clearFilters() {
  filters.value = {
    name: '',
  }
  selectedRecipe.value = []
  await loadData(paginator.value.limit, 0)
}

function handleSelectionChange(selection: string[]) {
  selectedRecipe.value = selection
}

function handleRowClick(item: ZimfarmRecipeLight) {
  if (selectedRecipe.value.includes(item.id)) {
    selectedRecipe.value = []
  } else {
    selectedRecipe.value = [item.id]
  }
}

function closeDialog() {
  dialogModel.value = false
  selectedRecipe.value = []
  filters.value = {
    name: '',
  }
}

function confirmSelection() {
  if (selectedRecipeData.value) {
    emit('recipeSelected', selectedRecipeData.value.id, selectedRecipeData.value.name)
    closeDialog()
  }
}

// Watch for dialog open to load and reset state
watch(dialogModel, async (newValue) => {
  if (newValue) {
    selectedRecipe.value = []
    filters.value = {
      name: '',
    }
    loading.value = false
  }
})
</script>
