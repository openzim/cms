<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-data-table-server
        :headers="headers"
        :items="collections"
        :loading="loading"
        :page="paginator.page"
        :items-per-page="paginator.limit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        class="elevation-1 cursor-pointer-table"
        item-key="id"
        hover
        @update:options="onUpdateOptions"
        @click:row="onRowClick"
        :hide-default-footer="props.paginator.count === 0"
        :hide-default-header="props.paginator.count === 0"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
      >
        <template #loading>
          <div class="d-flex flex-column align-center justify-center pa-8">
            <v-progress-circular indeterminate size="64" />
            <div class="mt-4 text-body-1">{{ loadingText || 'Fetching collections...' }}</div>
          </div>
        </template>

        <template #[`item.name`]="{ item }">
          <span class="font-weight-medium">{{ item.name }}</span>
        </template>

        <template #[`item.paths`]="{ item }">
          <v-chip
            v-for="path in item.paths"
            :key="path"
            size="small"
            class="mr-1 mt-1 mb-1"
            variant="tonal"
            color="primary"
          >
            {{ path }}
          </v-chip>
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="large" class="mb-2">mdi-folder-multiple-outline</v-icon>
            <div class="text-body-1">No collections found</div>
          </div>
        </template>
      </v-data-table-server>
      <ErrorMessage v-for="error in errors" :key="error" :message="error" />
    </v-card>
  </div>
</template>

<script setup lang="ts">
import ErrorMessage from '@/components/ErrorMessage.vue'
import type { Paginator } from '@/types/base'
import type { CollectionLight } from '@/types/collections'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'

const props = defineProps<{
  headers: { title: string; key: string; sortable?: boolean }[]
  collections: CollectionLight[]
  paginator: Paginator
  loading: boolean
  errors: string[]
  loadingText: string
}>()

const emit = defineEmits<{
  limitChanged: [limit: number]
}>()

const limits = [10, 20, 50, 100]
const router = useRouter()
const route = useRoute()
const { smAndDown } = useDisplay()

function onUpdateOptions(options: { page: number; itemsPerPage: number }) {
  const query = { ...route.query }

  if (options.page > 1) {
    query.page = options.page.toString()
  } else {
    delete query.page
  }

  router.push({ query })

  if (options.itemsPerPage != props.paginator.limit) {
    emit('limitChanged', options.itemsPerPage)
  }
}

function onRowClick(event: Event, { item }: { item: CollectionLight }) {
  router.push({ name: 'collection-detail', params: { id: item.name } })
}
</script>

<style scoped>
:deep(.cursor-pointer-table tbody tr) {
  cursor: pointer;
}
</style>
