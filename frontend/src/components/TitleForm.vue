<template>
  <v-form ref="formRef" v-model="formValid">
    <v-row>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.name"
          label="Title Name"
          :rules="[rules.required]"
          variant="outlined"
          density="comfortable"
        />
      </v-col>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.title"
          label="Title"
          :rules="inDialog && !isEditMode ? [rules.required] : []"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.creator"
          label="Creator"
          :rules="inDialog && !isEditMode ? [rules.required] : []"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.publisher"
          label="Publisher"
          :rules="inDialog && !isEditMode ? [rules.required] : []"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.language"
          label="Language"
          :rules="inDialog && !isEditMode ? [rules.required] : []"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.relation"
          label="Relation"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <ImageEditor
          v-model="formData.illustration_48x48_at_1"
          label="Illustration"
          :required="inDialog && !isEditMode"
          description="Upload a 48x48 pixel illustration image"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-textarea
          v-model="formData.description"
          label="Description"
          :rules="inDialog && !isEditMode ? [rules.required] : []"
          variant="outlined"
          density="comfortable"
          rows="3"
          clearable
        />
      </v-col>
    </v-row>

    <v-row v-if="!inDialog">
      <v-col cols="12">
        <v-textarea
          v-model="formData.long_description"
          label="Long Description"
          variant="outlined"
          density="comfortable"
          rows="5"
          clearable
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.license"
          label="License"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <v-text-field
          v-model="formData.source"
          label="Source"
          variant="outlined"
          density="comfortable"
          clearable
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" :md="inDialog ? 12 : 6">
        <!-- Empty column for layout in edit tab -->
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-switch
          v-model="isStable"
          color="primary"
          density="comfortable"
          :class="inDialog ? 'mb-2' : ''"
          :hint="maturityHint"
          persistent-hint
        >
          <template #label>
            <span class="text-subtitle-1"
              >Maturity: <strong>{{ formData.maturity }}</strong></span
            >
          </template>
        </v-switch>
      </v-col>
    </v-row>

    <v-divider class="my-4" />

    <div class="d-flex align-center justify-space-between mb-3">
      <h3 class="text-subtitle-1">Collection Paths</h3>
      <v-btn
        color="primary"
        variant="text"
        size="small"
        prepend-icon="mdi-plus"
        @click="addCollectionTitle"
        :disabled="loadingCollections || !canAddMoreCollections"
      >
        Add Collection
      </v-btn>
    </div>

    <v-alert
      v-if="formData.collection_titles.length === 0"
      type="info"
      density="compact"
      class="mb-4"
    >
      No collections added.
    </v-alert>

    <div
      v-for="(collectionTitle, index) in formData.collection_titles"
      :key="index"
      class="mb-4 pa-3 border rounded"
    >
      <div class="d-flex align-center mb-2">
        <span class="text-subtitle-2 flex-grow-1">Collection #{{ index + 1 }}</span>
        <v-btn
          icon="mdi-delete"
          size="x-small"
          variant="text"
          color="error"
          @click="removeCollectionTitle(index)"
        />
      </div>

      <v-select
        v-model="collectionTitle.collection_name"
        label="Collection"
        :items="getAvailableCollections(index)"
        :rules="[rules.required]"
        variant="outlined"
        density="comfortable"
        class="mb-2"
        :loading="loadingCollections"
        @update:model-value="handleCollectionChange(index)"
      />

      <v-select
        v-model="collectionTitle.path"
        label="Path"
        :items="getAvailablePaths(collectionTitle.collection_name)"
        :rules="[rules.required]"
        variant="outlined"
        density="comfortable"
        :disabled="!collectionTitle.collection_name"
        :hint="!collectionTitle.collection_name ? 'Please select a collection first' : ''"
        persistent-hint
      />
    </div>

    <v-alert
      v-if="isEditMode && hasCollectionChanges"
      type="warning"
      density="compact"
      class="mt-4"
      icon="mdi-alert"
    >
      Modifying title collections settings will cause books in production to be altered as
      specified. Beware of potential impact of removing a book from a location already in use by the
      library or currently being downloaded by users.
    </v-alert>
  </v-form>
</template>

<script setup lang="ts">
import ImageEditor from '@/components/ImageEditor.vue'
import { useCollectionsStore } from '@/stores/collections'
import type { BaseTitleCollection, Title, TitleUpdate } from '@/types/title'
import { computed, ref, watch } from 'vue'

