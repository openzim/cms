<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">{{
          isEditMode ? 'Edit Collection' : 'Create New Collection'
        }}</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            label="Collection Name"
            :rules="[rules.required, rules.nameUnique]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />

          <v-select
            v-if="!isEditMode"
            v-model="formData.warehouse_name"
            :items="warehouseStore.warehouses"
            label="Warehouse Name"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />

          <v-text-field
            v-if="isEditMode"
            :model-value="collection?.warehouse"
            label="Warehouse"
            variant="outlined"
            density="comfortable"
            class="mb-2"
            readonly
            disabled
          />

          <v-text-field
            v-model="formData.download_base_url"
            label="Download Base URL (Optional)"
            :rules="[rules.validUrl]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
            placeholder="https://example.com/download"
          />

          <v-text-field
            v-model="formData.view_base_url"
            label="View Base URL (Optional)"
            :rules="[rules.validUrl]"
            variant="outlined"
            density="comfortable"
            placeholder="https://example.com/view"
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
          :disabled="!formValid || loading || (isEditMode && !hasChanges)"
        >
          {{ isEditMode ? 'Save Changes' : 'Create Collection' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useCollectionsStore } from '@/stores/collections'
import { useWarehouseStore } from '@/stores/warehouse'
import type { Collection, CollectionUpdate } from '@/types/collections'
import { computed, ref, watch, onMounted } from 'vue'

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
const warehouseStore = useWarehouseStore()

onMounted(async () => {
  await warehouseStore.fetchWarehouses()
})

const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const error = ref('')

interface FormData {
  name: string
  warehouse_name?: string
  download_base_url?: string
  view_base_url?: string
}

const formData = ref<FormData>({
  name: '',
  warehouse_name: '',
  download_base_url: '',
  view_base_url: '',
})

const isEditMode = computed(() => props.collection !== null)

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const hasChanges = computed(() => {
  if (!isEditMode.value || !props.collection) return true

  const nameChanged = formData.value.name !== props.collection.name
  const downloadUrlChanged =
    (formData.value.download_base_url || '') !== (props.collection.download_base_url || '')
  const viewUrlChanged =
    (formData.value.view_base_url || '') !== (props.collection.view_base_url || '')

  return nameChanged || downloadUrlChanged || viewUrlChanged
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
  validUrl: (value: string) => {
    if (!value) return true // optional
    try {
      new URL(value)
      return true
    } catch {
      return 'Must be a valid URL'
    }
  },
  nameUnique: (value: string) => {
    if (!value) return false
    const normalizedValue = value.toLowerCase()
    const isConflict = collectionsStore.collections.some(
      (c) => c.name.toLowerCase() === normalizedValue,
    )

    if (
      isEditMode.value &&
      props.collection &&
      props.collection.name.toLowerCase() === normalizedValue
    ) {
      return true
    }

    return !isConflict || 'A collection with this name already exists'
  },
}

watch(
  () => props.collection,
  (newCollection) => {
    if (newCollection) {
      resetFormToCollection(newCollection)
    }
  },
  { immediate: true },
)

watch(isOpen, (newValue) => {
  if (newValue) {
    if (props.collection) {
      resetFormToCollection(props.collection)
    } else {
      resetForm()
    }
  }
})

function resetFormToCollection(collection: Collection) {
  formData.value = {
    name: collection.name,
    warehouse_name: collection.warehouse,
    download_base_url: collection.download_base_url || '',
    view_base_url: collection.view_base_url || '',
  }
  error.value = ''
  formRef.value?.resetValidation()
}

async function handleSubmit() {
  if (!formValid.value) return

  loading.value = true
  error.value = ''

  try {
    if (isEditMode.value && props.collection) {
      const updatePayload: Partial<CollectionUpdate> = {}

      if (formData.value.name !== props.collection.name) {
        updatePayload.name = formData.value.name
      }

      const currentDownloadUrl = formData.value.download_base_url || ''
      const originalDownloadUrl = props.collection.download_base_url || ''
      if (currentDownloadUrl !== originalDownloadUrl) {
        updatePayload.download_base_url = currentDownloadUrl || null
      }

      const currentViewUrl = formData.value.view_base_url || ''
      const originalViewUrl = props.collection.view_base_url || ''
      if (currentViewUrl !== originalViewUrl) {
        updatePayload.view_base_url = currentViewUrl || null
      }

      const response = await collectionsStore.updateCollection(props.collection.id, updatePayload)
      if (response) {
        emit('updated', { id: response.id, name: response.name })
        resetForm()
        isOpen.value = false
      } else {
        error.value = collectionsStore.errors.join(', ') || 'Failed to update collection'
      }
    } else {
      // Create mode
      const createPayload = {
        name: formData.value.name,
        warehouse_name: formData.value.warehouse_name!,
        download_base_url: formData.value.download_base_url || undefined,
        view_base_url: formData.value.view_base_url || undefined,
      }
      const response = await collectionsStore.createCollection(createPayload)
      if (response) {
        emit('created', response.name)
        resetForm()
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
  resetForm()
  isOpen.value = false
}

function resetForm() {
  if (isEditMode.value && props.collection) {
    resetFormToCollection(props.collection)
  } else {
    formData.value = {
      name: '',
      warehouse_name: warehouseStore.warehouses.length > 0 ? warehouseStore.warehouses[0] : '',
      download_base_url: '',
      view_base_url: '',
    }
    error.value = ''
    formRef.value?.resetValidation()
  }
}
</script>
