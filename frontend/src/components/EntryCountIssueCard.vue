<template>
  <v-card flat variant="outlined">
    <v-card-text class="pa-3">
      <v-row class="ga-3 px-3">
        <v-col>
          <v-icon color="brown-darken-4" size="large" class="mr-2"> mdi-alert-outline </v-icon>
          <span class="text-body-2">
            <span class="font-weight-medium">
              {{ label }} changed beyond {{ formatPercent(issue.alert_threshold) }} threshold
            </span>
          </span>
        </v-col>
      </v-row>

      <v-row class="ga-3 px-3">
        <!-- Previous book count -->
        <v-col class="bg-grey-lighten-5 pa-3 rounded">
          <div class="d-flex flex-column">
            <span class="text-caption text-medium-emphasis mb-1">Previous book</span>
            <span class="text-h6 font-weight-bold">
              {{ issue.previous_book_count.toLocaleString() }}
            </span>
          </div>
        </v-col>

        <v-col class="bg-grey-lighten-5 pa-3 rounded">
          <div class="d-flex flex-column">
            <span class="text-caption text-medium-emphasis mb-1">Current book</span>
            <span class="text-h6 font-weight-bold">
              {{ issue.current_book_count.toLocaleString() }}
            </span>
          </div>
        </v-col>

        <!-- Change summary -->
        <v-col class="bg-orange-lighten-4 pa-3 rounded text-brown-darken-4">
          <div class="d-flex flex-column">
            <span class="text-caption text-medium-emphasis mb-1">Change</span>
            <span class="text-h6 font-weight-bold">
              {{ signedDelta }} ({{ formatSignedPercent(issue.change_ratio) }})
            </span>
          </div>
        </v-col>
      </v-row>

      <v-row class="ga-3 px-3">
        <v-col>
          <span class="text-caption text-medium-emphasis"
            >Alert threshold: {{ formatPercent(issue.alert_threshold) }} ∙ only fires when current
            count differs from previous book count by
            {{ formatPercent(issue.alert_threshold) }} count.</span
          >
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { EntryCountIssue } from '@/types/book'

interface Props {
  issue: EntryCountIssue
  label: string
}

const props = defineProps<Props>()

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

const delta = computed(() => props.issue.current_book_count - props.issue.previous_book_count)

const signedDelta = computed(() => {
  const sign = delta.value > 0 ? '+' : ''
  return `${sign}${delta.value.toLocaleString()}`
})

function formatSignedPercent(value: number): string {
  const percent = value * 100
  const sign = delta.value > 0 ? '+' : '-'
  return `${sign}${percent.toFixed(1)}%`
}
</script>
