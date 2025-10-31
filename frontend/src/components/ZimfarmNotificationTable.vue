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
          :disabled="selectedZimfarmNotifications.length === 0"
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
        :items="zimfarmNotifications"
        :loading="loading"
        :items-per-page="selectedLimit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        class="elevation-1"
        item-value="name"
        :show-select="showSelection"
        :model-value="selectedZimfarmNotifications"
        @update:model-value="handleSelectionChange"
        @update:options="onUpdateOptions"
        :hide-default-footer="props.paginator.count === 0"
        :hide-default-header="props.paginator.count === 0"
      >
        <template #loading>
          <div class="d-flex flex-column align-center justify-center pa-8">
            <v-progress-circular indeterminate size="64" />
            <div class="mt-4 text-body-1">
              {{ loadingText || 'Fetching zimfarm notifications...' }}
            </div>
          </div>
        </template>

        <template #[`item.id`]="{ item }">
          <!-- <router-link :to="{ name: 'schedule-detail', params: { scheduleName: item.id } }"> -->
          <span class="d-flex align-center">
            {{ item.id }}
          </span>
          <!-- </router-link> -->
        </template>

        <template #[`item.received_at`]="{ item }">
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <span v-bind="props">
                {{ fromNow(item.received_at) }}
              </span>
            </template>
            <span>{{ formatDt(item.received_at) }}</span>
          </v-tooltip>
        </template>

        <template #[`item.status`]="{ item }">
          <span v-if="!item.processed" class="d-flex align-center">
            <v-icon size="small" color="success" icon="mdi-clock-check-outline"></v-icon>
            <span class="text-caption ml-1">Pending</span>
          </span>
          <span v-else-if="item.errored" class="d-flex align-center">
            <v-icon size="small" color="error" icon="mdi-alert-circle-outline"></v-icon>
            <span class="text-caption ml-1">Bad Error</span>
          </span>
          <span v-else class="d-flex align-center">
            <v-icon size="small" color="warning" icon="mdi-alert-circle-outline"></v-icon>
            <span class="text-caption ml-1">Bad Notification</span>
          </span>
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="x-large" class="mb-2">mdi-format-list-bulleted</v-icon>
            <div class="text-h6 text-grey-darken-1 mb-2">No Zimfarm notifications found</div>
          </div>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import type { Paginator } from '@/types/base'
import type { ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import { computed, ref, watch } from 'vue'
import { formatDt, fromNow } from '@/utils/format'

// Props
interface Props {
  headers: { title: string; value: string }[]
  zimfarmNotifications: ZimfarmNotificationLight[]
  paginator: Paginator
  loading: boolean
  errors: string[]
  loadingText: string
  filters?: {
    id: string
  }
  selectedZimfarmNotifications?: string[]
  showSelection?: boolean
  showFilters?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({ id: '' }),
  selectedZimfarmNotifications: () => [],
  showSelection: true,
  showFilters: true,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
  clearFilters: []
  selectionChanged: [selectedTitles: string[]]
}>()

const limits = [10, 20, 50, 100]
const selectedLimit = ref(props.paginator.limit)

const selectedZimfarmNotifications = computed(() => props.selectedZimfarmNotifications)

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
