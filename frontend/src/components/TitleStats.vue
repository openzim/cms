<template>
  <v-card flat>
    <v-card-text class="pa-0">
      <div class="ml-4 mr-4 mt-2 mb-2">
        <div v-if="loading" class="text-center pa-8">
          <v-progress-circular indeterminate size="64" />
          <div class="mt-4 text-body-1">Fetching download statistics...</div>
        </div>

        <v-data-table
          v-else-if="items.length > 0"
          :headers="headers"
          :items="items"
          :items-per-page="-1"
          :density="smAndDown ? 'compact' : 'comfortable'"
          disable-sort
          hide-default-footer
          class="elevation-0"
        >
          <template #[`item.month`]="{ item }">
            <span>{{ item.month }}</span>
            <v-tooltip v-if="item.isCurrentMonth" text="Month to Date" location="top">
              <template #activator="{ props: tooltipProps }">
                <v-chip
                  v-bind="tooltipProps"
                  size="x-small"
                  color="primary"
                  variant="tonal"
                  class="ml-2"
                >
                  MTD
                </v-chip>
              </template>
            </v-tooltip>
          </template>
          <template #[`item.total`]="{ item }">
            <span class="font-weight-medium">{{ item.total }}</span>
          </template>
        </v-data-table>

        <div v-else-if="statsStore.errors.length === 0" class="text-center pa-8">
          <v-icon size="large" class="mb-2">mdi-chart-line</v-icon>
          <div class="text-body-1 text-grey">No download statistics available for this title</div>
        </div>

        <ErrorMessage v-for="error in statsStore.errors" :key="error" :message="error" />
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import ErrorMessage from '@/components/ErrorMessage.vue'
import { useStatsStore } from '@/stores/stats'
import type { TitleFlavourDownloads } from '@/types/stats'
import { DateTime } from 'luxon'
import { computed, ref, watch } from 'vue'
import { useDisplay } from 'vuetify'

interface Props {
  titleId: string
}

const props = defineProps<Props>()

const statsStore = useStatsStore()
const { smAndDown } = useDisplay()

const loading = ref(false)
const flavours = ref<TitleFlavourDownloads[]>([])

// Fetch statistics for the current and previous calendar year
const loadStats = async () => {
  loading.value = true
  const now = DateTime.now()
  const from = now.startOf('year').minus({ years: 1 }).toISODate() ?? undefined
  const to = now.toISODate() ?? undefined
  flavours.value = await statsStore.fetchTitleDownloads(props.titleId, from, to)
  loading.value = false
}

watch(() => props.titleId, loadStats, { immediate: true })

const flavourNames = computed(() => [...new Set(flavours.value.map((flavour) => flavour.flavour))])

const EMPTY_FLAVOUR_KEY = '__empty__'
const EMPTY_FLAVOUR_LABEL = 'Empty'

const flavourColumns = computed(() =>
  flavourNames.value.map((flavour) => ({
    flavour,
    key: flavour === '' ? EMPTY_FLAVOUR_KEY : flavour,
    title: flavour === '' ? EMPTY_FLAVOUR_LABEL : flavour,
  })),
)

const currentMonth = computed(() => DateTime.now().toFormat('yyyy-MM'))

// Month (YYYY-MM) to flavour download counts, aggregated from the daily stats.
const monthlyDownloads = computed(() => {
  const months = new Map<string, Map<string, number>>()
  for (const flavour of flavours.value) {
    for (const day of flavour.downloads) {
      const month = day.date.slice(0, 7)
      let counts = months.get(month)
      if (!counts) {
        counts = new Map()
        months.set(month, counts)
      }
      counts.set(flavour.flavour, (counts.get(flavour.flavour) ?? 0) + day.downloads)
    }
  }
  return months
})

const headers = computed(() => {
  const baseHeaders = [
    { title: 'Month', key: 'month' },
    { title: 'Total Downloads', key: 'total' },
  ]
  if (flavourColumns.value.length <= 1) {
    return baseHeaders
  }
  return [
    ...baseHeaders,
    {
      title: 'Downloads by Flavour',
      key: 'flavours',
      children: flavourColumns.value.map(({ key, title }) => ({ title, key })),
    },
  ]
})

const items = computed(() =>
  Array.from(monthlyDownloads.value.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([month, counts]) => {
      const row: Record<string, string | number | boolean> = {
        month: DateTime.fromFormat(month, 'yyyy-MM').toFormat('MMMM yyyy'),
        isCurrentMonth: month === currentMonth.value,
      }
      let total = 0
      for (const column of flavourColumns.value) {
        const count = counts.get(column.flavour) ?? 0
        row[column.key] = count
        total += count
      }
      row.total = total
      return row
    }),
)
</script>
