<template>
  <div class="border rounded pa-3 mb-4">
    <v-row no-gutters>
      <v-col cols="12" md="3">
        <span class="text-subtitle-2 mr-2">Current book</span>
      </v-col>
      <v-col cols="12" md="9" class="d-flex align-center flex-wrap ga-2">
        <template v-if="book.recipe_link || currentUrls.length > 0">
          <v-btn
            v-if="book.recipe_link"
            :href="book.recipe_link"
            target="_blank"
            prepend-icon="mdi-open-in-new"
            variant="outlined"
            size="small"
          >
            Recipe
          </v-btn>
          <ZimUrlButtons :urls="currentUrls" :loading="loadingUrls" empty-text="" />
        </template>
        <span v-else class="text-grey">No URLs</span>
      </v-col>
    </v-row>

    <template v-if="showPreviousBook">
      <v-divider class="my-2" />
      <v-row no-gutters>
        <v-col cols="12" md="3">
          <span class="text-subtitle-2 mr-2">Previous book</span>
        </v-col>
        <v-col cols="12" md="9" class="d-flex align-center flex-wrap ga-2">
          <v-btn
            v-if="previousBook?.recipe_link"
            :href="previousBook.recipe_link"
            target="_blank"
            prepend-icon="mdi-open-in-new"
            variant="outlined"
            size="small"
          >
            Recipe
          </v-btn>
          <ZimUrlButtons :urls="previousUrls" :loading="loadingUrls" empty-text="" />
          <v-btn
            :to="{ name: 'book-detail', params: { id: previousBookId } }"
            variant="outlined"
            size="small"
          >
            Open Book Details
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Book, ZimUrl } from '@/types/book'
import { useBookStore } from '@/stores/book'
import ZimUrlButtons from '@/components/ZimUrlButtons.vue'

interface Props {
  book: Book
  previousBookId: string | null
}

const props = defineProps<Props>()

const bookStore = useBookStore()

const currentUrls = ref<ZimUrl[]>([])
const previousUrls = ref<ZimUrl[]>([])
const loadingUrls = ref(false)
const previousBook = ref<Book | null>(null)

const showPreviousBook = computed(
  () => !!props.previousBookId && props.previousBookId !== props.book.id,
)

async function loadUrls() {
  loadingUrls.value = true

  const ids = [props.book.id]
  if (showPreviousBook.value && props.previousBookId) {
    ids.push(props.previousBookId)
  }

  const response = await bookStore.fetchZimUrls(ids)
  if (response?.urls) {
    currentUrls.value = response.urls[props.book.id] ?? []
    if (showPreviousBook.value && props.previousBookId) {
      previousUrls.value = response.urls[props.previousBookId] ?? []
    }
  }

  loadingUrls.value = false
}

async function loadPreviousBook() {
  if (!showPreviousBook.value || !props.previousBookId) return
  previousBook.value = await bookStore.fetchBook(props.previousBookId)
}

watch(
  () => `${props.book.id}:${props.previousBookId ?? ''}`,
  () => {
    currentUrls.value = []
    previousUrls.value = []
    previousBook.value = null
    loadUrls()
    loadPreviousBook()
  },
  { immediate: true },
)
</script>
