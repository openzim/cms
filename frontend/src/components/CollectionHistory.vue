<template>
  <HistoryViewer
    :items="props.history"
    :has-more="props.hasMore"
    :loading="props.loading"
    :paginator="props.paginator"
    :entity-id="props.collectionName"
    entity-name="collection"
    loading-text="Loading Collection history..."
    empty-state-text="No history available for this collection"
    :fetch-history-entry="fetchEntry"
    :revert-to-history="revertEntry"
    :get-history-errors="getErrors"
    :compute-diff="computeCollectionDiff"
    @load="handleLoad"
    @revert="handleRevert"
  />
</template>

<script setup lang="ts">
import HistoryViewer from '@/components/HistoryViewer.vue'
import type { HistoryItem } from '@/components/HistoryViewer.vue'
import { useCollectionHistoryStore } from '@/stores/collectionHistory'
import type { Paginator } from '@/types/base'
import type { CollectionHistory } from '@/types/collections'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'

const props = defineProps<{
  history: CollectionHistory[]
  hasMore: boolean
  loading: boolean
  paginator: Paginator
  collectionName: string
}>()

const emit = defineEmits<{
  load: [{ limit: number; skip: number }]
  revert: []
}>()

const collectionHistoryStore = useCollectionHistoryStore()

const fetchEntry = async (
  collectionName: string,
  historyId: string,
): Promise<CollectionHistory | null> => {
  return await collectionHistoryStore.fetchHistoryEntry(collectionName, historyId)
}

const revertEntry = async (
  collectionName: string,
  historyId: string,
  comment?: string,
): Promise<boolean> => {
  return await collectionHistoryStore.revertToHistory(collectionName, historyId, comment)
}

const getErrors = (): string[] => {
  return collectionHistoryStore.errors
}

const computeCollectionDiff = (
  item1: HistoryItem & CollectionHistory,
  item2: HistoryItem & CollectionHistory,
): EnhancedDiff[] | undefined => {
  // Extract the subset from both items (excluding id, author, comment, created_at)
  const { id, author, comment, created_at, ...subset1 } = item1
  const { id: _id, author: _author, comment: _comment, created_at: _created_at, ...subset2 } = item2

  // Suppress unused variable warnings for destructured variables
  void id
  void author
  void comment
  void created_at
  void _id
  void _author
  void _comment
  void _created_at

  return diff(subset1, subset2)
}

const handleLoad = (params: { limit: number; skip: number }) => {
  emit('load', params)
}

const handleRevert = () => {
  emit('revert')
}
</script>
