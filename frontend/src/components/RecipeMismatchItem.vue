<template>
  <div class="border pa-2 rounded mb-2">
    <div class="text-body-2 text-wrap">
      Book recipe
      <a
        v-if="issue.book_recipe_link"
        :href="issue.book_recipe_link"
        class="text-primary"
        rel="noopener noreferrer"
        >({{ bookRecipeLabel }})
        <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
      </a>
      <span v-else class="text-medium-emphasis">(not set)</span>
      <span class="text-medium-emphasis"> is different from title flavour recipe </span>
      <a
        v-if="issue.flavour_recipe_link"
        :href="issue.flavour_recipe_link"
        class="text-primary"
        rel="noopener noreferrer"
        >({{ flavourRecipeLabel }}) >
        <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
      </a>
      <span v-else class="text-medium-emphasis">(not set)</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { RecipeMismatch } from '@/types/book'
import { useZimfarmRecipeStore } from '@/stores/zimfarm/recipe'
import { useNotificationStore } from '@/stores/notification'

interface Props {
  issue: RecipeMismatch
}

const props = defineProps<Props>()

const recipeStore = useZimfarmRecipeStore()
const notificationStore = useNotificationStore()

const bookRecipeName = ref<string | null>(null)
const flavourRecipeName = ref<string | null>(null)

const bookRecipeLabel = computed(() => bookRecipeName.value ?? props.issue.book_recipe_id ?? '')

const flavourRecipeLabel = computed(
  () => flavourRecipeName.value ?? props.issue.flavour_recipe_id ?? '',
)

async function loadRecipeNames() {
  if (props.issue.book_recipe_id) {
    const recipe = await recipeStore.fetchRecipe(props.issue.book_recipe_id)
    bookRecipeName.value = recipe?.name ?? null
    if (!recipe) {
      notificationStore.showErrors(recipeStore.errors)
    }
  }
  if (props.issue.flavour_recipe_id) {
    const recipe = await recipeStore.fetchRecipe(props.issue.flavour_recipe_id)
    flavourRecipeName.value = recipe?.name ?? null
    if (!recipe) {
      notificationStore.showErrors(recipeStore.errors)
    }
  }
}

onMounted(loadRecipeNames)
</script>
