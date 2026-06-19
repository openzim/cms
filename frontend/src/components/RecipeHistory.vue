<template>
  <HistoryViewer
    :items="props.history"
    :has-more="props.hasMore"
    :loading="props.loading"
    :paginator="props.paginator"
    :entity-id="props.recipeName"
    entity-name="recipe"
    loading-text="Loading Recipe history..."
    empty-state-text="No history available for this recipe"
    :enable-revert="false"
    :fetch-history-entry="fetchEntry"
    :get-history-errors="getErrors"
    :compute-diff="computeZimfarmRecipeDiff"
    @load="handleLoad"
  />
</template>

<script setup lang="ts">
import HistoryViewer from '@/components/HistoryViewer.vue'
import type { HistoryItem } from '@/components/HistoryViewer.vue'
import { useZimfarmRecipeHistoryStore } from '@/stores/zimfarmRecipeHistory'
import type { Paginator } from '@/types/base'
import type { ZimfarmRecipeHistory } from '@/types/zimfarmRecipe'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'

const props = defineProps<{
  history: ZimfarmRecipeHistory[]
  hasMore: boolean
  loading: boolean
  paginator: Paginator
  recipeName: string
}>()

const emit = defineEmits<{
  load: [{ limit: number; skip: number }]
  revert: []
}>()

const zimfarmRecipeHistoryStore = useZimfarmRecipeHistoryStore()

const fetchEntry = async (
  recipeName: string,
  historyId: string,
): Promise<ZimfarmRecipeHistory | null> => {
  return await zimfarmRecipeHistoryStore.fetchHistoryEntry(recipeName, historyId)
}

const getErrors = (): string[] => {
  return zimfarmRecipeHistoryStore.errors
}

const computeZimfarmRecipeDiff = (
  item1: HistoryItem & ZimfarmRecipeHistory,
  item2: HistoryItem & ZimfarmRecipeHistory,
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
</script>
