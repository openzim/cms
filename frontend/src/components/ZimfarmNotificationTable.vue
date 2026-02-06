<template>
  <div>
    <v-card v-if="!errors.length" :class="{ loading: loading }" flat>
      <v-card-title
        v-if="showSelection || $slots.actions"
        class="d-flex flex-column-reverse flex-sm-row align-sm-center justify-sm-end ga-2"
      >
        <slot name="actions" />
        <v-btn
          v-if="showSelection"
          size="small"
          variant="elevated"
          color="warning"
          :disabled="selectedZimfarmNotifications.length === 0"
          @click="clearSelections"
        >
          <v-icon size="small" class="mr-1">mdi-checkbox-multiple-blank-outline</v-icon>
          clear selections
        </v-btn>
      </v-card-title>

      <v-data-table-server
        :headers="headers"
        :items="zimfarmNotifications"
        :loading="loading"
        :page="props.paginator.page"
        :items-per-page="props.paginator.limit"
        :items-length="paginator.count"
        :items-per-page-options="limits"
        :mobile="smAndDown"
        :density="smAndDown ? 'compact' : 'comfortable'"
        class="elevation-1"
        item-value="name"
        :show-select="showSelection"
        :model-value="selectedZimfarmNotifications"
        @update:model-value="handleSelectionChange"
        @update:options="onUpdateOptions"
        :hide-default-footer="props.paginator.count === 0"
        :hide-default-header="props.paginator.count === 0"
      >
        <template #loading>
          <div class="d-flex flex-column align-center justify-center pa-8">
            <v-progress-circular indeterminate size="64" />
            <div class="mt-4 text-body-1">
              {{ loadingText || 'Fetching zimfarm notifications...' }}
            </div>
          </div>
        </template>

        <template #[`item.id`]="{ item }">
          <router-link :to="{ name: 'zimfarm-notification-detail', params: { id: item.id } }">
            <span class="d-flex align-center">
              {{ item.id }}
            </span>
          </router-link>
        </template>

        <template #[`item.received_at`]="{ item }">
          <v-tooltip location="bottom">
            <template #activator="{ props }">
              <span v-bind="props">
                {{ fromNow(item.received_at) }}
              </span>
            </template>
            <span>{{ formatDt(item.received_at) }}</span>
          </v-tooltip>
        </template>

        <template #[`item.status`]="{ item }">
          <ZimfarmNotificationStatus :zimfarm-notification="item" />
        </template>

        <template #no-data>
          <div class="text-center pa-4">
            <v-icon size="x-large" class="mb-2">mdi-format-list-bulleted</v-icon>
            <div class="text-h6 text-grey-darken-1 mb-2">No Zimfarm notifications found</div>
          </div>
        </template>
      </v-data-table-server>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import type { Paginator } from '@/types/base'
import type { ZimfarmNotificationLight } from '@/types/zimfarmNotification'
import { computed } from 'vue'
import { formatDt, fromNow } from '@/utils/format'
import ZimfarmNotificationStatus from '@/components/ZimfarmNotificationStatus.vue'
import { useRouter, useRoute } from 'vue-router'
import { useDisplay } from 'vuetify'

const router = useRouter()
const route = useRoute()

const { smAndDown } = useDisplay()

// Props
interface Props {
  headers: { title: string; value: string }[]
  zimfarmNotifications: ZimfarmNotificationLight[]
  paginator: Paginator
  loading: boolean
  errors: string[]
  loadingText: string
  filters?: {
    id: string
  }
  selectedZimfarmNotifications?: string[]
  showSelection?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  filters: () => ({ id: '' }),
  selectedZimfarmNotifications: () => [],
  showSelection: true,
})

// Define emits
const emit = defineEmits<{
  limitChanged: [limit: number]
  loadData: [limit: number, skip: number]
  selectionChanged: [selectedTitles: string[]]
}>()

const limits = [10, 20, 50, 100]

const selectedZimfarmNotifications = computed(() => props.selectedZimfarmNotifications)

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

function handleSelectionChange(selection: string[]) {
  emit('selectionChanged', selection)
}

function clearSelections() {
  emit('selectionChanged', [])
}
</script>
