<template>
  <v-card flat>
    <v-card-text class="pa-0">
      <div v-if="loading" class="text-center pa-8">
        <v-progress-circular indeterminate size="64" />
        <div class="mt-4 text-body-1">Loading recipe information...</div>
      </div>

      <div v-if="!loading && !props.book.recipe_id && !recipeData">
        <!-- No Recipe Associated -->
        <v-card variant="elevated" class="mb-4">
          <v-card-text>
            <p class="text-body-2 mb-4">
              Browse and select the Zimfarm recipe that you want to use for this book's
              configuration.
            </p>
            <v-btn
              color="primary"
              variant="outlined"
              prepend-icon="mdi-magnify"
              @click="openRecipeSelectDialog"
            >
              Browse Recipes
            </v-btn>
          </v-card-text>
        </v-card>
      </div>

      <div v-else-if="!loading && recipeData">
        <v-alert type="info" variant="tonal" class="mb-4">
          <div class="d-flex justify-space-between align-center mb-2">
            <div class="font-weight-bold">Current Recipe Configuration</div>
            <v-btn
              v-if="!props.book.recipe_id"
              size="small"
              variant="text"
              color="error"
              @click="clearRecipeSelection"
            >
              <v-icon size="small" class="mr-1">mdi-close-circle</v-icon>
              Clear Selection
            </v-btn>
          </div>
          <div class="d-flex flex-column ga-2">
            <div>
              <span class="text-medium-emphasis">Recipe Name:</span>
              <strong class="ml-2">{{ recipeData.name }}</strong>
              <v-btn
                :href="recipeData.link"
                target="_blank"
                size="x-small"
                variant="text"
                color="primary"
                class="ml-2"
              >
                <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
                View in Zimfarm
              </v-btn>
            </div>
            <div>
              <span class="text-medium-emphasis">Current Title:</span>
              <strong class="ml-2">{{ recipeData.title_name || 'Not configured' }}</strong>
            </div>
            <div>
              <span class="text-medium-emphasis">Expected Flavours:</span>
              <span v-if="recipeData.flavours.length === 0" class="ml-2 text-grey">
                None configured
              </span>
              <span v-else class="ml-2">
                <v-chip
                  v-for="tf in recipeData.flavours"
                  :key="tf.flavour"
                  size="small"
                  color="primary"
                  variant="outlined"
                >
                  {{ tf.flavour }}
                </v-chip>
              </span>
            </div>
          </div>
        </v-alert>

        <!-- Action Buttons -->
        <v-card variant="outlined" class="mb-4">
          <v-card-title class="text-h6">Choose Action</v-card-title>
          <v-card-text>
            <v-radio-group v-model="actionMode" class="mb-2">
              <v-radio label="Create New Title" value="create-title" color="primary" />
              <v-radio label="Configure Existing Recipe" value="configure-recipe" color="primary" />
            </v-radio-group>
          </v-card-text>
        </v-card>

        <!-- Create Title Action -->
        <v-card v-if="actionMode === 'create-title'" variant="outlined" class="mb-4">
          <v-card-title>Create New Title</v-card-title>
          <v-card-text>
            <p class="text-body-2 mb-4">A new title will be created based on the book metadata</p>
            <v-btn color="primary" variant="elevated" @click="handleCreateTitle">
              <v-icon class="mr-2">mdi-plus-circle</v-icon>
              Create Title
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card v-if="actionMode === 'configure-recipe'" variant="outlined" class="mb-4">
          <v-card-title>Configure Recipe</v-card-title>
          <v-card-text>
            <!-- Select Title -->
            <div class="mb-4">
              <div class="d-flex align-center mb-2">
                <span class="text-subtitle-1 font-weight-bold">Select Title</span>
                <v-btn
                  size="small"
                  variant="text"
                  color="primary"
                  class="ml-2"
                  @click="openTitleSelectDialog"
                >
                  <v-icon size="small" class="mr-1">mdi-magnify</v-icon>
                  Browse Titles
                </v-btn>
              </div>
              <v-text-field
                v-model="selectedTitleName"
                label="Title Name"
                variant="outlined"
                density="compact"
                readonly
                placeholder="Select a title..."
              />
            </div>

            <div class="mb-4">
              <span class="text-subtitle-1 font-weight-bold">Expected Flavours</span>
              <v-combobox
                v-model="selectedFlavours"
                label="Flavours"
                variant="outlined"
                density="compact"
                multiple
                clearable
                chips
                closable-chips
                class="mt-2"
                hint="Press Enter to add a new flavour or select from available options"
                persistent-hint
                :items="availableFlavours"
              />
            </div>

            <!-- Conflict Warnings -->
            <v-alert
              v-if="titleConflict || flavourConflicts.length > 0"
              type="warning"
              variant="tonal"
              class="mb-4"
            >
              <div class="font-weight-bold mb-2">Configuration Conflicts</div>
              <div v-if="titleConflict" class="mb-2">
                <div class="text-body-2">
                  <v-icon size="small" class="mr-1">mdi-alert</v-icon>
                  The selected title is already associated with recipe:
                  <strong>{{ titleConflict.recipe_name }}</strong>
                  <v-btn
                    :href="titleConflict.recipe_link"
                    target="_blank"
                    size="x-small"
                    variant="text"
                    color="primary"
                    class="ml-1"
                  >
                    <v-icon size="x-small" class="mr-1">mdi-open-in-new</v-icon>
                    View
                  </v-btn>
                </div>
              </div>
              <div v-if="flavourConflicts.length > 0">
                <div class="text-body-2 mb-1">
                  <v-icon size="small" class="mr-1">mdi-alert</v-icon>
                  The following flavours are already associated with other recipes:
                </div>
                <ul class="ml-6">
                  <li v-for="conflict in flavourConflicts" :key="conflict.flavour">
                    <strong>{{ conflict.flavour }}</strong> is linked to
                    <strong>{{ conflict.recipe_name }}</strong>
                    <v-btn
                      :href="conflict.recipe_link"
                      target="_blank"
                      size="x-small"
                      variant="text"
                      color="primary"
                      class="ml-1"
                    >
                      <v-icon size="x-small" class="mr-1">mdi-open-in-new</v-icon>
                      View
                    </v-btn>
                  </li>
                </ul>
              </div>
            </v-alert>

            <!-- Save Button -->
            <v-btn
              color="primary"
              variant="elevated"
              :disabled="!canSave || saving"
              :loading="saving"
              @click="handleSaveConfiguration"
            >
              <v-icon class="mr-2">mdi-content-save</v-icon>
              Save Configuration
            </v-btn>
          </v-card-text>
        </v-card>
      </div>
    </v-card-text>

    <TitleSelectDialog
      v-if="book && book.name"
      v-model="titleSelectDialogOpen"
      :book-name="book.name"
      @title-selected="handleTitleSelected"
      dialog-title="Choose a Title"
      confirm-button-text="Select Title"
    />

    <RecipeSelectDialog v-model="recipeSelectDialogOpen" @recipe-selected="handleRecipeSelected" />
  </v-card>
