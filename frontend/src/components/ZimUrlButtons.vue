<template>
  <div v-if="loading" class="d-flex align-center">
    <v-progress-circular indeterminate size="20" width="2" />
    <span v-if="!compact" class="ml-2 text-grey">Loading URLs...</span>
  </div>
  <div v-else-if="displayUrls.length > 0">
    <v-tooltip v-for="url in displayUrls" :key="`${url.kind}-${url.collection}`" location="bottom">
      <template #activator="{ props: tooltipProps }">
        <v-btn
          v-bind="tooltipProps"
          :href="url.url"
          target="_blank"
          :icon="compact"
          :prepend-icon="compact ? undefined : url.kind === 'download' ? 'mdi-download' : 'mdi-eye'"
          :variant="compact ? 'text' : 'outlined'"
          :size="compact ? 'x-small' : 'small'"
          :class="compact ? '' : 'mr-2'"
        >
          <v-icon v-if="compact">{{ url.kind === 'download' ? 'mdi-download' : 'mdi-eye' }}</v-icon>
          <span v-else>{{ url.kind === 'download' ? 'Download' : 'View' }}</span>
        </v-btn>
      </template>
      <span>{{ url.kind === 'download' ? 'Download' : 'View' }}</span>
    </v-tooltip>
  </div>
  <span v-else class="text-grey">{{ emptyText }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ZimUrl } from '@/types/book'

const props = withDefaults(
  defineProps<{
    urls?: ZimUrl[]
    loading?: boolean
    compact?: boolean
    emptyText?: string
  }>(),
  {
    urls: undefined,
    loading: false,
    compact: false,
    emptyText: 'No URLs available',
  },
)

const displayUrls = computed(
  () => props.urls?.filter((url) => url.kind === 'view' || url.kind === 'download') ?? [],
)
</script>
