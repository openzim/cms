<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-card-title
        v-if="showSelection || showFilters || $slots.actions"
        class="d-flex flex-column-reverse flex-sm-row align-sm-center justify-sm-end ga-2"
      >
        <slot name="actions" />
        <v-btn
          v-if="showSelection"
          size="small"
          variant="elevated"
          color="warning"
          :disabled="selectedBooks.length === 0"
          @click="clearSelections"
        >
          <v-icon size="small" class="mr-1">mdi-checkbox-multiple-blank-outline</v-icon>
          clear selections
        </v-btn>
        <v-btn
          v-if="showFilters"
          size="small"
          variant="outlined"
          :disabled="!hasActiveFilters"
          @click="handleClearFilters"
        >
          <v-icon size="small" class="mr-1">mdi-close-circle</v-icon>
          clear filters
        </v-btn>
      </v-card-title>

      <v-data-table-server
        :headers="headers"
        :items="books"
        :loading="loading"
        :items-per-page="selectedLimit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        class="elevation-1"
        item-value="name"
        :show-select="showSelection"
        :model-value="selectedBooks"
        @update:model-value="handleSelectionChange"
        @update:options="onUpdateOptions"
        :hide-default-footer="props.paginator.count === 0"
        :hide-default-header="props.paginator.count === 0"
      >
        <template #loading>
          <div class="d-flex flex-column align-center justify-center pa-8">
            <v-progress-circular indeterminate size="64" />
            <div class="mt-4 text-body-1">
              {{ loadingText || 'Fetching books...' }}
            </div>
          </div>
        </template>

        <template #[`item.id`]="{ item }">
          <router-link :to="{ name: 'book-detail', params: { id: item.id } }">
            <span class="d-flex align-center">
              {{ item.id }}
            </span>
          </router-link>
        </template>

        <template #[`item.status`]="{ item }">
          <BookStatus :book="item" />
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="x-large" class="mb-2">mdi-book-open-page-variant</v-icon>
            <div class="text-h6 text-grey-darken-1 mb-2">No books found</div>
          </div>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import BookStatus from '@/components/BookStatus.vue'
import type { Paginator } from '@/types/base'
import type { BookLight } from '@/types/book'
import { computed, ref, watch } from 'vue'

// Props
interface Props {
  headers: { title: string; value: string }[]
  books: BookLight[]
  paginator: Paginator
  loading: boolean
  errors: string[]
  loadingText: string
  filters?: {
    id: string
  }
  selectedBooks?: string[]
  showSelection?: boolean
  showFilters?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({ id: '' }),
  selectedBooks: () => [],
  showSelection: true,
  showFilters: true,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
  clearFilters: []
  selectionChanged: [selectedBooks: string[]]
}>()

const limits = [10, 20, 50, 100]
const selectedLimit = ref(props.paginator.limit)

const selectedBooks = computed(() => props.selectedBooks)

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return props.filters.id.length > 0
})

function onUpdateOptions(options: { page: number; itemsPerPage: number }) {
  // page is 1-indexed, we need to calculate the skip for the request
  const page = options.page > 1 ? options.page - 1 : 0
  emit('loadData', options.itemsPerPage, page * options.itemsPerPage)
}

watch(
  () => props.paginator,
  (newPaginator) => {
    selectedLimit.value = newPaginator.limit
  },
  { immediate: true },
)

function handleSelectionChange(selection: string[]) {
  emit('selectionChanged', selection)
}

function clearSelections() {
  emit('selectionChanged', [])
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
