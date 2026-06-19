<template>
  <v-container>
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-1">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded && recipe">
      <v-tabs
        v-model="currentTab"
        class="mb-4"
        color="primary"
        slider-color="primary"
        show-arrows
        :grow="!smAndDown"
      >
        <v-tab
          base-color="primary"
          value="details"
          :to="{
            name: 'recipe-detail',
            params: { id: recipe.name },
          }"
        >
          <v-icon class="mr-2">mdi-information</v-icon>
          Info
        </v-tab>

        <v-tab
          base-color="primary"
          v-if="canEditRecipe"
          value="history"
          :to="{
            name: 'recipe-detail-tab',
            params: { id: recipe.name, selectedTab: 'history' },
          }"
        >
          <v-icon class="mr-2">mdi-history</v-icon>
          History
        </v-tab>
      </v-tabs>

      <v-window v-model="currentTab">
        <v-window-item value="details">
          <div>
            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Id</div>
              </v-col>
              <v-col cols="12" md="9">
                <code>{{ recipe.id }}</code
                >,
                <a target="_blank" :href="recipe.link">
                  View in Zimfarm <v-icon size="small">mdi-open-in-new</v-icon>
                </a>
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Name</div>
              </v-col>
              <v-col cols="12" md="9">
                {{ recipe.name }}
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Flavours</div>
              </v-col>
              <v-col cols="12" md="9">
                <div v-if="recipe.flavours.length > 0">
                  <v-chip
                    v-for="tf in recipe.flavours"
                    :key="tf.flavour || 'empty'"
                    size="small"
                    variant="outlined"
                    color="primary"
                    class="mr-2 mb-1"
                  >
                    {{ tf.flavour == '' ? 'Empty' : tf.flavour }}
                  </v-chip>
                </div>
                <span v-else class="text-grey">No flavours set</span>
              </v-col>
            </v-row>
            <v-divider class="my-2"></v-divider>

            <v-row v-if="recipe.title_name" no-gutters class="py-2">
              <v-col cols="12" md="3">
                <div class="text-subtitle-2">Title</div>
              </v-col>
              <v-col cols="12" md="9">
                <router-link
                  :to="{ name: 'title-detail', params: { id: recipe.title_name } }"
                  class="text-decoration-none text-primary font-weight-medium"
                >
                  View Title
                </router-link>
              </v-col>
            </v-row>
          </div>
        </v-window-item>

        <v-window-item value="history">
          <RecipeHistory
            v-if="canEditRecipe"
            :history="zimfarmRecipeHistoryStore.history"
            :has-more="canLoadMoreHistory"
            :loading="loadingHistory"
            :paginator="zimfarmRecipeHistoryStore.paginator"
            :recipe-name="recipe.name"
            @load="loadHistory"
          />
        </v-window-item>
      </v-window>
    </div>
  </v-container>
</template>

<script setup lang="ts">
import RecipeHistory from '@/components/RecipeHistory.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useZimfarmRecipeStore } from '@/stores/zimfarmRecipe'
import { useZimfarmRecipeHistoryStore } from '@/stores/zimfarmRecipeHistory'
import { useAuthStore } from '@/stores/auth'
import type { ZimfarmRecipe } from '@/types/zimfarmRecipe'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'

const { smAndDown } = useDisplay()

const router = useRouter()

const loadingStore = useLoadingStore()
const zimfarmRecipeStore = useZimfarmRecipeStore()
const zimfarmRecipeHistoryStore = useZimfarmRecipeHistoryStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()

const error = ref<string | null>(null)
const recipe = ref<ZimfarmRecipe | null>(null)
const dataLoaded = ref(false)
const loadingHistory = ref<boolean>(false)

const canEditRecipe = computed(() => authStore.hasPermission('recipe', 'update'))

const canLoadMoreHistory = computed(() => {
  const { skip, limit, count } = zimfarmRecipeHistoryStore.paginator
  return skip + limit < count
})

interface Props {
  id: string
  selectedTab?: string
}

const props = withDefaults(defineProps<Props>(), {
  selectedTab: 'details',
})

const currentTab = ref(props.selectedTab)

const loadHistory = async ({ limit, skip }: { limit: number; skip: number }) => {
  if (skip > 0 && !canLoadMoreHistory.value) return

  loadingHistory.value = true
  try {
    const response = await zimfarmRecipeHistoryStore.fetchHistory(props.id, limit, skip)
    if (!response) {
      notificationStore.showError(`Failed to ${skip > 0 ? 'load more' : 'load'} history items`)
    }
  } catch (error) {
    console.error('Failed to load history items', error)
  } finally {
    loadingHistory.value = false
  }
}

const loadData = async (forceReload: boolean = false, fetchHistory: boolean = false) => {
  loadingStore.startLoading('Fetching collection...')

  const data = await zimfarmRecipeStore.fetchZimfarmRecipe(props.id, forceReload)

  if (fetchHistory) {
    zimfarmRecipeHistoryStore.clearHistory()
    await loadHistory({ limit: zimfarmRecipeHistoryStore.paginator.limit, skip: 0 })
  }

  if (data) {
    error.value = null
    recipe.value = data
    dataLoaded.value = true
  } else {
    error.value = 'Failed to load collection'
    for (const err of zimfarmRecipeStore.errors) {
      notificationStore.showError(err)
    }
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

onMounted(async () => {
  await loadData(true, props.selectedTab === 'history')

  // Redirect to details if trying to access restricted tabs without permission
  if (props.selectedTab !== 'details' && !canEditRecipe.value) {
    router.push({ name: 'recipe-detail', params: { id: props.id } })
    return
  }
})

onUnmounted(() => {
  // Clear recipe history to prevent accumulation of history items
  zimfarmRecipeHistoryStore.clearHistory()
})

// Watch for tab changes
watch(
  () => props.selectedTab,
  async (newTab) => {
    currentTab.value = newTab
    await loadData(newTab === 'edit', newTab === 'history')
  },
)

// Watch for recipe id changes (when navigating to a different collection)
watch(
  () => props.id,
  async () => {
    // Reset the current tab to details when switching recipe
    // Clear current data and reload the new recipe
    recipe.value = null
    currentTab.value = 'details'
  },
)
</script>
