<template>
  <v-card flat>
    <v-card-text class="pa-4">
      <v-alert type="info" variant="tonal" class="mb-4">
        <div class="font-weight-bold mb-2">Book Information</div>
        <div class="d-flex flex-column ga-1">
          <div>
            <span class="text-medium-emphasis">Name:</span>
            <strong class="ml-2">{{ book.name }}</strong>
          </div>
          <div>
            <span class="text-medium-emphasis">Flavour:</span>
            <strong class="ml-2">{{ book.flavour || 'N/A' }}</strong>
          </div>
        </div>
      </v-alert>

      <div v-if="book.issues && book.issues.length > 0">
        <v-expansion-panels v-model="openPanels" multiple>
          <v-expansion-panel v-if="recipeIssues.length > 0" value="recipe" class="mb-2">
            <v-expansion-panel-title>
              <div class="d-flex align-center">
                <v-icon color="warning" class="mr-2">mdi-chef-hat</v-icon>
                <span class="font-weight-bold">Recipe Issues</span>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <RecipeIssueSection
                ref="recipeIssueSectionRef"
                :book="book"
                @title-created="handleTitleCreated"
                @recipe-configured="handleRecipeConfigured"
              />
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>

      <v-alert v-else type="success" variant="tonal">
        <div class="d-flex align-center">
          <v-icon class="mr-2">mdi-check-circle</v-icon>
          <span>No issues found for this book.</span>
        </div>
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import RecipeIssueSection from '@/components/RecipeIssueSection.vue'
import type { Book } from '@/types/book'
import { computed, ref } from 'vue'

interface Props {
  book: Book
}

const props = defineProps<Props>()

const emit = defineEmits<{
  titleCreated: []
  recipeConfigured: []
}>()

const recipeIssueSectionRef = ref<InstanceType<typeof RecipeIssueSection> | null>(null)

// Track which panels are open (open recipe panel by default if it exists)
const openPanels = ref<string[]>([])

// Categorize issues
const recipeIssues = computed(() => {
  if (!props.book.issues) return []
  return props.book.issues.filter((issue) => issue == 'recipe issue')
})

if (recipeIssues.value.length > 0) {
  openPanels.value = ['recipe']
}

function handleTitleCreated() {
  emit('titleCreated')
}

function handleRecipeConfigured() {
  emit('recipeConfigured')
}
// Expose method to be called from parent
defineExpose({
  handlePostTitleCreation: async (titleName: string) => {
    await recipeIssueSectionRef.value?.handlePostTitleCreation(titleName)
  },
})
</script>
