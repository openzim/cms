<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-card-title
        v-if="showSelection || $slots.actions"
        class="d-flex flex-column-reverse flex-sm-row align-sm-center justify-sm-start ga-2"
      >
        <slot name="actions" />
        <v-btn
          v-if="showSelection"
          size="small"
          variant="elevated"
          color="warning"
          :disabled="selectedTitles.length === 0"
          @click="promptClearSelections"
        >
          <v-icon size="small" class="mr-1">mdi-checkbox-multiple-blank-outline</v-icon>
          clear selections
        </v-btn>

        <ConfirmDialog
          v-model="showClearConfirm"
          title="Confirm Clear Selections"
          message="Are you sure you want to clear your current selection?"
          confirm-text="Proceed"
          cancel-text="Abort"
          confirm-color="warning"
          icon="mdi-help-circle"
          icon-color="warning"
          @confirm="clearSelections"
          @cancel="showClearConfirm = false"
        />
      </v-card-title>

      <v-data-table-server
        :headers="headers"
        :items="titles"
        :loading="loading"
        :items-per-page="props.paginator.limit"
        :items-length="props.paginator.count"
        :page="props.paginator.page"
        :items-per-page-options="limits"
        class="elevation-1 cursor-pointer-table"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
        item-value="name"
        :model-value="selectedTitles"
        :show-select="showSelection"
        :row-props="getRowProps"
        hover
        @update:model-value="handleSelectionChange"
        @update:options="onUpdateOptions"
        @click:row="onRowClick"
        :hide-default-footer="props.paginator.count === 0"
        :hide-default-header="props.paginator.count === 0"
      >
        <template #loading>
          <div class="d-flex flex-column align-center justify-center pa-8">
            <v-progress-circular indeterminate size="64" />
            <div class="mt-4 text-body-1">{{ loadingText || 'Fetching titles...' }}</div>
          </div>
        </template>

        <template #[`header.maturity`]="{ column }">
          <div>
            <span>{{ column.title }}</span>
            <v-tooltip location="top">
              <template #activator="{ props: tooltipProps }">
                <v-icon v-bind="tooltipProps" size="small" class="ml-1" color="grey-darken-1">
                  mdi-information-outline
                </v-icon>
              </template>
              <div>
                <div>
                  <strong>Unstable:</strong> ZIM files go through staging first before moving to
                  production
                </div>
                <div><strong>Stable:</strong> ZIM files go directly to production</div>
              </div>
            </v-tooltip>
          </div>
        </template>

        <template #[`item.name`]="{ item }">
          <div class="d-flex align-center ga-2">
            <v-icon
              v-if="!showSelection"
              size="small"
              :color="selectedTitles.includes(item.name) ? 'primary' : undefined"
              :style="{ opacity: selectedTitles.includes(item.name) ? 1 : 0 }"
              aria-hidden="true"
            >
              mdi-check-circle
            </v-icon>
            {{ item.name }}
          </div>
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="x-large" class="mb-2">mdi-format-list-bulleted</v-icon>
            <div class="text-h6 text-grey-darken-1 mb-2">No titles found</div>
          </div>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import type { Paginator } from '@/types/base'
import type { TitleLight } from '@/types/title'
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

import ConfirmDialog from '@/components/ConfirmDialog.vue'

// Props
interface Props {
  headers: { title: string; value: string }[]
  titles: TitleLight[]
  paginator: Paginator
  loading: boolean
  errors: string[]
  loadingText: string
  filters?: {
    name: string
    collection_name: string
  }
  selectedTitles?: string[]
  showSelection?: boolean
  disableNavigation?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({ name: '', collection_name: '' }),
  selectedTitles: () => [],
  showSelection: false,
  disableNavigation: false,
})

const { smAndDown } = useDisplay()

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
  selectionChanged: [selectedTitles: string[]]
  rowClicked: [item: TitleLight]
}>()

const router = useRouter()
const route = useRoute()
const limits = [10, 20, 50, 100]

const selectedTitles = computed(() => props.selectedTitles)
const showClearConfirm = ref(false)

function onUpdateOptions(options: { page: number; itemsPerPage: number }) {
  const query = { ...route.query }
  if (options.page > 1) {
    query.page = options.page.toString()
  } else {
    delete query.page
  }

  if (!props.disableNavigation) {
    router.push({ query })
  } else {
    // When navigation is disabled, emit loadData directly
    if (options.itemsPerPage === props.paginator.limit) {
      const skip = (options.page - 1) * options.itemsPerPage
      emit('loadData', options.itemsPerPage, skip)
    }
  }

  // Emit limit change when it actually changes as the query would be the
  // same and we need to reload the data.
  if (options.itemsPerPage != props.paginator.limit) {
    emit('limitChanged', options.itemsPerPage)
  }
}

function handleSelectionChange(selection: string[]) {
  emit('selectionChanged', selection)
}

function promptClearSelections() {
  showClearConfirm.value = true
}

function clearSelections() {
  emit('selectionChanged', [])
  showClearConfirm.value = false
}

function getRowProps({ item }: { item: TitleLight }) {
  return {
    class: props.selectedTitles?.includes(item.name) ? 'selected-row' : '',
  }
}

function onRowClick(event: Event, { item }: { item: TitleLight }) {
  // Don't navigate if clicking on checkbox column
  const target = event.target as HTMLElement
  if (target.closest('.v-selection-control') || target.closest('td.v-data-table__td--select')) {
    return
  }

  emit('rowClicked', item)

  if (!props.disableNavigation) {
    router.push({ name: 'title-detail', params: { id: item.name } })
  }
}
</script>

<style scoped>
:deep(.cursor-pointer-table tbody tr) {
  cursor: pointer;
}

:deep(.selected-row td) {
  background-color: rgba(var(--v-theme-primary), 0.1) !important;
}

:deep(.selected-row td:first-child) {
  box-shadow: inset 3px 0 0 rgb(var(--v-theme-primary));
}

:deep(.selected-row:hover td) {
  background-color: rgba(var(--v-theme-primary), 0.16) !important;
}
</style>
