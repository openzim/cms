<template>
  <v-card elevation="2" class="h-100 d-flex flex-column border">
    <v-card-title class="d-flex flex-column align-start pa-4">
      <div class="d-flex align-center flex-wrap w-100">
        <div class="text-subtitle-1 text-truncate flex-grow-1">
          {{ displayName }}
        </div>
      </div>

      <div class="d-flex align-center flex-wrap mt-2 ga-2">
        <v-chip v-if="book.flavour" size="small" variant="tonal" color="primary">
          {{ book.flavour }}
        </v-chip>

        <v-chip v-if="book.date" size="small" variant="outlined">
          <v-icon start size="small">mdi-calendar</v-icon>
          {{ book.date }}
        </v-chip>

        <v-chip v-if="offlinerName !== 'Unknown'" size="small" variant="outlined" color="teal">
          <v-icon start size="small">mdi-cogs</v-icon>
          {{ offlinerName }}
        </v-chip>

        <v-chip v-if="book.deletion_date" size="small" variant="outlined" color="red">
          <v-icon start size="small">mdi-delete-clock</v-icon>
          {{ formatDt(book.deletion_date, 'ff') }}
        </v-chip>
      </div>
    </v-card-title>

    <v-divider />

    <v-card-text class="pa-4">
      <div class="d-flex flex-column ga-2">
        <!-- Status -->
        <div class="d-flex justify-space-between align-center">
          <div class="text-body-2 font-weight-medium">Status</div>
          <BookStatusIndicator :book="book" />
        </div>

        <!-- Location -->
        <div v-if="showLocationChip" class="d-flex justify-space-between align-center">
          <div class="text-body-2 font-weight-medium">Location</div>
          <BookLocationChip :book="book" />
        </div>

        <!-- Issues -->
        <div
          v-if="book.issues && book.issues.length"
          class="d-flex justify-space-between align-start"
        >
          <div class="text-body-2 font-weight-medium">Issues</div>
          <div class="d-flex flex-column ga-1">
            <v-chip
              v-for="(issue, idx) in book.issues"
              :key="idx"
              size="x-small"
              color="red"
              variant="outlined"
              class="align-self-end"
            >
              <span class="text-truncate d-block">{{ issue }}</span>
            </v-chip>
          </div>
        </div>
      </div>
    </v-card-text>
    <v-divider />

    <v-card-actions class="pa-3 justify-end">
      <v-tooltip location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            :to="{ name: 'book-detail', params: { id: book.id } }"
            variant="text"
            size="small"
            icon
            @click.stop
          >
            <v-icon>mdi-information</v-icon>
          </v-btn>
        </template>
        <span>View Book</span>
      </v-tooltip>

      <template v-if="showUrls && zimUrls && zimUrls[book.id]">
        <ZimUrlButtons
          :urls="zimUrls[book.id]"
          :loading="loadingUrls"
          :compact="true"
          empty-text=""
        />
      </template>

      <v-tooltip v-if="canViewBookIssues && book.issues && book.issues.length" location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            :to="{
              name: 'book-detail-tab',
              params: { id: book.id, selectedTab: 'issues' },
            }"
            variant="text"
            size="small"
            icon
            @click.stop
          >
            <v-icon>mdi-bell-alert</v-icon>
          </v-btn>
        </template>
        <span>View Issues</span>
      </v-tooltip>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import BookStatusIndicator from '@/components/BookStatusIndicator.vue'
import BookLocationChip from '@/components/BookLocationChip.vue'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'
import type { BookLight, ZimUrl } from '@/types/book'
import { formatDt, matchOffliner } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import { useZimfarmOfflinerStore } from '@/stores/zimfarm/offliner'
import { computed, onMounted } from 'vue'

const authStore = useAuthStore()
const offlinerStore = useZimfarmOfflinerStore()

onMounted(async () => {
  await offlinerStore.fetchOffliners()
})

interface Props {
  book: BookLight
  showUrls?: boolean
  zimUrls?: Record<string, ZimUrl[]>
  loadingUrls?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showUrls: false,
  zimUrls: undefined,
  loadingUrls: false,
})

const displayName = computed(() => {
  return props.book.title_name || props.book.name || props.book.id
})

const isErrored = computed(() => props.book.has_error)
const isProcessing = computed(() => props.book.needs_processing && !props.book.has_error)
const isDeleted = computed(() => props.book.location_kind === 'deleted')
const isToBeDeleted = computed(() => props.book.location_kind === 'to_delete')

const showLocationChip = computed(() => {
  // If the evaluated status is 'Errored' or 'Processing', we want to show the location chip
  // even if the location is 'deleted' or 'to_delete' so the user knows where the errored/processing book is.
  if (isErrored.value) return true
  if (isProcessing.value) return true
  // Otherwise, if the status evaluates exactly to 'Deleted' or 'To Be Deleted', we hide the redundant chip.
  if (isDeleted.value) return false
  if (isToBeDeleted.value) return false
  return true
})

const offlinerName = computed(() => matchOffliner(props.book.offliner, offlinerStore.offliners))

const canViewBookIssues = computed(() => {
  return authStore.hasPermission('book', 'update')
})
</script>
