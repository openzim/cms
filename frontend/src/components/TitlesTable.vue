<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-card-title
        v-if="showSelection || $slots.actions"
        class="d-flex flex-column-reverse flex-sm-row align-sm-center justify-sm-end ga-2"
      >
        <slot name="actions" />
      </v-card-title>

      <v-data-table-server
        :headers="headers"
        :items="titles"
        :loading="loading"
        :items-per-page="selectedLimit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        class="elevation-1 cursor-pointer-table"
        item-value="name"
        :model-value="selectedTitles"
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

        <template #[`item.name`]="{ item }">
          <span class="d-flex align-center">
            {{ item.name }}
          </span>
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
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({ name: '', collection_name: '' }),
  selectedTitles: () => [],
  showSelection: true,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
  selectionChanged: [selectedTitles: string[]]
}>()

const router = useRouter()
const route = useRoute()
const limits = [10, 20, 50, 100]
const selectedLimit = ref(props.paginator.limit)

const selectedTitles = computed(() => props.selectedTitles)

function onUpdateOptions(options: { page: number; itemsPerPage: number }) {
  const query = { ...route.query }
  if (options.page > 1) {
    query.page = options.page.toString()
  } else {
    delete query.page
  }

  router.push({ query })

  // Emit limit change when it actually changes as the query would be the
  // same and we need to reload the data.
  if (options.itemsPerPage != props.paginator.limit) {
    emit('limitChanged', options.itemsPerPage)
  }
}

function handleSelectionChange(selection: string[]) {
  emit('selectionChanged', selection)
}

function onRowClick(event: Event, { item }: { item: TitleLight }) {
  // Don't navigate if clicking on checkbox column
  const target = event.target as HTMLElement
  if (target.closest('.v-selection-control') || target.closest('td.v-data-table__td--select')) {
    return
  }
  router.push({ name: 'title-detail', params: { id: item.name } })
}
</script>

<style scoped>
:deep(.cursor-pointer-table tbody tr) {
  cursor: pointer;
}
</style>
