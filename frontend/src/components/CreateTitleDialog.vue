<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Create New Title</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            label="Title Name"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />

          <v-text-field
            v-model="formData.maturity"
            label="Title Maturity"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />
        </v-form>

        <v-alert v-if="error" type="error" class="mt-4" density="compact">
          {{ error }}
        </v-alert>
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
          Create Title
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useTitleStore } from '@/stores/title'
import type { TitleCreate } from '@/types/title'
import { computed, ref } from 'vue'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: []
}>()

const titleStore = useTitleStore()

const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const error = ref('')

const formData = ref<TitleCreate>({
  name: '',
  maturity: 'dev',
})

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

async function handleSubmit() {
  if (!formValid.value) return

  loading.value = true
  error.value = ''

  try {
    await titleStore.createTitle(formData.value)
    emit('created')
    resetForm()
    isOpen.value = false
  } catch (err) {
    console.error('Failed to create title', err)
    error.value = titleStore.errors.join(', ') || 'Failed to create title'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  resetForm()
  isOpen.value = false
}

function resetForm() {
  formData.value = {
    name: '',
    maturity: 'dev',
  }
  error.value = ''
  formRef.value?.resetValidation()
}
</script>
