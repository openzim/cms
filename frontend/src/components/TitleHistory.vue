<template>
  <HistoryViewer
    :items="props.history"
    :has-more="props.hasMore"
    :loading="props.loading"
    :paginator="props.paginator"
    :entity-id="props.titleName"
    entity-name="title"
    loading-text="Loading Title history..."
    empty-state-text="No history available for this title"
    :fetch-history-entry="fetchEntry"
    :revert-to-history="revertEntry"
    :get-history-errors="getErrors"
    :compute-diff="computeTitleDiff"
    @load="handleLoad"
    @revert="handleRevert"
  />
</template>

<script setup lang="ts">
import HistoryViewer from '@/components/HistoryViewer.vue'
import type { HistoryItem } from '@/components/HistoryViewer.vue'
import { useTitleHistoryStore } from '@/stores/titleHistory'
import type { Paginator } from '@/types/base'
import type { TitleHistorySchema } from '@/types/title'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'

const props = defineProps<{
  history: TitleHistorySchema[]
  hasMore: boolean
  loading: boolean
  paginator: Paginator
  titleName: string
}>()

const emit = defineEmits<{
  load: [{ limit: number; skip: number }]
  revert: []
}>()

const titleHistoryStore = useTitleHistoryStore()

const fetchEntry = async (
  titleName: string,
  historyId: string,
): Promise<TitleHistorySchema | null> => {
  return await titleHistoryStore.fetchHistoryEntry(titleName, historyId)
}

const revertEntry = async (
  titleName: string,
  historyId: string,
  comment?: string,
): Promise<boolean> => {
  return await titleHistoryStore.revertToHistory(titleName, historyId, comment)
}

const getErrors = (): string[] => {
  return titleHistoryStore.errors
}

const computeTitleDiff = (
  item1: HistoryItem & TitleHistorySchema,
  item2: HistoryItem & TitleHistorySchema,
): EnhancedDiff[] | undefined => {
  // Extract the subset from both items (excluding id, author, comment, created_at)
  const { id, author, comment, created_at, illustration_48x48_at_1_hash, ...subset1 } = item1
  const {
    id: _id,
    author: _author,
    comment: _comment,
    created_at: _created_at,
    illustration_48x48_at_1_hash: _hash,
    ...subset2
  } = item2

  // Suppress unused variable warnings for destructured variables
  void id
  void author
  void comment
  void created_at
  void illustration_48x48_at_1_hash
  void _id
  void _author
  void _comment
  void _created_at
  void _hash

  const hash1 = item1.illustration_48x48_at_1_hash
  const hash2 = item2.illustration_48x48_at_1_hash
  if (hash1 != null && hash2 != null && hash1 === hash2) {
    subset1.illustration_48x48_at_1 = null
    subset2.illustration_48x48_at_1 = null
  }

  const differences = diff(subset1, subset2)

  if (!differences) {
    return undefined
  }

  // Enhance differences with blob metadata
  return differences.map((diff) => {
    const enhanced: EnhancedDiff = { ...diff }
    if (diff.path?.includes('illustration_48x48_at_1')) {
      enhanced.isBlob = true
    }
    return enhanced
  }) as EnhancedDiff[]
}

const handleLoad = (params: { limit: number; skip: number }) => {
  emit('load', params)
}

const handleRevert = () => {
  emit('revert')
}
</script>
