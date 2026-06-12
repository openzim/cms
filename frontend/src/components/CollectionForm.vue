<template>
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

    <v-text-field
      v-model="formData.article_count_change_threshold"
      label="Article Count Change Threshold (Optional)"
      type="number"
      min="0"
      max="1.0"
      density="comfortable"
      variant="outlined"
      placeholder="0.1"
      :step="0.1"
    />

    <v-text-field
      v-model="formData.media_count_change_threshold"
      label="Media Count Change Threshold (Optional)"
      type="number"
      density="comfortable"
      variant="outlined"
      placeholder="0.1"
      min="0"
      max="1.0"
      :step="0.1"
    />
  </v-form>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { useCollectionsStore } from '@/stores/collections'
import { useWarehouseStore } from '@/stores/warehouse'
import type { Collection, CollectionUpdate } from '@/types/collections'
import type { Config } from '@/config'
import constants from '@/constants'
import { computed, ref, watch, onMounted } from 'vue'

interface Props {
  collection?: Collection | null
}

const props = withDefaults(defineProps<Props>(), {
  collection: null,
})

const emit = defineEmits<{
  'update:valid': [value: boolean]
  'update:hasChanges': [value: boolean]
}>()

const config = inject<Config>(constants.config)
if (!config) {
  throw new Error('Config is not defined')
}

const collectionsStore = useCollectionsStore()
const warehouseStore = useWarehouseStore()

const formRef = ref()
const formValid = ref(false)

interface FormData {
  name: string
  warehouse_name?: string
  download_base_url?: string
  view_base_url?: string
  article_count_change_threshold?: number
  media_count_change_threshold?: number
}

const defaultArticleCountChangeThreshold = computed(() =>
  config ? config.ARTICLE_COUNT_CHANGE_THRESHOLD : undefined,
)
const defaultMediaCountChangeThreshold = computed(() =>
  config ? config.MEDIA_COUNT_CHANGE_THRESHOLD : undefined,
)

const formData = ref<FormData>({
  name: '',
  warehouse_name: '',
  download_base_url: '',
  view_base_url: '',
  article_count_change_threshold: defaultArticleCountChangeThreshold.value,
  media_count_change_threshold: defaultMediaCountChangeThreshold.value,
})

const isEditMode = computed(() => props.collection !== null)

const hasChanges = computed(() => {
  if (!isEditMode.value || !props.collection) return true

  const nameChanged = formData.value.name !== props.collection.name
  const downloadUrlChanged =
    (formData.value.download_base_url || '') !== (props.collection.download_base_url || '')
  const viewUrlChanged =
    (formData.value.view_base_url || '') !== (props.collection.view_base_url || '')

  const articleCountChanged =
    (formData.value.article_count_change_threshold || null) !=
    (props.collection.article_count_change_threshold || null)

  const mediaCountChanged =
    (formData.value.media_count_change_threshold || null) !=
    (props.collection.media_count_change_threshold || null)

  return (
    nameChanged || downloadUrlChanged || viewUrlChanged || articleCountChanged || mediaCountChanged
  )
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

onMounted(async () => {
  await warehouseStore.fetchWarehouses()
  await collectionsStore.fetchCollections()
  if (!isEditMode.value && warehouseStore.warehouses.length > 0) {
    formData.value.warehouse_name = warehouseStore.warehouses[0]
  }
})

watch(
  () => props.collection,
  (newCollection) => {
    if (newCollection) {
      resetFormToCollection(newCollection)
    } else {
      resetForm()
    }
  },
  { immediate: true },
)

watch(formValid, (newValue) => {
  emit('update:valid', newValue)
})

watch(hasChanges, (newValue) => {
  emit('update:hasChanges', newValue)
})

function resetFormToCollection(collection: Collection) {
  formData.value = {
    name: collection.name,
    warehouse_name: collection.warehouse,
    download_base_url: collection.download_base_url || '',
    view_base_url: collection.view_base_url || '',
    article_count_change_threshold: collection.article_count_change_threshold || undefined,
    media_count_change_threshold: collection.media_count_change_threshold || undefined,
  }
  formRef.value?.resetValidation()
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
      article_count_change_threshold: defaultArticleCountChangeThreshold.value,
      media_count_change_threshold: defaultMediaCountChangeThreshold.value,
    }
    formRef.value?.resetValidation()
  }
}

function getUpdatePayload(): Partial<CollectionUpdate> | null {
  if (!props.collection) return null

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

  const currentArticleCountThreshold = formData.value.article_count_change_threshold || null
  const originalArticleCountThreshold = props.collection.article_count_change_threshold || null
  if (currentArticleCountThreshold != originalArticleCountThreshold) {
    updatePayload.article_count_change_threshold = currentArticleCountThreshold
  }

  const currentMediaCountThreshold = formData.value.media_count_change_threshold || null
  const originalMediaCountThreshold = props.collection.media_count_change_threshold || null
  if (currentMediaCountThreshold != originalMediaCountThreshold) {
    updatePayload.media_count_change_threshold = currentMediaCountThreshold
  }

  return updatePayload
}

function getFormData() {
  return formData.value
}

defineExpose({
  resetFormToCollection,
  resetForm,
  getUpdatePayload,
  getFormData,
})
</script>
