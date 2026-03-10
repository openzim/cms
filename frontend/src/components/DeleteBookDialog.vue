<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Delete Book</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid">
          <div v-if="book" class="mb-4">
            <div class="text-body-2 mb-2">
              <strong>Book ID:</strong> <code>{{ book.id }}</code>
            </div>
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
            Choose how you want to delete this book.
          </v-alert>

          <v-radio-group v-model="deleteType" :rules="[rules.required]">
            <v-radio value="normal">
              <template #label>
                <div>
                  <div class="font-weight-medium">Normal Delete (Recommended)</div>
                  <div class="text-caption">
                    Book will be deleted after the usual grace period. This is the safe option.
                  </div>
                </div>
              </template>
            </v-radio>

            <v-radio value="force" class="mt-3">
              <template #label>
                <div>
                  <div class="font-weight-medium text-error">Force Delete (Immediate)</div>
                  <div class="text-caption">
                    Book will be deleted immediately and this will break user experience as ongoing
                    downloads will be broken. Use with extreme caution!
                  </div>
                </div>
              </template>
            </v-radio>
          </v-radio-group>

          <v-alert
            v-if="deleteType === 'force'"
            density="compact"
            class="mt-4"
            icon="mdi-shield-alert"
          >
            <div class="text-subtitle-2 mb-2">Confirmation Required</div>
            <div class="text-body-2 mb-3">
              To proceed with force delete, please type the book ID below to confirm:
            </div>

            <v-text-field
              v-model="confirmationId"
              label="Type Book ID to confirm"
              :rules="[rules.required, rules.matchBookId]"
              variant="outlined"
              density="comfortable"
              placeholder="Enter book ID"
              class="mb-0"
              persistent-hint
            />
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading">Cancel</v-btn>
        <v-btn
          :color="deleteType === 'force' ? 'error' : 'warning'"
          variant="elevated"
          @click="handleDelete"
          :loading="loading"
          :disabled="!isFormValid || loading"
        >
          {{ deleteType === 'force' ? 'Force Delete Now' : 'Delete Book' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useBookStore } from '@/stores/book'
import { useNotificationStore } from '@/stores/notification'
import type { Book } from '@/types/book'
import { formatDt } from '@/utils/format'
import { computed, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  book: Book | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  deleted: []
}>()

const bookStore = useBookStore()
const notificationStore = useNotificationStore()

const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const deleteType = ref<'normal' | 'force'>('normal')
const confirmationId = ref('')

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const isFormValid = computed(() => {
  if (!formValid.value) return false
  if (deleteType.value === 'force' && confirmationId.value !== props.book?.id) {
    return false
  }
  return true
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
  matchBookId: (value: string) => {
    if (deleteType.value === 'force') {
      return value === props.book?.id || 'Book ID does not match'
    }
    return true
  },
}

watch(isOpen, (newValue) => {
  if (newValue) {
    resetForm()
  }
})

watch(deleteType, () => {
  confirmationId.value = ''
  formRef.value?.resetValidation()
})

async function handleDelete() {
  if (!props.book) return

  loading.value = true

  const forceDelete = deleteType.value === 'force'
  const book = await bookStore.deleteBook(props.book.id, forceDelete)
  if (book) {
    emit('deleted')
    resetForm()
    isOpen.value = false
  } else {
    for (const error of bookStore.errors) {
      notificationStore.showError(error)
    }
  }
  loading.value = false
}

function handleCancel() {
  resetForm()
  isOpen.value = false
}

function resetForm() {
  deleteType.value = 'normal'
  confirmationId.value = ''
  formRef.value?.resetValidation()
}
</script>
