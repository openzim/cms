<template>
  <div>
    <div v-if="loading" class="text-center pa-4">
      <v-progress-circular indeterminate size="32" />
      <div class="mt-2 text-body-2 text-medium-emphasis">Loading issues...</div>
    </div>

    <div
      v-else-if="!issueMap || Object.keys(issueMap).length === 0"
      class="text-center pa-4 text-medium-emphasis"
    >
      No issues found for this book.
    </div>

    <div v-else>
      <BookIssueToolbar v-if="book" :book="book" :previous-book-id="previousBookId" />
      <v-expansion-panels v-model="openPanels" multiple variant="accordion">
        <v-expansion-panel
          v-for="(reasons, issueKey) in issueMap"
          :key="issueKey"
          :title="issueKey"
          :value="issueKey"
        >
          <template #text>
            <div v-if="isEntryCountIssueKey(issueKey)" class="d-flex flex-column">
              <EntryCountIssueCard
                v-for="(issue, index) in toEntryCountIssues(reasons.issues)"
                :key="index"
                :issue="issue"
                :label="issueKey === 'media count' ? 'Media count' : 'Article count'"
              />
            </div>

            <div v-else-if="issueKey === 'metadata mismatch'" class="border pa-2 rounded mt-0">
              <template v-if="metadataDifferences">
                <div class="text-subtitle-2 mb-2">Book Metadata vs Title Metadata:</div>
                <DiffViewer :differences="metadataDifferences" />
              </template>
              <div v-else class="text-center pa-2 text-body-2 text-medium-emphasis">
                No metadata differences found.
              </div>
            </div>

            <div v-else-if="issueKey === 'invalid language code'" class="border pa-2 rounded mt-0">
              <div class="text-body-2 text-wrap">
                Book has unknown language code(s):
                <span class="font-weight-medium">{{ joinLanguageCodes(reasons.issues) }}</span>
              </div>
            </div>

            <div v-else-if="issueKey === 'flavour mismatch'" class="d-flex flex-column">
              <div
                v-for="(issue, index) in toFlavourMismatches(reasons.issues)"
                :key="index"
                class="border pa-2 rounded mb-2"
              >
                <div class="text-body-2 text-wrap">
                  Book flavour
                  <span class="font-weight-medium">{{ issue.book_flavour }}</span>
                  is not in list of title flavours
                  <span class="font-weight-medium">{{ issue.title_flavours.join(', ') }}</span>
                </div>
              </div>
            </div>

            <div v-else-if="issueKey === 'recipe issue'" class="d-flex flex-column">
              <RecipeMismatchItem
                v-for="(issue, index) in toRecipeMismatches(reasons.issues)"
                :key="index"
                :issue="issue"
              />
            </div>

            <v-list
              v-else
              density="compact"
              class="py-0 overflow-y-auto striped-list"
              border
              style="max-height: 300px"
            >
              <v-list-item
                v-for="(message, index) in toMessages(reasons.issues)"
                :key="index"
                class="px-3 py-1"
              >
                <v-list-item-title class="text-body-2 text-wrap">{{ message }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </template>

          <template #title>
            <div class="d-flex align-center">
              <v-icon color="warning" size="small" class="mr-2">mdi-alert-circle</v-icon>
              <span class="text-capitalize">{{ issueKey }}</span>
              <v-chip size="x-small" class="ml-2" variant="flat" color="warning">
                {{ reasons.issues.length }}
              </v-chip>
            </div>
          </template>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { diff } from 'deep-diff'
import type {
  BadMetadata,
  Book,
  BookIssueResponse,
  EntryCountIssue,
  FlavourMismatch,
  InvalidLanguageCode,
  KnownIssues,
  MetadaMismatch,
  RecipeMismatch,
  ZimcheckIssue,
} from '@/types/book'
import type { EnhancedDiff } from '@/utils/diff'
import DiffViewer from '@/components/DiffViewer.vue'
import EntryCountIssueCard from '@/components/EntryCountIssueCard.vue'
import RecipeMismatchItem from '@/components/RecipeMismatchItem.vue'
import BookIssueToolbar from '@/components/BookIssueToolbar.vue'

interface Props {
  issue: BookIssueResponse | null
  loading: boolean
  book: Book | null
}

const props = defineProps<Props>()

const issueMap = computed(() => props.issue?.issues ?? null)
const previousBookId = computed(() => props.issue?.previous_book_id ?? null)

const openPanels = ref<string[]>([])
watch(
  () => issueMap.value,
  (map) => {
    openPanels.value = map ? Object.keys(map) : []
  },
  { immediate: true },
)

const ENTRY_COUNT_ISSUE_KEYS = ['media count', 'article count'] as const

function isEntryCountIssueKey(key: string): boolean {
  return (ENTRY_COUNT_ISSUE_KEYS as readonly string[]).includes(key)
}

function toEntryCountIssues(reasons: KnownIssues[]): EntryCountIssue[] {
  return reasons as EntryCountIssue[]
}

function toFlavourMismatches(reasons: KnownIssues[]): FlavourMismatch[] {
  return reasons as FlavourMismatch[]
}

function toRecipeMismatches(reasons: KnownIssues[]): RecipeMismatch[] {
  return reasons as RecipeMismatch[]
}

function toInvalidLanguageCodes(reasons: KnownIssues[]): InvalidLanguageCode[] {
  return reasons as InvalidLanguageCode[]
}

function toMessages(reasons: KnownIssues[]): string[] {
  return (reasons as (BadMetadata | ZimcheckIssue)[]).map(
    (reason) => reason.message.charAt(0).toUpperCase() + reason.message.slice(1),
  )
}

function joinLanguageCodes(reasons: KnownIssues[]): string {
  return toInvalidLanguageCodes(reasons)
    .map((issue) => issue.code)
    .join(', ')
}

const metadataMismatches = computed<MetadaMismatch[]>(() => {
  return (issueMap.value?.['metadata mismatch']?.issues ?? []) as MetadaMismatch[]
})

const metadataDifferences = computed(() => {
  if (metadataMismatches.value.length === 0) return undefined

  const bookMetadata: Record<string, string | null> = {}
  const titleMetadata: Record<string, string | null> = {}
  for (const item of metadataMismatches.value) {
    bookMetadata[item.name] = item.book_value ?? null
    titleMetadata[item.name] = item.title_value ?? null
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
