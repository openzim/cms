<template>
  <HistoryViewer
    :items="props.history"
    :has-more="props.hasMore"
    :loading="props.loading"
    :paginator="props.paginator"
    :entity-id="props.bookId"
    entity-name="book"
    loading-text="Loading Book history..."
    empty-state-text="No history available for this book"
    :fetch-history-entry="fetchEntry"
    :revert-to-history="revertEntry"
    :get-history-errors="getErrors"
    :compute-diff="computeBookDiff"
    @load="handleLoad"
    @revert="handleRevert"
  />
</template>

<script setup lang="ts">
import HistoryViewer from '@/components/HistoryViewer.vue'
import type { HistoryItem } from '@/components/HistoryViewer.vue'
import { useBookHistoryStore } from '@/stores/bookHistory'
import type { Paginator } from '@/types/base'
import type { BookHistory } from '@/types/book'
import type * as DeepDiff from 'deep-diff'
import { diff } from 'deep-diff'

const props = defineProps<{
  history: BookHistory[]
  hasMore: boolean
  loading: boolean
  paginator: Paginator
  bookId: string
}>()

const emit = defineEmits<{
  load: [{ limit: number; skip: number }]
  revert: []
}>()

const bookHistoryStore = useBookHistoryStore()

const fetchEntry = async (bookId: string, historyId: string): Promise<BookHistory | null> => {
  return await bookHistoryStore.fetchHistoryEntry(bookId, historyId)
}

const revertEntry = async (
  bookId: string,
  historyId: string,
  comment?: string,
): Promise<boolean> => {
  return await bookHistoryStore.revertToHistory(bookId, historyId, comment)
}

const getErrors = (): string[] => {
  return bookHistoryStore.errors
}

const computeBookDiff = (
  item1: HistoryItem & BookHistory,
  item2: HistoryItem & BookHistory,
): DeepDiff.Diff<Record<string, unknown>, Record<string, unknown>>[] | undefined => {
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
