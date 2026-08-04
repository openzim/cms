<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-data-table-server
        :headers="headers"
        :items="tasks"
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
            <div class="mt-4 text-body-1">{{ loadingText || 'Fetching tasks...' }}</div>
          </div>
        </template>

        <template #[`item.id`]="{ item }">
          <span class="text-caption text-mono">{{ item.id }}</span>
        </template>

        <template #[`item.status`]="{ item }">
          <v-chip size="small" variant="tonal">
            {{ item.status }}
          </v-chip>
        </template>

        <template #[`item.zimfarm_link`]="{ item }">
          <a
            v-if="item.zimfarm_link && item.status !== 'requested'"
            :href="item.zimfarm_link"
            target="_blank"
            rel="noopener noreferrer"
            class="text-decoration-none"
          >
            <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
            View task
          </a>
          <span v-else class="text-grey">—</span>
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
            <div class="text-body-1">No tasks found</div>
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
import type { RequestedTaskLight } from '@/types/requestedTask'
import { formatDt } from '@/utils/format'
import { useRoute, useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'

const props = defineProps<{
  headers: { title: string; key: string; sortable?: boolean }[]
  tasks: RequestedTaskLight[]
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
