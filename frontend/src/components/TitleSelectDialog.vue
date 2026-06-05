<template>
  <v-dialog v-model="dialogModel" max-width="800" persistent>
    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span class="text-h5">Select Title</span>
        <v-btn icon="mdi-close" variant="text" @click="closeDialog" />
      </v-card-title>

      <v-card-text class="pa-4">
        <TitlesFilter
          v-if="!loading"
          :filters="filters"
          :collections="collectionNames"
          @filters-changed="handleFiltersChange"
          @clear-filters="clearFilters"
        />

        <div v-if="titles.length > 0" class="d-flex justify-end gap-2">
          <v-btn variant="text" @click="closeDialog"> Cancel </v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :disabled="!selectedTitleData"
            @click="confirmSelection"
          >
            Update Title Name
          </v-btn>
        </div>
        <v-alert v-if="selectedTitleData" type="info" variant="tonal" class="mt-4">
          <div class="font-weight-bold mb-1">Selected Title</div>
          <div>{{ selectedTitleData.name }}</div>
          <div class="mt-2 text-caption">
            This will update the title name to: <strong>{{ bookName }}</strong>
          </div>
        </v-alert>

        <TitlesTable
          v-if="!loading"
          :headers="headers"
          :titles="titles"
          :paginator="paginator"
          :loading="loadingStore.isLoading"
          :loading-text="loadingStore.loadingText"
          :errors="errors"
          :filters="filters"
          :selected-titles="selectedTitle"
          :show-selection="false"
          disable-navigation
          @limit-changed="handleLimitChange"
          @load-data="loadData"
          @selection-changed="handleSelectionChange"
          @row-clicked="handleRowClick"
        />

        <v-alert v-if="selectedTitleData" type="info" variant="tonal" class="mt-4">
          <div class="font-weight-bold mb-1">Selected Title</div>
          <div>{{ selectedTitleData.name }}</div>
          <div class="mt-2 text-caption">
            This will update the title name to: <strong>{{ bookName }}</strong>
          </div>
        </v-alert>
      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4" v-if="titles.length > 0">
        <v-spacer />
        <v-btn variant="text" @click="closeDialog"> Cancel </v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :disabled="!selectedTitleData"
          @click="confirmSelection"
        >
          Update Title Name
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import TitlesFilter from '@/components/TitlesFilters.vue'
import TitlesTable from '@/components/TitlesTable.vue'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useCollectionsStore } from '@/stores/collections'
import type { TitleLight } from '@/types/title'
import type { Paginator } from '@/types/base'
import { computed, onMounted, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  bookName: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  titleSelected: [titleName: string]
}>()

const headers = [
  { title: 'Name', value: 'name' },
  {
    title: 'Maturity',
    value: 'maturity',
  },
]

const titles = ref<TitleLight[]>([])
const loading = ref<boolean>(true)
const errors = ref<string[]>([])
const filters = ref({
  name: '',
  collection_name: '',
})
const selectedTitle = ref<string[]>([])

const titleStore = useTitleStore()
const collectionsStore = useCollectionsStore()
const loadingStore = useLoadingStore()
const notificationStore = useNotificationStore()

const collectionNames = computed(() => collectionsStore.collections.map((c) => c.name))

const paginator = ref<Paginator>({
  page: 1,
  page_size: titleStore.defaultLimit,
  skip: 0,
  limit: titleStore.defaultLimit,
  count: 0,
})

const dialogModel = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const selectedTitleData = computed(() => {
  if (selectedTitle.value.length === 0) return null
  return titles.value.find((t) => t.name === selectedTitle.value[0])
})

async function loadData(limit: number, skip: number, hideLoading: boolean = false) {
  if (!hideLoading) {
    loadingStore.startLoading('Fetching titles...')
  }

  await titleStore.fetchTitles(
    limit,
    skip,
    filters.value.name || undefined,
    filters.value.collection_name || undefined,
    false,
  )

  titles.value = titleStore.titles
  paginator.value = titleStore.paginator
  errors.value = titleStore.errors

  for (const error of errors.value) {
    notificationStore.showError(error)
  }

  if (loadingStore.isLoading) {
    loadingStore.stopLoading()
  }
}

async function handleFiltersChange(newFilters: typeof filters.value) {
  filters.value = newFilters
  selectedTitle.value = []
  await loadData(paginator.value.limit, 0)
}

async function handleLimitChange(newLimit: number) {
  await loadData(newLimit, 0)
}

async function clearFilters() {
  filters.value = {
    name: '',
    collection_name: '',
  }
  selectedTitle.value = []
  await loadData(paginator.value.limit, 0)
}

function handleSelectionChange(selection: string[]) {
  selectedTitle.value = selection
}

function handleRowClick(item: TitleLight) {
  if (selectedTitle.value.includes(item.name)) {
    selectedTitle.value = []
  } else {
    selectedTitle.value = [item.name]
  }
}

function closeDialog() {
  dialogModel.value = false
  selectedTitle.value = []
}

function confirmSelection() {
  if (selectedTitleData.value) {
    emit('titleSelected', selectedTitleData.value.name)
    closeDialog()
  }
}

onMounted(async () => {
  await collectionsStore.fetchCollections(20)
  loading.value = false
})

// Watch for dialog open to load and reset state
watch(dialogModel, async (newValue) => {
  if (newValue) {
    selectedTitle.value = []
    filters.value = {
      name: '',
      collection_name: '',
    }
    await loadData(paginator.value.limit, 0)
  }
})
</script>
