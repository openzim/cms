<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">{{
          isEditMode ? 'Edit Collection' : 'Create New Collection'
        }}</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <CollectionForm
          ref="collectionFormRef"
          :collection="collection"
          @update:valid="formValid = $event"
          @update:has-changes="hasChanges = $event"
        />

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
          :disabled="!formValid || loading || (isEditMode && !hasChanges)"
        >
          {{ isEditMode ? 'Save Changes' : 'Create Collection' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import CollectionForm from '@/components/CollectionForm.vue'
import { useCollectionsStore } from '@/stores/collections'
import type { Collection } from '@/types/collections'
import { computed, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  collection?: Collection | null
}

const props = withDefaults(defineProps<Props>(), {
  collection: null,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [name: string]
  updated: [updatedCollection: { id: string; name: string }]
}>()

const collectionsStore = useCollectionsStore()

const collectionFormRef = ref<InstanceType<typeof CollectionForm>>()
const formValid = ref(false)
const hasChanges = ref(false)
const loading = ref(false)
const error = ref('')

const isEditMode = computed(() => props.collection !== null)

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

watch(
  () => props.collection,
  (newCollection) => {
    if (newCollection) {
      collectionFormRef.value?.resetFormToCollection(newCollection)
    }
  },
  { immediate: true },
)

watch(isOpen, (newValue) => {
  if (newValue) {
    if (props.collection) {
      collectionFormRef.value?.resetFormToCollection(props.collection)
    } else {
      collectionFormRef.value?.resetForm()
    }
    error.value = ''
  }
})

async function handleSubmit() {
  if (!formValid.value || !collectionFormRef.value) return

  loading.value = true
  error.value = ''

  try {
    if (isEditMode.value && props.collection) {
      const updatePayload = collectionFormRef.value.getUpdatePayload()

      if (!updatePayload) {
        throw new Error('Failed to get update payload')
      }

      const response = await collectionsStore.updateCollection(props.collection.id, updatePayload)
      if (response) {
        emit('updated', { id: response.id, name: response.name })
        collectionFormRef.value.resetForm()
        isOpen.value = false
      } else {
        error.value = collectionsStore.errors.join(', ') || 'Failed to update collection'
      }
    } else {
      // Create mode
      const formData = collectionFormRef.value.getFormData()
      const createPayload = {
        name: formData.name,
        warehouse_name: formData.warehouse_name!,
        download_base_url: formData.download_base_url || undefined,
        view_base_url: formData.view_base_url || undefined,
      }
      const response = await collectionsStore.createCollection(createPayload)
      if (response) {
        emit('created', response.name)
        collectionFormRef.value.resetForm()
        isOpen.value = false
      } else {
        error.value = collectionsStore.errors.join(', ') || 'Failed to create collection'
      }
    }
  } catch (err) {
    console.error(`Failed to ${isEditMode.value ? 'update' : 'create'} collection`, err)
    error.value =
      collectionsStore.errors.join(', ') ||
      `Failed to ${isEditMode.value ? 'update' : 'create'} collection`
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  collectionFormRef.value?.resetForm()
  error.value = ''
  isOpen.value = false
}
</script>
