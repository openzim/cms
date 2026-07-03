<template>
  <v-form ref="formRef" v-model="formValid">
    <!-- Basic Settings Section -->
    <div class="mb-6">
      <h3 class="text-h6 mb-4">Basic Settings</h3>
      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleNameField v-model="formData.name" />
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleMaturityField v-model="formData.maturity" />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12">
          <TitleFlavoursField v-model="formData.flavours" :available-flavours="flavours" />
        </v-col>
      </v-row>
    </div>

    <v-divider v-if="isEditMode" class="my-6" />

    <!-- Metadata Section -->
    <div v-if="isEditMode" class="mb-6">
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
          <TitleTextField v-model="formData.title" label="Title" :max-graphemes="titleMaxLength" />
          <div v-if="!inDialog && isFieldDifferent('title')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleTextField v-model="formData.creator" label="Creator" />
          <div v-if="!inDialog && isFieldDifferent('creator')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleTextField v-model="formData.publisher" label="Publisher" />
          <div v-if="!inDialog && isFieldDifferent('publisher')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleLanguageField v-model="formData.language" />
          <div v-if="!inDialog && isFieldDifferent('language')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleTextField v-model="formData.license" label="License" />
          <div v-if="!inDialog && isFieldDifferent('license')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleTextField v-model="formData.relation" label="Relation" />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <TitleTextField v-model="formData.source" label="Source" />
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <TitleIllustrationField v-model="formData.illustration_48x48_at_1" />
          <div
            v-if="!inDialog && isFieldDifferent('illustration_48x48_at_1')"
            class="text-body-2 mt-2 mb-2"
          >
            <div class="mb-1 text-warning font-weight-medium">
              Different from latest book which has:
            </div>
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex flex-column flex-grow-1">
                <v-img
                  :src="getImageDataUrl(bookMetadata?.illustration_48x48_at_1)"
                  width="48"
                  height="48"
                  class="rounded border w-100"
                />
                <span class="text-caption text-grey-darken-1 mt-1">{{ bookIllustrationSize }}</span>
              </div>
              <v-btn
                size="small"
                variant="outlined"
                color="warning"
                class="ml-3"
                @click="useBookValue('illustration_48x48_at_1')"
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <TitleTextField
            v-model="formData.description"
            label="Description"
            textarea
            :max-graphemes="descriptionMaxLength"
          />
          <div v-if="!inDialog && isFieldDifferent('description')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
      </v-row>

      <v-row v-if="!inDialog">
        <v-col cols="12">
          <TitleTextField
            v-model="formData.long_description"
            label="Long Description"
            textarea
            :rows="5"
          />
          <div v-if="isFieldDifferent('long_description')" class="text-body-2 mb-2">
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
                >Use this</v-btn
              >
            </div>
          </div>
        </v-col>
      </v-row>
    </div>

    <v-divider class="my-6" />

    <!-- Collections Section -->
    <div>
      <TitleCollectionsField v-model="formData.collection_titles" :collections="collections" />

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
import TitleNameField from '@/components/TitleNameField.vue'
import TitleMaturityField from '@/components/TitleMaturityField.vue'
import TitleFlavoursField from '@/components/TitleFlavoursField.vue'
import TitleTextField from '@/components/TitleTextField.vue'
import TitleLanguageField from '@/components/TitleLanguageField.vue'
import TitleIllustrationField from '@/components/TitleIllustrationField.vue'
import TitleCollectionsField from '@/components/TitleCollectionsField.vue'
import type { BaseTitleCollection, Title, TitleUpdate } from '@/types/title'
import type { CollectionLight } from '@/types/collections'
import type { Book } from '@/types/book'
import { computed, inject, ref, watch } from 'vue'
import constants from '@/constants'
import type { Config } from '@/config'
import { base64ByteSize } from '@/utils/format'

interface Props {
  title?: Title | null
  inDialog?: boolean
  latestBook?: Book | null
  flavours: string[]
  collections: CollectionLight[]
}

const props = withDefaults(defineProps<Props>(), {
  title: null,
  inDialog: false,
  latestBook: null,
  flavours: () => [],
  collections: () => [],
})

const emit = defineEmits<{
  'update:valid': [value: boolean]
  'update:hasChanges': [value: boolean]
}>()

const config = inject<Config>(constants.config)!

const formRef = ref()
const formValid = ref(false)

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

