<template>
  <div>
    <div v-if="loading" class="text-center pa-4">
      <v-progress-circular indeterminate size="32" />
      <div class="mt-2 text-body-2 text-medium-emphasis">Loading issues...</div>
    </div>

    <div
      v-else-if="!issues || Object.keys(issues).length === 0"
      class="text-center pa-4 text-medium-emphasis"
    >
      No issues found for this book.
    </div>

    <v-expansion-panels v-else variant="accordion">
      <v-expansion-panel v-for="(reasons, issueKey) in issues" :key="issueKey" :title="issueKey">
        <template #text>
          <v-list
            v-if="issueKey !== 'metadata mismatch'"
            density="compact"
            class="py-0 overflow-y-auto striped-list"
            border
            style="max-height: 300px"
          >
            <v-list-item v-for="(reason, index) in reasons" :key="index" class="px-3 py-1">
              <v-list-item-title class="text-body-2 text-wrap">{{ reason }}</v-list-item-title>
            </v-list-item>
          </v-list>

          <div
            v-if="issueKey === 'metadata mismatch' && metadataDifferences"
            class="border pa-2 rounded mt-0"
          >
            <div class="text-subtitle-2 mb-2">Book Metadata vs Title Metadata:</div>
            <DiffViewer :differences="metadataDifferences" />
          </div>
        </template>

        <template #title>
          <div class="d-flex align-center">
            <v-icon color="warning" size="small" class="mr-2">mdi-alert-circle</v-icon>
            <span class="text-capitalize">{{ issueKey }}</span>
            <v-chip size="x-small" class="ml-2" variant="flat" color="warning">
              {{ reasons.length }}
            </v-chip>
          </div>
        </template>
      </v-expansion-panel>
    </v-expansion-panels>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { diff } from 'deep-diff'
import type { Book } from '@/types/book'
import type { Title } from '@/types/title'
import type { EnhancedDiff } from '@/utils/diff'
import DiffViewer from '@/components/DiffViewer.vue'

interface Props {
  issues: Record<string, string[]> | null
  loading: boolean
  book: Book | null
  title: Title | null
}

const props = defineProps<Props>()

const METADATA_KEYS = [
  'Title',
  'Creator',
  'Publisher',
  'Description',
  'Language',
  'Illustration_48x48@1',
] as const

type MetadataKey = (typeof METADATA_KEYS)[number]

const metadataDifferences = computed(() => {
  if (!props.book || !props.title) return undefined

  const metadata = props.book.zim_metadata as Record<string, unknown>

  const bookMetadata: Record<MetadataKey, unknown> = {} as Record<MetadataKey, unknown>
  for (const key of METADATA_KEYS) {
    bookMetadata[key] = metadata[key] ?? null
  }

  const titleMetadata: Record<MetadataKey, unknown> = {
    Title: props.title.title,
    Creator: props.title.creator,
    Publisher: props.title.publisher,
    Description: props.title.description,
    Language: props.title.language,
    'Illustration_48x48@1': props.title.illustration_48x48_at_1,
  }

  const differences = diff(bookMetadata, titleMetadata)
  if (!differences) return undefined

  // Enhance differences with blob metadata
  return differences.map((d) => {
    const enhanced: EnhancedDiff = { ...d }
    if (d.path?.includes('Illustration_48x48@1')) {
      enhanced.isBlob = true
    }
    return enhanced
  }) as EnhancedDiff[]
})
</script>

<style scoped>
.striped-list :deep(.v-list-item:nth-child(even)) {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
}
</style>
