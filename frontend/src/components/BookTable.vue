<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-data-table-server
        :headers="headers"
        :items="books"
        :loading="loading"
        :page="props.paginator.page"
        :items-per-page="props.paginator.limit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
        class="elevation-1"
        item-value="name"
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
            {{ item.id }}
          </router-link>
        </template>

        <template #[`item.location_kind`]="{ item }">
          <v-chip :color="locationKindColors[item.location_kind]" size="small" variant="flat">
            {{ item.location_kind }}
          </v-chip>
        </template>

        <template #[`item.status`]="{ item }">
          <BookStatus :book="item" />
        </template>

        <template #[`item.deletion_date`]="{ item }">
          {{ item.deletion_date ? formatDt(item.deletion_date) : '-' }}
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
import { formatDt } from '@/utils/format'
import type { BookLight, LocationKind } from '@/types/book'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

const router = useRouter()
const route = useRoute()

const { smAndDown } = useDisplay()

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
    location_kind: string
    flag: string
  }
  showFilters?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({ id: '', location_kind: '', flag: '' }),
  showSelection: true,
  showFilters: true,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
}>()

const limits = [10, 20, 50, 100]

const locationKindColors: Record<LocationKind, string> = {
  quarantine: 'warning',
  staging: 'secondary',
  prod: 'success',
  to_delete: 'info',
  deleted: 'red-lighten-1',
}

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
</script>