</template>

<script setup lang="ts">
import TitleSelectDialog from '@/components/TitleSelectDialog.vue'
import RecipeSelectDialog from '@/components/RecipeSelectDialog.vue'
import { useZimfarmRecipeStore } from '@/stores/zimfarmRecipe'
import { useTitleStore } from '@/stores/title'
import { useNotificationStore } from '@/stores/notification'
import type { Book } from '@/types/book'
import type { ZimfarmRecipe } from '@/types/zimfarmRecipe'
import type { TitleFlavour } from '@/types/title'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

interface Props {
  book: Book
}

const props = defineProps<Props>()

const emit = defineEmits<{
  titleCreated: []
  recipeConfigured: []
}>()

const zimfarmRecipeStore = useZimfarmRecipeStore()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const loading = ref(false)
const recipeData = ref<ZimfarmRecipe | null>(null)
const actionMode = ref<'create-title' | 'configure-recipe'>('configure-recipe')
const selectedTitleName = ref('')
const selectedFlavours = ref<string[]>([])
const titleSelectDialogOpen = ref(false)
const recipeSelectDialogOpen = ref(false)
const saving = ref(false)
const selectedRecipeId = ref('')
const selectedRecipeName = ref('')

// Conflict tracking
const titleConflict = ref<{
  recipe_name: string
  recipe_link: string
} | null>(null)

const flavourConflicts = ref<
  Array<{
    flavour: string
    recipe_name: string
    recipe_link: string
  }>
>([])

const canSave = computed(() => {
  return selectedTitleName.value !== '' && selectedFlavours.value.length > 0
})

// Get list of conflicting recipe names for API call
const conflictingRecipeNames = computed(() => {
  const recipes = new Set<string>()
  if (titleConflict.value) {
    recipes.add(titleConflict.value.recipe_name)
  }
  flavourConflicts.value.forEach((conflict) => {
    recipes.add(conflict.recipe_name)
  })
  return Array.from(recipes)
})

async function loadRecipeData() {
  if (!props.book.recipe_id) {
    return
  }
  await loadRecipeDataById(props.book.recipe_id)
}

async function loadRecipeDataById(recipeId: string) {
  loading.value = true

  try {
    const recipe = await zimfarmRecipeStore.fetchZimfarmRecipe(recipeId, true)
    if (recipe) {
      recipeData.value = recipe
      // Pre-populate fields if recipe already has configuration
      if (recipe.title_name) {
        selectedTitleName.value = recipe.title_name
      }
      if (recipe.flavours && recipe.flavours.length > 0) {
        selectedFlavours.value = recipe.flavours.map((f) => f.flavour)
      }
    } else {
      notificationStore.showError('Failed to load recipe data')
    }
  } catch (error) {
    console.error('Error loading recipe:', error)
  } finally {
    loading.value = false
  }
}