const isEditMode = computed(() => props.title !== null && props.title.id !== '')

// Book metadata comparison
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
  if (bookValue === undefined || bookValue === null) return false
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
    if (isFieldDifferent(field)) useBookValue(field)
  })
}

const getImageDataUrl = (base64String: string | undefined): string | undefined => {
  if (!base64String) return undefined
  if (base64String.startsWith('data:') || base64String.startsWith('http')) return base64String
  return `data:image/png;base64,${base64String}`
}

const bookIllustrationSize = computed(() => {
  const illustration = bookMetadata.value?.illustration_48x48_at_1
  if (!illustration) return ''
  return `${base64ByteSize(illustration)} bytes`
})

const hasCollectionChanges = computed(() => {
  if (!isEditMode.value) return false
  const currentCollections = formData.value.collection_titles

  if (originalCollections.value.length !== currentCollections.length) return true

  const originalSet = new Set(
    originalCollections.value.map((c) => `${c.collection_name}:${c.path}`),
  )
  const currentSet = new Set(currentCollections.map((c) => `${c.collection_name}:${c.path}`))

  for (const item of currentSet) {
    if (!originalSet.has(item)) return true
  }
  return false
})

const hasChanges = computed(() => {
  if (!isEditMode.value) return true

  const titleFlavours = props.title?.flavours || []
  const formFlavours = formData.value.flavours || []
  const flavoursChanged =
    titleFlavours.length !== formFlavours.length ||
    !titleFlavours.every((f) => formFlavours.includes(f))

  return (
    formData.value.name !== props.title?.name ||
    formData.value.maturity !== props.title?.maturity ||
    formData.value.title !== props.title?.title ||
    formData.value.creator !== props.title?.creator ||
    formData.value.publisher !== props.title?.publisher ||
    formData.value.description !== props.title?.description ||
    formData.value.language !== props.title?.language ||
    formData.value.illustration_48x48_at_1 !== props.title?.illustration_48x48_at_1 ||
    formData.value.long_description !== props.title?.long_description ||
    formData.value.license !== props.title?.license ||
    formData.value.relation !== props.title?.relation ||
    formData.value.source !== props.title?.source ||
    flavoursChanged ||
    hasCollectionChanges.value
  )
})

const titleMaxLength = config.ZIM_TITLE_MAX_LENGTH ?? 30
const descriptionMaxLength = config.ZIM_DESCRIPTION_MAX_LENGTH ?? 80

watch(formValid, (value) => emit('update:valid', value))
watch(hasChanges, (value) => emit('update:hasChanges', value))

watch(
  () => props.title,
  (newTitle) => {
    if (newTitle) resetFormToTitle(newTitle)
    else resetForm()
  },
  { immediate: true },
)

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

function getFormData(): TitleUpdate {
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

  if (formData.value.name !== props.title.name) payload.name = formData.value.name
  if (formData.value.maturity !== props.title.maturity) payload.maturity = formData.value.maturity
  if (formData.value.title !== props.title.title) payload.title = formData.value.title
  if (formData.value.creator !== props.title.creator) payload.creator = formData.value.creator
  if (formData.value.publisher !== props.title.publisher)
    payload.publisher = formData.value.publisher
  if (formData.value.description !== props.title.description)
    payload.description = formData.value.description
  if (formData.value.language !== props.title.language) payload.language = formData.value.language
  if (formData.value.illustration_48x48_at_1 !== props.title.illustration_48x48_at_1)
    payload.illustration_48x48_at_1 = formData.value.illustration_48x48_at_1
  if (formData.value.long_description !== props.title.long_description)
    payload.long_description = formData.value.long_description
  if (formData.value.license !== props.title.license) payload.license = formData.value.license
  if (formData.value.relation !== props.title.relation) payload.relation = formData.value.relation
  if (formData.value.source !== props.title.source) payload.source = formData.value.source

  const titleFlavours = props.title.flavours || []
  const formFlavours = formData.value.flavours || []
  const flavoursChanged =
    titleFlavours.length !== formFlavours.length ||
    !titleFlavours.every((f) => formFlavours.includes(f))
  if (flavoursChanged) payload.flavours = formData.value.flavours

  if (hasCollectionChanges.value) payload.collection_titles = formData.value.collection_titles

  return payload
}

defineExpose({
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
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>
