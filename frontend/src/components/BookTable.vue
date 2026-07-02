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
        :mobile="isMobile"
        :density="isMobile ? 'compact' : 'comfortable'"
        :class="['elevation-1', 'book-table', { 'force-cards': forceMobile }]"
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
          <div>
            <span v-if="item.flavour">{{ item.flavour }}</span>
            <span v-else class="text-grey"></span>
          </div>
        </template>

        <template #[`item.date`]="{ item }">
          <span v-if="item.date">{{ item.date }}</span>
          <span v-else class="text-grey">-</span>
        </template>

        <template #[`item.status`]="{ item }">
          <div class="card-status-wrap" :class="forceMobile ? 'd-flex justify-end' : undefined">
            <BookStatus
              :book="item"
              :force-row="forceMobile"
              :hide-issues="headersContainIssuesColumn"
            />
          </div>
        </template>

        <template #[`item.deletion_date`]="{ item }">
          {{ item.deletion_date ? formatDt(item.deletion_date, 'ff') : '-' }}
        </template>

        <template #[`item.issues`]="{ item }">
          <div
            v-if="item.issues && item.issues.length"
            class="card-issues-wrap d-flex flex-column align-end"
            :class="forceMobile ? 'my-0' : 'my-1'"
          >
            <v-chip
              v-for="(issue, idx) in item.issues"
              :key="idx"
              size="x-small"
              class="mb-1"
              color="red"
              variant="outlined"
            >
              <span class="text-truncate d-block">{{ issue }}</span>
            </v-chip>
            <div v-if="canViewBookIssues">
              <v-divider class="my-0" />
              <v-btn
                variant="outlined"
                size="x-small"
                color="primary"
                block
                rounded
                :to="{
                  name: 'book-detail-tab',
                  params: { id: item.id, selectedTab: 'issues' },
                }"
              >
                <v-icon size="small" class="mr-1">mdi-alert-circle</v-icon>
                View Issues
              </v-btn>
            </div>
          </div>
          <span v-else class="text-grey">-</span>
        </template>

        <template #[`item.scraper`]="{ item }">
          <span v-if="item.scraper">{{ item.scraper }}</span>
          <span v-else class="text-grey">-</span>
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
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

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
    name: string
    location_kind: string
    flag: string
  }
  isServerSide?: boolean
  showUrls?: boolean
  zimUrls?: Record<string, ZimUrl[]>
  loadingUrls?: boolean
  forceMobile?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  paginator: () => ({ page: 1, limit: 20, skip: 0, count: 0, page_size: 20 }),
  loading: false,
  errors: () => [],
  loadingText: 'Fetching books...',
  filters: () => ({ name: '', location_kind: '', flag: '' }),
  isServerSide: true,
  showUrls: false,
  loadingUrls: false,
  forceMobile: false,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
}>()

const isMobile = computed(() => props.forceMobile || smAndDown.value)

const computedHeaders = computed(() => {
  return props.headers
})

const canViewBookIssues = computed(() => {
  return authStore.hasPermission('book', 'update')
})

const headersContainIssuesColumn = computed(() =>
  computedHeaders.value.some((header) => header.value == 'issues'),
)

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

.book-table.force-cards :deep(tbody) {
  display: grid !important;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)) !important;
  gap: 8px !important;
}

.book-table.force-cards :deep(.v-data-table__tr--mobile) {
  font-size: 0.8125rem !important;
}

.book-table.force-cards :deep(.v-data-table__tr--mobile:hover) {
  background-color: rgba(var(--v-border-color), var(--v-hover-opacity)) !important;
}

.book-table.force-cards :deep(.v-data-table__tr--mobile > td::after) {
  content: none !important;
}

.book-table.force-cards :deep(.v-data-table__tr--mobile > td) {
  min-height: 24px;
  padding: 0 6px !important;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.book-table.force-cards :deep(.v-data-table__tr--mobile > td:has(.card-issues-wrap)) {
  height: auto;
  white-space: normal;
  overflow: visible;
}

.book-table.force-cards :deep(.v-data-table__tr--mobile > td:has(.card-status-wrap)) {
  height: auto;
  overflow: visible;
}
</style>
