<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <component
        :is="isServerSide ? 'v-data-table-server' : 'v-data-table'"
        :headers="computedHeaders"
        :items="books"
        :loading="loading"
        :page="isServerSide ? props.paginator.page : undefined"
        :items-per-page="isServerSide ? props.paginator.limit : -1"
        :items-length="isServerSide ? paginator.count : undefined"
        :items-per-page-options="isServerSide ? limits : undefined"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
        class="elevation-1 book-table"
        item-value="id"
        hover
        @update:options="isServerSide ? onUpdateOptions($event) : undefined"
        @click:row="handleRowClick"
        :hide-default-footer="isServerSide ? props.paginator.count === 0 : true"
        :hide-default-header="isServerSide ? props.paginator.count === 0 : false"
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
          <router-link :to="{ name: 'book-detail', params: { id: item.id } }" @click.stop>
            {{ item.id }}
          </router-link>
        </template>

        <template #[`item.name`]="{ item }">
          <span v-if="item.name">{{ item.name }}</span>
          <span v-else class="text-grey">-</span>
        </template>

        <template #[`item.flavour`]="{ item }">
          <span v-if="item.flavour">{{ item.flavour }}</span>
          <span v-else class="text-grey">-</span>
        </template>

        <template #[`item.date`]="{ item }">
          <span v-if="item.date">{{ item.date }}</span>
          <span v-else class="text-grey">-</span>
        </template>

        <template #[`item.status`]="{ item }">
          <BookStatus :book="item" />
        </template>

        <template #[`item.deletion_date`]="{ item }">
          {{ item.deletion_date ? formatDt(item.deletion_date, 'ff') : '-' }}
        </template>

        <template #[`item.urls`]="{ item }">
          <ZimUrlButtons
            v-if="showUrls && zimUrls"
            :urls="zimUrls[item.id]"
            :loading="loadingUrls"
            :compact="true"
            empty-text=""
          />
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="x-large" class="mb-2">mdi-book-open-page-variant</v-icon>
            <div class="text-h6 text-grey-darken-1 mb-2">No books found</div>
          </div>
        </template>
      </component>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import BookStatus from '@/components/BookStatus.vue'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'
import type { Paginator } from '@/types/base'
import { formatDt } from '@/utils/format'
import type { BookLight, ZimUrl } from '@/types/book'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()

const { smAndDown } = useDisplay()

// Props
interface Props {
  headers: { title: string; value: string }[]
  books: BookLight[]
  paginator?: Paginator
  loading?: boolean
  errors?: string[]
  loadingText?: string
  filters?: {
    id: string
    location_kind: string
    flag: string
  }
  showFilters?: boolean
  isServerSide?: boolean
  showUrls?: boolean
  zimUrls?: Record<string, ZimUrl[]>
  loadingUrls?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  paginator: () => ({ page: 1, limit: 20, skip: 0, count: 0, page_size: 20 }),
  loading: false,
  errors: () => [],
  loadingText: 'Fetching books...',
  filters: () => ({ id: '', location_kind: '', flag: '' }),
  showFilters: true,
  isServerSide: true,
  showUrls: false,
  loadingUrls: false,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
}>()

const computedHeaders = computed(() => {
  return props.headers
})

const limits = [10, 20, 50, 100]

function onUpdateOptions(options: { page: number; itemsPerPage: number }) {
  if (!props.isServerSide) return
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

function handleRowClick(event: Event, { item }: { item: BookLight }) {
  // Prevent navigation if the user clicked on a link or button
  const target = event.target as HTMLElement
  if (target.closest('a') || target.closest('button')) {
    return
  }
  router.push({ name: 'book-detail', params: { id: item.id } })
}
</script>

<style scoped>
.book-table :deep(tbody tr) {
  cursor: pointer;
}
</style>
