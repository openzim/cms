<template>
  <v-form ref="formRef" v-model="formValid">
    <!-- Basic Settings Section -->
    <div class="mb-6">
      <h3 class="text-h6 mb-4">Basic Settings</h3>
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
          <v-switch
            v-model="isStable"
            color="primary"
            density="comfortable"
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
      <v-row>
        <v-col cols="12">
          <v-combobox
            v-model="formData.flavours"
            label="Expected Flavours"
            variant="outlined"
            density="compact"
            clearable
            chips
            multiple
            closable-chips
            hint="Press Enter to add a new flavour or select from available options"
            persistent-hint
            :items="availableFlavours"
            :loading="loadingFlavours"
          />
        </v-col>
      </v-row>
    </div>

    <v-divider class="my-6" />

    <!-- Metadata Section -->
    <div class="mb-6">
      <div class="d-flex align-center justify-space-between mb-4">
        <h3 class="text-h6">Metadata</h3>
        <v-btn
          v-if="!inDialog && hasAnyDifferences"
          color="primary"
          variant="elevated"
          size="small"
          prepend-icon="mdi-download"
          @click="useAllBookValues"
        >
          Use All from Latest Book
        </v-btn>
      </div>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <v-text-field
            v-model="formData.title"
            label="Title"
            variant="outlined"
            density="comfortable"
            clearable
            :color="!inDialog && isFieldDifferent('title') ? 'warning' : undefined"
            :base-color="!inDialog && isFieldDifferent('title') ? 'warning' : undefined"
          />
          <div v-if="!inDialog && isFieldDifferent('title')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.title }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('title')"
              >
                Use this
              </v-btn>
            </div>
          </div>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <v-text-field
            v-model="formData.creator"
            label="Creator"
            variant="outlined"
            density="comfortable"
            clearable
            :color="!inDialog && isFieldDifferent('creator') ? 'warning' : undefined"
            :base-color="!inDialog && isFieldDifferent('creator') ? 'warning' : undefined"
          />
          <div v-if="!inDialog && isFieldDifferent('creator')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.creator }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('creator')"
              >
                Use this
              </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <v-text-field
            v-model="formData.publisher"
            label="Publisher"
            variant="outlined"
            density="comfortable"
            clearable
            :color="!inDialog && isFieldDifferent('publisher') ? 'warning' : undefined"
            :base-color="!inDialog && isFieldDifferent('publisher') ? 'warning' : undefined"
          />
          <div v-if="!inDialog && isFieldDifferent('publisher')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.publisher }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('publisher')"
              >
                Use this
              </v-btn>
            </div>
          </div>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <v-text-field
            v-model="formData.language"
            label="Language"
            variant="outlined"
            density="comfortable"
            clearable
            :color="!inDialog && isFieldDifferent('language') ? 'warning' : undefined"
            :base-color="!inDialog && isFieldDifferent('language') ? 'warning' : undefined"
          />
          <div v-if="!inDialog && isFieldDifferent('language')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.language }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('language')"
              >
                Use this
              </v-btn>
            </div>
          </div>
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
            :color="!inDialog && isFieldDifferent('license') ? 'warning' : undefined"
            :base-color="!inDialog && isFieldDifferent('license') ? 'warning' : undefined"
          />
          <div v-if="!inDialog && isFieldDifferent('license')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.license }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('license')"
              >
                Use this
              </v-btn>
            </div>
          </div>
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
        <v-col cols="12">
          <ImageEditor
            v-model="formData.illustration_48x48_at_1"
            label="Illustration"
            description="Upload a 48x48 pixel illustration image"
          />
          <div
            v-if="!inDialog && isFieldDifferent('illustration_48x48_at_1')"
            class="text-body-2 mt-2 mb-2"
          >
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between mb-2">
              <v-img
                :src="getImageDataUrl(bookMetadata?.illustration_48x48_at_1)"
                width="48"
                height="48"
                class="rounded border"
              />
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('illustration_48x48_at_1')"
              >
                Use this
              </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <v-textarea
            v-model="formData.description"
            label="Description"
            variant="outlined"
            density="comfortable"
            rows="3"
            clearable
            :color="!inDialog && isFieldDifferent('description') ? 'warning' : undefined"
            :base-color="!inDialog && isFieldDifferent('description') ? 'warning' : undefined"
          />
          <div v-if="!inDialog && isFieldDifferent('description')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.description }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('description')"
              >
                Use this
              </v-btn>
            </div>
          </div>
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
            :color="isFieldDifferent('long_description') ? 'warning' : undefined"
            :base-color="isFieldDifferent('long_description') ? 'warning' : undefined"
          />
          <div v-if="isFieldDifferent('long_description')" class="text-body-2 mt-n2 mb-2">
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between">
              <strong>{{ bookMetadata?.long_description }}</strong>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('long_description')"
              >
                Use this
              </v-btn>
            </div>
          </div>
        </v-col>
      </v-row>
    </div>

    <v-divider class="my-6" />

    <!-- Collections Section -->
    <div>
      <div class="d-flex align-center justify-space-between mb-4">
        <h3 class="text-h6">Collections</h3>
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
        specified. Beware of potential impact of removing a book from a location already in use by
        the library or currently being downloaded by users.
      </v-alert>
    </div>
  </v-form>
</template>

<script setup lang="ts">
import ImageEditor from '@/components/ImageEditor.vue'
import { useCollectionsStore } from '@/stores/collections'
import { useBookStore } from '@/stores/book'
import type { BaseTitleCollection, Title, TitleUpdate } from '@/types/title'
import type { Book } from '@/types/book'
import { computed, ref, watch } from 'vue'

