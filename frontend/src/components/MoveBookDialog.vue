<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Move Book</span>
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
            Select the destination to move this book.
          </v-alert>

          <v-select
            v-model="destination"
            label="Destination"
            :items="availableDestinations"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />

          <v-alert
            v-if="destination"
            type="warning"
            density="compact"
            class="mt-4"
            icon="mdi-alert"
            variant="tonal"
          >
            Moving this book to {{ destination }} will trigger file operations. This action cannot
            be undone immediately.
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="handleSubmit"
          :loading="loading"
          :disabled="!formValid || loading"
        >
          Move Book
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
  moved: []
}>()

const bookStore = useBookStore()
const notificationStore = useNotificationStore()

const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const destination = ref<'staging' | 'prod' | ''>('')

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const availableDestinations = computed(() => {
  if (!props.book) return []

  const destinations: Array<{ title: string; value: 'staging' | 'prod' }> = []
  const currentLocation = props.book.location_kind

  if (currentLocation !== 'staging') {
    destinations.push({ title: 'Staging', value: 'staging' })
  }

  if (currentLocation !== 'prod') {
    destinations.push({ title: 'Production', value: 'prod' })
  }

  return destinations
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

watch(isOpen, (newValue) => {
  if (newValue) {
    resetForm()
    // Auto-select destination if only one option is available
    if (availableDestinations.value.length === 1) {
      destination.value = availableDestinations.value[0].value
    }
  }
})

async function handleSubmit() {
  if (!formValid.value || !props.book || !destination.value) return

  loading.value = true

  const book = await bookStore.moveBook(props.book.id, destination.value)
  if (book) {
    emit('moved')
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
  destination.value = ''
  formRef.value?.resetValidation()
}
</script>
