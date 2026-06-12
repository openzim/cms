<template>
  <v-dialog v-model="isTargetDialogOpen" :max-width="600" persistent>
    <v-card>
      <v-card-title class="text-h6">
        <v-icon class="mr-2" color="primary">mdi-merge</v-icon>
        Select Target Title for Merge
      </v-card-title>

      <v-card-text class="text-body-1">
        <p class="mb-4">
          Select in which title you want to move all books. Other titles will be deleted.
        </p>
        <v-select
          v-model="targetTitle"
          :items="selectedTitles"
          label="Target Title"
          variant="outlined"
          density="comfortable"
          :rules="[(v: string) => !!v || 'Target title is required']"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :title="item.value" />
          </template>
        </v-select>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="outlined" @click="handleCancelTarget">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :disabled="!targetTitle"
          @click="handleConfirmTarget"
        >
          Continue
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Confirmation Dialog -->
  <ConfirmDialog
    v-model="isConfirmDialogOpen"
    title="Confirm Merge"
    confirm-text="Merge"
    cancel-text="Cancel"
    confirm-color="primary"
    icon="mdi-merge"
    icon-color="primary"
    :max-width="600"
    :loading="merging"
    @confirm="handleMergeConfirm"
    @cancel="handleMergeCancel"
  >
    <template #content>
      <div>
        <p class="mb-2"><strong>Target Title:</strong> {{ targetTitle }}</p>
        <div v-if="sourceTitles.length > 1">
          <p class="mb-2"><strong>Source Titles:</strong></p>
          <ul class="ml-4">
            <li v-for="title in sourceTitles" :key="title">{{ title }}</li>
          </ul>
        </div>
        <div v-else>
          <p class="mb-2"><strong>Source Title:</strong> {{ sourceTitles[0] }}</p>
        </div>
        <v-alert type="warning" variant="tonal" class="mt-4">
          This action cannot be undone. Books of source titles will be moved to the target title,
          all books (source and target) will be reprocessed and source titles will be deleted.
        </v-alert>
      </div>
    </template>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { computed, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  selectedTitles: string[]
  merging: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [target: string, sources: string[]]
  cancel: []
}>()

const isTargetDialogOpen = ref(false)
const isConfirmDialogOpen = ref(false)
const targetTitle = ref<string>('')

const sourceTitles = computed(() => {
  return props.selectedTitles.filter((title) => title !== targetTitle.value)
})

const handleCancelTarget = () => {
  targetTitle.value = ''
  isTargetDialogOpen.value = false
  emit('update:modelValue', false)
  emit('cancel')
}

const handleConfirmTarget = () => {
  if (!targetTitle.value) return
  isTargetDialogOpen.value = false
  isConfirmDialogOpen.value = true
}

const handleMergeConfirm = () => {
  emit('confirm', targetTitle.value, sourceTitles.value)
}

const handleMergeCancel = () => {
  isConfirmDialogOpen.value = false
  targetTitle.value = ''
  isTargetDialogOpen.value = true
}

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      targetTitle.value = ''
      isTargetDialogOpen.value = true
      isConfirmDialogOpen.value = false
    } else {
      isTargetDialogOpen.value = false
      isConfirmDialogOpen.value = false
    }
  },
)

watch([isTargetDialogOpen, isConfirmDialogOpen], ([target, confirm]) => {
  if (!target && !confirm) {
    emit('update:modelValue', false)
  }
})
</script>