const availableFlavours = computed(() => {
  if (!recipeData.value || !recipeData.value.flavours) {
    return []
  }

  return recipeData.value.flavours.map((tf: TitleFlavour) => tf.flavour)
})

async function handleCreateTitle() {
  emit('titleCreated')
  // After title creation, the parent component should trigger a refresh
  // which will load the newly created title details and switch to configure mode
}

function openTitleSelectDialog() {
  titleSelectDialogOpen.value = true
}

function openRecipeSelectDialog() {
  recipeSelectDialogOpen.value = true
}

function handleRecipeSelected(recipeId: string, recipeName: string) {
  selectedRecipeId.value = recipeId
  selectedRecipeName.value = recipeName
  loadRecipeDataById(recipeId)
}

function clearRecipeSelection() {
  selectedRecipeId.value = ''
  selectedRecipeName.value = ''
  recipeData.value = null
  selectedTitleName.value = ''
  selectedFlavours.value = []
  titleConflict.value = null
  flavourConflicts.value = []
  actionMode.value = 'configure-recipe'
}

async function handleTitleSelected(titleName: string) {
  selectedTitleName.value = titleName
  await checkConflicts()
}

async function checkConflicts() {
  titleConflict.value = null
  flavourConflicts.value = []

  if (!selectedTitleName.value) {
    return
  }

  try {
    // Fetch the title to check its current recipe associations
    const title = await titleStore.fetchTitleById(selectedTitleName.value)
    if (title) {
      // Check if title is already associated with a different recipe
      if (title.flavours && title.flavours.length > 0) {
        const existingRecipe = title.flavours[0].recipe_id
        if (existingRecipe && existingRecipe !== props.book.recipe_id) {
          // Fetch recipe details to get name and link
          const recipe = await zimfarmRecipeStore.fetchZimfarmRecipe(existingRecipe)
          if (recipe) {
            titleConflict.value = {
              recipe_name: recipe.name,
              recipe_link: recipe.link,
            }
          }
        }
      }

      // Check for flavour conflicts
      if (title.flavours && selectedFlavours.value.length > 0) {
        for (const selectedFlavour of selectedFlavours.value) {
          const titleFlavour = title.flavours.find(
            (f: TitleFlavour) => f.flavour === selectedFlavour,
          )
          if (
            titleFlavour &&
            titleFlavour.recipe_id &&
            titleFlavour.recipe_id !== props.book.recipe_id
          ) {
            // Fetch recipe details
            const recipe = await zimfarmRecipeStore.fetchZimfarmRecipe(titleFlavour.recipe_id)
            if (recipe) {
              flavourConflicts.value.push({
                flavour: selectedFlavour,
                recipe_name: recipe.name,
                recipe_link: recipe.link,
              })
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('Error checking conflicts:', error)
  }
}

async function handleSaveConfiguration() {
  if (!canSave.value || !recipeData.value) {
    return
  }

  saving.value = true

  try {
    const updateData = {
      title_name: selectedTitleName.value,
      flavours: selectedFlavours.value,
      current_recipes: conflictingRecipeNames.value,
    }

    const success = await zimfarmRecipeStore.updateZimfarmRecipe(recipeData.value.name, updateData)

    if (success) {
      notificationStore.showSuccess('Recipe configuration updated successfully')
      emit('recipeConfigured')
      await loadRecipeData()
    } else {
      notificationStore.showErrors(zimfarmRecipeStore.errors)
    }
  } catch (error) {
    console.error('Error saving configuration:', error)
    notificationStore.showError('An error occurred while saving the configuration')
  } finally {
    saving.value = false
  }
}

watch(
  [selectedTitleName, selectedFlavours],
  () => {
    checkConflicts()
  },
  { deep: true },
)

async function handlePostTitleCreation(titleName: string) {
  selectedTitleName.value = titleName
  actionMode.value = 'configure-recipe'
  // If the title has flavours from the book, pre-populate them
  try {
    const title = await titleStore.fetchTitleById(titleName)
    if (title && title.flavours && title.flavours.length > 0) {
      selectedFlavours.value = title.flavours.map((f: TitleFlavour) => f.flavour)
    }
  } catch (error) {
    console.error('Error loading title details:', error)
  }
  await checkConflicts()
}

defineExpose({
  handlePostTitleCreation,
})

onMounted(() => {
  loadRecipeData()
})

onUnmounted(() => {
  // Clean up temporary recipe selection when component unmounts
  if (!props.book.recipe_id) {
    selectedRecipeId.value = ''
    selectedRecipeName.value = ''
    recipeData.value = null
  }
})
</script>
