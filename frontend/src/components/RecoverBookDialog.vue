<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Recover Book</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <div v-if="book" class="mb-4">
          <div v-if="book.name" class="text-body-2 mb-2">
            <strong>Name:</strong> {{ book.name }}
          </div>
          <div v-if="book.flavour" class="text-body-2 mb-2">
            <strong>Flavour:</strong> {{ book.flavour }}
          </div>
          <div v-if="book.date" class="text-body-2 mb-2">
            <strong>Date:</strong> {{ book.date }}
          </div>
          <div class="text-body-2 mb-2">
            <strong>Created:</strong> {{ formatDt(book.created_at) }}
          </div>
        </div>
        <v-alert type="info" density="compact" class="mb-4" variant="tonal">
          This will recover the book and cancel the deletion process.
        </v-alert>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="handleRecover"
          :loading="loading"
          :disabled="loading"
        >
          Recover Book
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useBookStore } from '@/stores/book'
import { useNotificationStore } from '@/stores/notification'
import { formatDt } from '@/utils/format'
import type { Book } from '@/types/book'
import { computed, ref } from 'vue'

interface Props {
  modelValue: boolean
  book: Book | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  recovered: []
}>()

const bookStore = useBookStore()
const notificationStore = useNotificationStore()

const loading = ref(false)

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

async function handleRecover() {
  if (!props.book) return

  loading.value = true

  const book = await bookStore.recoverBook(props.book.id)
  if (book) {
    emit('recovered')
    isOpen.value = false
  } else {
    for (const error of bookStore.errors) {
      notificationStore.showError(error)
    }
  }
  loading.value = false
}

function handleCancel() {
  isOpen.value = false
}
</script>