interface Props {
  title?: Title | null
  inDialog?: boolean
  latestBook?: Book | null
}

const props = withDefaults(defineProps<Props>(), {
  title: null,
  inDialog: false,
  latestBook: null,
})

const emit = defineEmits<{
  'update:valid': [value: boolean]
  'update:hasChanges': [value: boolean]
}>()

const collectionsStore = useCollectionsStore()
const bookStore = useBookStore()

const formRef = ref()
const formValid = ref(false)
const loadingCollections = ref(false)
const availableFlavours = ref<string[]>([])
const loadingFlavours = ref(false)

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
  flavours: [],
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

// Extract book metadata for comparison
type BookMetadataFields = {
  title: string | undefined
  creator: string | undefined
  publisher: string | undefined
  description: string | undefined
  long_description: string | undefined
  language: string | undefined
  license: string | undefined
  illustration_48x48_at_1: string | undefined
}

const bookMetadata = computed<BookMetadataFields | null>(() => {
  if (!props.latestBook?.zim_metadata) return null
  const metadata = props.latestBook.zim_metadata
  return {
    title: metadata.Title as string | undefined,
    creator: metadata.Creator as string | undefined,
    publisher: metadata.Publisher as string | undefined,
    description: metadata.Description as string | undefined,
    long_description: metadata.LongDescription as string | undefined,
    language: metadata.Language as string | undefined,
    license: metadata.License as string | undefined,
    illustration_48x48_at_1: metadata['Illustration_48x48@1'] as string | undefined,
  }
})

const isFieldDifferent = (field: keyof BookMetadataFields) => {
  if (!bookMetadata.value || !isEditMode.value) return false
  const bookValue = bookMetadata.value[field]
  const titleValue = formData.value[field as keyof typeof formData.value]

  // If book has no value, don't show hint
  if (bookValue === undefined || bookValue === null) return false

  // If values are the same, don't show hint
  if (bookValue === titleValue) return false

  return true
}

const hasAnyDifferences = computed(() => {
  if (!bookMetadata.value || !isEditMode.value) return false
  const fields: (keyof BookMetadataFields)[] = [
    'title',
    'creator',
    'publisher',
    'description',
    'long_description',
    'language',
    'license',
    'illustration_48x48_at_1',
  ]
  return fields.some((field) => isFieldDifferent(field))
})

const useBookValue = (field: keyof BookMetadataFields) => {
  if (!bookMetadata.value) return
  const value = bookMetadata.value[field]
  if (value !== undefined && value !== null) {
    ;(formData.value[field as keyof typeof formData.value] as string | null) = value
  }
}

const useAllBookValues = () => {
  if (!bookMetadata.value) return
  const fields: (keyof BookMetadataFields)[] = [
    'title',
    'creator',
    'publisher',
    'description',
    'long_description',
    'language',
    'license',
    'illustration_48x48_at_1',
  ]
  fields.forEach((field) => {
    if (isFieldDifferent(field)) {
      useBookValue(field)
    }
  })
}

const getImageDataUrl = (base64String: string | undefined): string | undefined => {
  if (!base64String) return undefined
  if (base64String.startsWith('data:') || base64String.startsWith('http')) {
    return base64String
  }
  return `data:image/png;base64,${base64String}`
}

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

  // Check if flavours changed
  const titleFlavours = props.title?.flavours || []
  const formFlavours = formData.value.flavours || []
  const flavoursChanged =
    titleFlavours.length !== formFlavours.length ||
    !titleFlavours.every((f) => formFlavours.includes(f))

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
    flavoursChanged ||
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
    flavours: title.flavours ? [...title.flavours] : [],
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
    flavours: [],
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

async function fetchFlavours() {
  loadingFlavours.value = true
  try {
    const flavours = await bookStore.fetchBookFlavours()
    if (flavours) {
      availableFlavours.value = flavours
    }
  } catch (err) {
    console.error('Failed to fetch flavours', err)
  } finally {
    loadingFlavours.value = false
  }
}

function getFormData(): TitleUpdate {
  // For creation (non-edit mode), include all fields with their current values (null if not set)
  if (!isEditMode.value) {
    return {
      name: formData.value.name || '',
      maturity: formData.value.maturity || 'unstable',
      collection_titles: formData.value.collection_titles,
      title: formData.value.title || null,
      creator: formData.value.creator || null,
      publisher: formData.value.publisher || null,
      description: formData.value.description || null,
      language: formData.value.language || null,
      illustration_48x48_at_1: formData.value.illustration_48x48_at_1 || null,
      long_description: formData.value.long_description,
      license: formData.value.license,
      relation: formData.value.relation,
      source: formData.value.source,
      flavours: formData.value.flavours || [],
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

  // Check if flavours changed
  const titleFlavours = props.title.flavours || []
  const formFlavours = formData.value.flavours || []
  const flavoursChanged =
    titleFlavours.length !== formFlavours.length ||
    !titleFlavours.every((f) => formFlavours.includes(f))

  if (flavoursChanged) {
    payload.flavours = formData.value.flavours
  }

  if (hasCollectionChanges.value) {
    payload.collection_titles = formData.value.collection_titles
  }

  return payload
}

// Expose methods and data for parent components
defineExpose({
  fetchCollections,
  fetchFlavours,
  resetForm,
  resetFormToTitle,
  getFormData,
  getUpdatePayload,
  formValid,
  formData,
  hasAnyDifferences,
  useAllBookValues,
})
</script>

<style scoped>
.border {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
