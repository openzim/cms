<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-data-table-server
        :headers="headers"
        :items="events"
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
              {{ loadingText || 'Fetching events...' }}
            </div>
          </div>
        </template>

        <template #[`item.id`]="{ item }">
          <span>
            {{ item.id }}
          </span>
        </template>

        <template #[`item.created_at`]="{ item }">
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <span v-bind="props">
                {{ fromNow(item.created_at) }}
              </span>
            </template>
            <span>{{ formatDt(item.created_at) }}</span>
          </v-tooltip>
        </template>

        <template #[`item.topic`]="{ item }">
          <span>{{ item.topic }}</span>
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="x-large" class="mb-2">mdi-format-list-bulleted</v-icon>
            <div class="text-h6 text-grey-darken-1 mb-2">No events found</div>
          </div>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import type { Paginator } from '@/types/base'
import type { EventLight } from '@/types/event'
import { formatDt, fromNow } from '@/utils/format'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

const router = useRouter()
const route = useRoute()

const { smAndDown } = useDisplay()

// Props
interface Props {
  headers: { title: string; value: string }[]
  events: EventLight[]
  paginator: Paginator
  loading: boolean
  errors: string[]
  loadingText: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
}>()

const limits = [10, 20, 50, 100]

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
