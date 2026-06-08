<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Create New Title</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <TitleForm
          ref="titleFormRef"
          :title="title"
          :in-dialog="true"
          @update:valid="formValid = $event"
          @update:has-changes="hasChanges = $event"
        />
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
import TitleForm from '@/components/TitleForm.vue'
import { useTitleStore } from '@/stores/title'
import type { Title, TitleCreate } from '@/types/title'
import { computed, ref, watch } from 'vue'
import { useNotificationStore } from '@/stores/notification'

interface Props {
  modelValue: boolean
  title?: Title | null
}

const props = withDefaults(defineProps<Props>(), {
  title: null,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: []
  updated: [updatedTitle: { id: string; name: string }]
}>()

const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const titleFormRef = ref<InstanceType<typeof TitleForm>>()
const formValid = ref(false)
const hasChanges = ref(false)
const loading = ref(false)

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

watch(isOpen, async (newValue) => {
  if (newValue) {
    await titleFormRef.value?.fetchCollections()
    await titleFormRef.value?.fetchFlavours()
  }
})

async function handleSubmit() {
  if (!formValid.value || !titleFormRef.value) return

  loading.value = true

  try {
    const formData = titleFormRef.value.getFormData() as TitleCreate
    const response = await titleStore.createTitle(formData)
    if (!response) {
      notificationStore.showError('Failed to create title')
      notificationStore.showErrors(titleStore.errors)
      return
    }
    emit('created')
    titleFormRef.value.resetForm()
    isOpen.value = false
  } catch (err) {
    notificationStore.showError('Failed to create title')
    console.error(`Failed to create title`, err)
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  titleFormRef.value?.resetForm()
  isOpen.value = false
}
</script>
