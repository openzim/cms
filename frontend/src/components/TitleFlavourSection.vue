<template>
  <div>
    <v-divider v-if="showHeader" class="my-3" color="primary" thickness="2">
      <span class="text-primary text-body-large">{{ flavourLabel }}</span>
    </v-divider>

    <div v-if="flavourInfo" class="d-flex align-center flex-wrap ga-2 mb-3">
      <v-chip
        v-if="flavourInfo.recipe_id"
        size="small"
        variant="tonal"
        :color="flavourInfo.recipe_link ? 'success' : 'warning'"
      >
        {{ flavourInfo.recipe_link ? 'Recipe available' : 'Recipe pending' }}
      </v-chip>

      <v-chip v-if="flavourInfo.recipe_link" size="small" variant="outlined">
        <v-icon start size="small">mdi-open-in-new</v-icon>
        <a
          :href="flavourInfo.recipe_link"
          target="_blank"
          rel="noopener noreferrer"
          class="text-decoration-none text-inherit"
          >View recipe</a
        >
      </v-chip>

      <v-chip v-if="flavourInfo.is_rotten" size="small" variant="tonal" color="error">
        <v-icon start size="small">mdi-alert-circle</v-icon>
        Rotten
      </v-chip>

      <v-chip v-if="flavourInfo.last_book_added_at" size="small" variant="outlined">
        <v-icon start size="small">mdi-calendar-plus</v-icon>
        Last book added on: {{ formatDt(flavourInfo.last_book_added_at, 'ff') }}
      </v-chip>

      <v-chip v-if="flavourInfo.archived" size="small" variant="tonal" color="grey">
        <v-icon start size="small">mdi-eye-off</v-icon>
        Hidden from catalog
      </v-chip>

      <v-chip
        v-if="flavourInfo.temporary_manual_review"
        size="small"
        variant="tonal"
        color="warning"
      >
        <v-icon start size="small">mdi-alert-circle</v-icon>
        Temporary manual review
      </v-chip>
    </div>

    <div v-if="canManageFlavours && flavourInfo" class="d-flex flex-wrap align-center ga-2 mb-3">
      <v-btn
        size="small"
        variant="text"
        :prepend-icon="
          flavourInfo!.temporary_manual_review ? 'mdi-close-circle' : 'mdi-shield-alert-outline'
        "
        @click="showManualReviewConfirm = true"
      >
        {{
          flavourInfo!.temporary_manual_review
            ? 'Remove temporary manual review'
            : 'Require manual review temporarily'
        }}
      </v-btn>

      <v-btn
        size="small"
        variant="text"
        :prepend-icon="flavourInfo!.archived ? 'mdi-eye' : 'mdi-eye-off'"
        @click="showArchiveConfirm = true"
      >
        {{ flavourInfo!.archived ? 'Show in catalog' : 'Hide from catalog' }}
      </v-btn>
    </div>

    <ConfirmDialog
      v-if="flavourInfo"
      v-model="showManualReviewConfirm"
      :title="
        flavourInfo.temporary_manual_review
          ? 'Remove Temporary Manual Review'
          : 'Enable Temporary Manual Review'
      "
      :message="
        flavourInfo.temporary_manual_review
          ? `Remove temporary manual review for flavour '${flavourLabel}'? Books of this flavour will no longer be held for manual review until it is enabled again.`
          : `Require manual review for flavour '${flavourLabel}' until its next book is moved to production?`
      "
      :confirm-text="flavourInfo.temporary_manual_review ? 'Remove' : 'Enable'"
      :icon="flavourInfo.temporary_manual_review ? 'mdi-close-circle' : 'mdi-shield-alert'"
      @confirm="
        $emit('toggle-temporary-manual-review', flavour, !flavourInfo.temporary_manual_review)
      "
    />

    <ConfirmDialog
      v-if="flavourInfo"
      v-model="showArchiveConfirm"
      :title="flavourInfo.archived ? 'Show in Catalog' : 'Hide from Catalog'"
      :message="
        flavourInfo.archived
          ? `Show flavour '${flavourLabel}' in the catalog again?`
          : `Hide flavour '${flavourLabel}' from the catalog? Its books will stay available, but the flavour will no longer be published.`
      "
      :confirm-text="flavourInfo.archived ? 'Show' : 'Hide'"
      :confirm-color="flavourInfo.archived ? 'primary' : 'warning'"
      :icon="flavourInfo.archived ? 'mdi-eye' : 'mdi-eye-off'"
      @confirm="$emit('toggle-archive', flavour, !flavourInfo.archived)"
    />

    <v-row v-if="books.length > 0">
      <v-col v-for="book in books" :key="book.id" cols="12" sm="6" md="4" lg="3">
        <BookCard
          :book="book"
          :show-urls="true"
          :show-flavour="false"
          :zim-urls="zimUrls"
          :loading-urls="loadingUrls"
          :offliners="offliners"
        />
      </v-col>
    </v-row>
    <span v-else class="text-grey">No books</span>
  </div>
</template>

<script setup lang="ts">
import BookCard from '@/components/BookCard.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import type { BookLight, ZimUrl } from '@/types/book'
import type { TitleFlavour } from '@/types/title'
import { formatDt } from '@/utils/format'
import { computed, ref } from 'vue'

interface Props {
  flavour: string
  flavourInfo?: TitleFlavour | null
  books: BookLight[]
  showHeader?: boolean
  canManageFlavours?: boolean
  zimUrls?: Record<string, ZimUrl[]>
  loadingUrls?: boolean
  offliners?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  flavourInfo: null,
  showHeader: true,
  canManageFlavours: false,
  zimUrls: undefined,
  loadingUrls: false,
  offliners: () => [],
})

defineEmits<{
  'toggle-archive': [flavour: string, archived: boolean]
  'toggle-temporary-manual-review': [flavour: string, temporaryManualReview: boolean]
}>()

const showManualReviewConfirm = ref(false)
const showArchiveConfirm = ref(false)

const flavourLabel = computed(() => (props.flavour === '' ? 'Empty' : props.flavour))
</script>
