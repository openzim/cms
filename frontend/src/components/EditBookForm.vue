<template>
  <v-card flat>
    <v-card-text>
      <v-form ref="formRef" @submit.prevent="handleSubmit">
        <v-row>
          <v-col cols="12">
            <v-select
              v-model="localBook.flavour"
              label="Flavour"
              :items="formattedFlavourOptions"
              :rules="[rules.required]"
              variant="outlined"
              :loading="loadingFlavours"
              :disabled="loading"
            />
          </v-col>
        </v-row>

        <v-row>
          <v-col cols="12" class="d-flex justify-end">
            <v-btn
              :color="isDisabled ? undefined : 'primary'"
              type="submit"
              :loading="loading"
              :disabled="isDisabled"
            >
              Save Changes
            </v-btn>
          </v-col>
        </v-row>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { Book } from '@/types/book'
import { computed, ref, watch } from 'vue'

interface Props {
  book: Book | null
  loading?: boolean
  flavourOptions?: string[]
  loadingFlavours?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  flavourOptions: () => [],
  loadingFlavours: false,
})

const emit = defineEmits<{
  submit: [book: { flavour: string }]
}>()

const formRef = ref()

const localBook = ref({
  flavour: props.book?.flavour || '',
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

const isDisabled = computed(() => {
  return props.loading || !hasChanges.value
})

const formattedFlavourOptions = computed(() => {
  return props.flavourOptions.map((option) => ({
    title: option,
    value: option,
  }))
})

const hasChanges = computed(() => {
  if (!props.book) return false
  return localBook.value.flavour !== props.book.flavour
})

watch(
  () => props.book,
  (newBook) => {
    if (newBook) {
      localBook.value = {
        flavour: newBook.flavour || '',
      }
    }
  },
  { deep: true, immediate: true },
)

const handleSubmit = async () => {
  const { valid } = await formRef.value.validate()
  if (valid) {
    emit('submit', {
      flavour: localBook.value.flavour,
    })
  }
}
</script>