interface Props {
  title?: Title | null
  inDialog?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: null,
  inDialog: false,
})

const emit = defineEmits<{
  'update:valid': [value: boolean]
  'update:hasChanges': [value: boolean]
}>()

const collectionsStore = useCollectionsStore()

const formRef = ref()
const formValid = ref(false)
const loadingCollections = ref(false)

const formData = ref<TitleUpdate>({
  name: '',
  maturity: 'unstable',
  collection_titles: [],
  title: null,
  creator: null,
  publisher: null,
  description: null,
  language: null,
  illustration_48x48_at_1: null,
  long_description: null,
  license: null,
  relation: null,
  source: null,
})

const originalCollections = ref<BaseTitleCollection[]>([])

const isEditMode = computed(() => props.title !== null)

const maturityHint = computed(() => {
  if (formData.value.maturity === 'unstable') {
    return 'ZIM files will go through staging first before moving to production.'
  } else if (formData.value.maturity === 'stable') {
    return 'ZIM files will go directly to production.'
  }
  return ''
})

const isStable = computed({
  get: () => formData.value.maturity === 'stable',
  set: (value: boolean) => {
    formData.value.maturity = value ? 'stable' : 'unstable'
  },
})

const collectionNames = computed(() => {
  return collectionsStore.collections.map((collection) => collection.name)
})

const canAddMoreCollections = computed(() => {
  const usedCollections = new Set<string>()
  formData.value.collection_titles.forEach((ct) => {
    if (ct.collection_name) {
      usedCollections.add(ct.collection_name)
    }
  })
  return collectionNames.value.length > usedCollections.size
})

const hasCollectionChanges = computed(() => {
  if (!isEditMode.value) return false

  const currentCollections = formData.value.collection_titles

  if (originalCollections.value.length !== currentCollections.length) {
    return true
  }

  const originalSet = new Set(
    originalCollections.value.map((c) => `${c.collection_name}:${c.path}`),
  )
  const currentSet = new Set(currentCollections.map((c) => `${c.collection_name}:${c.path}`))

  for (const item of currentSet) {
    if (!originalSet.has(item)) {
      return true
    }
  }

  return false
})

