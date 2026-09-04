<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-data-table-server
        :headers="headers"
        :items="titleUploads"
        :loading="loading"
        :page="paginator.page"
        :items-per-page="paginator.limit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        class="elevation-1"
        item-key="id"
        hover
        @update:options="onUpdateOptions"
        :hide-default-footer="paginator.count === 0"
        :hide-default-header="paginator.count === 0"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
      >
        <template #loading>
          <div class="d-flex flex-column align-center justify-center pa-8">
            <v-progress-circular indeterminate size="64" />
            <div class="mt-4 text-body-1">{{ loadingText || 'Fetching title uploads...' }}</div>
          </div>
        </template>

        <template #[`item.id`]="{ item }">
          <TaskStatusDisplay
            :status="item.status"
            :updated-at="item.updated_at"
            :zimfarm-link="item.zimfarm_link"
          />
        </template>

        <template #[`item.book_id`]="{ item }">
          <router-link
            v-if="item.book_id"
            :to="{ name: 'book-detail', params: { id: item.book_id } }"
            @click.stop
          >
            View
          </router-link>
          <span v-else>—</span>
        </template>

        <template #[`item.requested_by`]="{ item }">
          <span>{{ item.requested_by || '—' }}</span>
        </template>

        <template #[`item.created_at`]="{ item }">
          <span>{{ formatDt(item.created_at) }}</span>
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="large" class="mb-2">mdi-clipboard-text-clock</v-icon>
            <div class="text-body-1">No uploads found</div>
          </div>
        </template>
      </v-data-table-server>
      <ErrorMessage v-for="error in errors" :key="error" :message="error" />
    </v-card>
  </div>
</template>

<script setup lang="ts">
import ErrorMessage from '@/components/ErrorMessage.vue'
import TaskStatusDisplay from '@/components/TaskStatusDisplay.vue'
import type { Paginator } from '@/types/base'
import type { TitleUploadLight } from '@/types/titleUpload'
import { formatDt } from '@/utils/format'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'

const props = defineProps<{
  headers: { title: string; key: string; sortable?: boolean }[]
  titleUploads: TitleUploadLight[]
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
</script>
