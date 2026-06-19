<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-data-table-server
        :headers="headers"
        :items="recipes"
        :loading="loading"
        :items-per-page="paginator.limit"
        :page="paginator.page"
        :items-per-page-options="limits"
        class="elevation-1 cursor-pointer-table"
        item-value="id"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
        :items-length="paginator.count"
        :model-value="selectedRecipes"
        :loading-text="loadingText"
        :row-props="getRowProps"
        :show-select="showSelection"
        hover
        @update:model-value="handleSelectionChange"
        @update:options="onUpdateOptions"
        @click:row="onRowClick"
        :hide-default-footer="props.paginator.count === 0"
        :hide-default-header="props.paginator.count === 0"
      >
        <template #[`item.name`]="{ item }">
          <span class="d-flex align-center ga-2">
            <v-icon
              v-if="!showSelection"
              size="small"
              :color="selectedRecipes.includes(item.id) ? 'primary' : undefined"
              :style="{ opacity: selectedRecipes.includes(item.id) ? 1 : 0 }"
              aria-hidden="true"
            >
              mdi-check-circle
            </v-icon>
            {{ item.name }}
          </span>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import type { Paginator } from '@/types/base'
import type { ZimfarmRecipeLight } from '@/types/zimfarmRecipe'
import { useDisplay } from 'vuetify'
import { useRouter, useRoute } from 'vue-router'

interface Props {
  recipes: ZimfarmRecipeLight[]
  paginator: Paginator
  loading?: boolean
  loadingText?: string
  errors?: string[]
  selectedRecipes?: string[]
  showSelection?: boolean
  disableNavigation?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  loadingText: 'Loading recipes...',
  errors: () => [],
  selectedRecipes: () => [],
  showSelection: false,
  disableNavigation: false,
})

const router = useRouter()
const route = useRoute()
const limits = [10, 20, 50, 100]

const { smAndDown } = useDisplay()

const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
  selectionChanged: [selectedRecipes: string[]]
  rowClicked: [item: ZimfarmRecipeLight]
}>()

const headers = [{ title: 'Name', value: 'name', sortable: false }]

function getRowProps({ item }: { item: ZimfarmRecipeLight }) {
  return {
    class: props.selectedRecipes?.includes(item.id) ? 'selected-row' : '',
  }
}

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

function onRowClick(event: Event, { item }: { item: ZimfarmRecipeLight }) {
  // Don't navigate if clicking on checkbox column
  const target = event.target as HTMLElement
  if (target.closest('.v-selection-control') || target.closest('td.v-data-table__td--select')) {
    return
  }

  emit('rowClicked', item)

  if (!props.disableNavigation) {
    router.push({ name: 'recipe-detail', params: { id: item.name } })
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