const hasChanges = computed(() => {
  if (!isEditMode.value) return true

  const nameChanged = formData.value.name !== props.title?.name
  const maturityChanged = formData.value.maturity !== props.title?.maturity
  const titleChanged = formData.value.title !== props.title?.title
  const creatorChanged = formData.value.creator !== props.title?.creator
  const publisherChanged = formData.value.publisher !== props.title?.publisher
  const descriptionChanged = formData.value.description !== props.title?.description
  const languageChanged = formData.value.language !== props.title?.language
  const illustrationChanged =
    formData.value.illustration_48x48_at_1 !== props.title?.illustration_48x48_at_1
  const longDescriptionChanged = formData.value.long_description !== props.title?.long_description
  const licenseChanged = formData.value.license !== props.title?.license
  const relationChanged = formData.value.relation !== props.title?.relation
  const sourceChanged = formData.value.source !== props.title?.source

  return (
    nameChanged ||
    maturityChanged ||
    titleChanged ||
    creatorChanged ||
    publisherChanged ||
    descriptionChanged ||
    languageChanged ||
    illustrationChanged ||
    longDescriptionChanged ||
    licenseChanged ||
    relationChanged ||
    sourceChanged ||
    hasCollectionChanges.value
  )
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

watch(formValid, (value) => {
  emit('update:valid', value)
})

watch(hasChanges, (value) => {
  emit('update:hasChanges', value)
})

watch(
  () => props.title,
  (newTitle) => {
    if (newTitle) {
      resetFormToTitle(newTitle)
    } else {
      resetForm()
    }
  },
  { immediate: true },
)

function getAvailableCollections(currentIndex: number) {
  const usedCollections = new Set<string>()
  formData.value.collection_titles.forEach((ct, index) => {
    if (index !== currentIndex && ct.collection_name) {
      usedCollections.add(ct.collection_name)
    }
  })
  return collectionNames.value.filter((name) => !usedCollections.has(name))
}

function getAvailablePaths(collectionName: string) {
  if (!collectionName) return []
  const selectedCollection = collectionsStore.collections.find(
    (collection) => collection.name === collectionName,
  )
  return selectedCollection?.paths || []
}

function addCollectionTitle() {
  const newCollectionTitle: BaseTitleCollection = {
    collection_name: '',
    path: '',
  }
  const newIndex = formData.value.collection_titles.length
  formData.value.collection_titles.push(newCollectionTitle)

  // Auto-select collection if only one is available
  const availableCollections = getAvailableCollections(newIndex)
  if (availableCollections.length === 1) {
    newCollectionTitle.collection_name = availableCollections[0]
  }
}

function removeCollectionTitle(index: number) {
  formData.value.collection_titles.splice(index, 1)
}

function handleCollectionChange(index: number) {
  // Reset path when collection changes
  formData.value.collection_titles[index].path = ''
}

function resetFormToTitle(title: Title) {
  const collections =
    title.collections?.map((tc) => ({
      collection_name: tc.collection_name,
      path: tc.path,
    })) || []

  formData.value = {
    name: title.name,
    maturity: title.maturity,
    collection_titles: collections.map((c) => ({ ...c })),
    title: title.title,
    creator: title.creator,
    publisher: title.publisher,
    description: title.description,
    language: title.language,
    illustration_48x48_at_1: title.illustration_48x48_at_1,
    long_description: title.long_description,
    license: title.license,
    relation: title.relation,
    source: title.source,
  }

  originalCollections.value = collections.map((c) => ({ ...c }))
  formRef.value?.resetValidation()
}

function resetForm() {
  formData.value = {
    name: '',
    maturity: 'unstable',
    collection_titles: [],
    title: null,
    creator: null,
    publisher: null,
    description: null,
    language: null,
    illustration_48x48_at_1: null,
    long_description: null,
    license: null,
    relation: null,
    source: null,
  }
  originalCollections.value = []
  formRef.value?.resetValidation()
}

async function fetchCollections() {
  loadingCollections.value = true
  try {
    await collectionsStore.fetchCollections()
  } catch (err) {
    console.error('Failed to fetch collections', err)
  } finally {
    loadingCollections.value = false
  }
}

function getFormData(): TitleUpdate {
  // For creation (non-edit mode), ensure required fields are not null/undefined
  if (!isEditMode.value) {
    return {
      name: formData.value.name || '',
      maturity: formData.value.maturity || 'unstable',
      collection_titles: formData.value.collection_titles,
      title: formData.value.title || '',
      creator: formData.value.creator || '',
      publisher: formData.value.publisher || '',
      description: formData.value.description || '',
      language: formData.value.language || '',
      illustration_48x48_at_1: formData.value.illustration_48x48_at_1 || '',
      long_description: formData.value.long_description,
      license: formData.value.license,
      relation: formData.value.relation,
      source: formData.value.source,
    }
  }
  return { ...formData.value }
}

function getUpdatePayload(): Partial<TitleUpdate> {
  if (!props.title) return {}

  const payload: Partial<TitleUpdate> = {}

  if (formData.value.name !== props.title.name) {
    payload.name = formData.value.name
  }

  if (formData.value.maturity !== props.title.maturity) {
    payload.maturity = formData.value.maturity
  }

  if (formData.value.title !== props.title.title) {
    payload.title = formData.value.title
  }

  if (formData.value.creator !== props.title.creator) {
    payload.creator = formData.value.creator
  }

  if (formData.value.publisher !== props.title.publisher) {
    payload.publisher = formData.value.publisher
  }

  if (formData.value.description !== props.title.description) {
    payload.description = formData.value.description
  }

  if (formData.value.language !== props.title.language) {
    payload.language = formData.value.language
  }

  if (formData.value.illustration_48x48_at_1 !== props.title.illustration_48x48_at_1) {
    payload.illustration_48x48_at_1 = formData.value.illustration_48x48_at_1
  }

  if (formData.value.long_description !== props.title.long_description) {
    payload.long_description = formData.value.long_description
  }

  if (formData.value.license !== props.title.license) {
    payload.license = formData.value.license
  }

  if (formData.value.relation !== props.title.relation) {
    payload.relation = formData.value.relation
  }

  if (formData.value.source !== props.title.source) {
    payload.source = formData.value.source
  }

  if (hasCollectionChanges.value) {
    payload.collection_titles = formData.value.collection_titles
  }

  return payload
}

// Expose methods and data for parent components
defineExpose({
  fetchCollections,
  resetForm,
  resetFormToTitle,
  getFormData,
  getUpdatePayload,
  formValid,
  formData,
})
</script>

<style scoped>
.border {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
