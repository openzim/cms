<template>
  <HistoryViewer
    :items="props.history"
    :has-more="props.hasMore"
    :loading="props.loading"
    :paginator="props.paginator"
    :entity-id="`${props.name} (${storeLabel(props.store)})`"
    entity-name="application"
    loading-text="Loading Application history..."
    empty-state-text="No history available for this application"
    :fetch-history-entry="fetchEntry"
    :revert-to-history="revertEntry"
    :get-history-errors="getErrors"
    :compute-diff="computeApplicationDiff"
    @load="handleLoad"
    @revert="handleRevert"
  />
</template>

<script setup lang="ts">
import HistoryViewer from '@/components/HistoryViewer.vue'
import type { HistoryItem } from '@/components/HistoryViewer.vue'
import { useApplicationHistoryStore } from '@/stores/applicationHistory'
import type { ApplicationHistory } from '@/types/application'
import type { Paginator } from '@/types/base'
import type { PublicationStore } from '@/types/publication'
import type { EnhancedDiff } from '@/utils/diff'
import { storeLabel } from '@/utils/format'
import { diff } from 'deep-diff'

const props = defineProps<{
  history: ApplicationHistory[]
  hasMore: boolean
  loading: boolean
  paginator: Paginator
  applicationId: string
  name: string
  store: PublicationStore
}>()

const emit = defineEmits<{
  load: [{ limit: number; skip: number }]
  revert: []
}>()

const applicationHistoryStore = useApplicationHistoryStore()

const fetchEntry = async (
  _entityId: string,
  historyId: string,
): Promise<ApplicationHistory | null> => {
  return await applicationHistoryStore.fetchHistoryEntry(props.applicationId, historyId)
}

const revertEntry = async (
  _entityId: string,
  historyId: string,
  comment?: string,
): Promise<boolean> => {
  return await applicationHistoryStore.revertToHistory(props.applicationId, historyId, comment)
}

const getErrors = (): string[] => {
  return applicationHistoryStore.errors
}

const computeApplicationDiff = (
  item1: HistoryItem & ApplicationHistory,
  item2: HistoryItem & ApplicationHistory,
): EnhancedDiff[] | undefined => {
  const { id, author, comment, created_at, title_id, title_name, ...subset1 } = item1
  const {
    id: _id,
    author: _author,
    comment: _comment,
    created_at: _created_at,
    title_id: _titleId,
    title_name: _titleName,
    ...subset2
  } = item2

  void id
  void author
  void comment
  void created_at
  void title_id
  void title_name
  void _id
  void _author
  void _comment
  void _created_at
  void _titleId
  void _titleName

  return diff(subset1, subset2) as EnhancedDiff[] | undefined
}

const handleLoad = (params: { limit: number; skip: number }) => {
  emit('load', params)
}

const handleRevert = () => {
  emit('revert')
}
</script>
