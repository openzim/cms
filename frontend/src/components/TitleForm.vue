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
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('title')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.title"
            @use="useBookValue('title')"
          >
            <TitleTextField
              v-model="formData.title"
              label="Title"
              :max-graphemes="titleMaxLength"
            />
          </MetadataFieldWithDiff>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('creator')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.creator"
            @use="useBookValue('creator')"
          >
            <TitleTextField v-model="formData.creator" label="Creator" />
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('publisher')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.publisher"
            @use="useBookValue('publisher')"
          >
            <TitleTextField v-model="formData.publisher" label="Publisher" />
          </MetadataFieldWithDiff>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('language')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.language"
            @use="useBookValue('language')"
          >
            <TitleLanguageField v-model="formData.language" />
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('license')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.license"
            @use="useBookValue('license')"
          >
            <TitleTextField v-model="formData.license" label="License" />
          </MetadataFieldWithDiff>
        </v-col>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('relation')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.relation"
            @use="useBookValue('relation')"
          >
            <TitleTextField v-model="formData.relation" label="Relation" />
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12" :md="inDialog ? 12 : 6">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('source')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.source"
            @use="useBookValue('source')"
          >
            <TitleTextField v-model="formData.source" label="Source" />
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('illustration_48x48_at_1')"
            diff-label="Different from latest book which has:"
            @use="useBookValue('illustration_48x48_at_1')"
          >
            <TitleIllustrationField v-model="formData.illustration_48x48_at_1" />
            <template #diff-content>
              <div class="d-flex flex-column flex-grow-1">
                <v-img
                  :src="getImageDataUrl(bookMetadata?.illustration_48x48_at_1)"
                  width="48"
                  height="48"
                  class="rounded border w-100"
                />
                <span class="text-caption text-grey-darken-1 mt-1">{{ bookIllustrationSize }}</span>
              </div>
            </template>
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>

      <v-row>
        <v-col cols="12">
          <MetadataFieldWithDiff
            :show-diff="!inDialog && isFieldDifferent('description')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.description"
            @use="useBookValue('description')"
          >
            <TitleTextField
              v-model="formData.description"
              label="Description"
              textarea
              :max-graphemes="descriptionMaxLength"
            />
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>

      <v-row v-if="!inDialog">
        <v-col cols="12">
          <MetadataFieldWithDiff
            :show-diff="isFieldDifferent('long_description')"
            diff-label="Different from latest book which has:"
            :diff-value="bookMetadata?.long_description"
            @use="useBookValue('long_description')"
          >
            <TitleTextField
              v-model="formData.long_description"
              label="Long Description"
              textarea
              :rows="5"
            />
          </MetadataFieldWithDiff>
        </v-col>
      </v-row>
    </div>

    <v-divider class="my-6" />

    <!-- Collections Section -->
    <div>
      <TitleCollectionsField
        v-model="formData.collection_titles"
        :collections="collections"
        :disabled="collectionsDisabled"
      />

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
import TitleTextField from '@/components/TitleTextField.vue'
import TitleLanguageField from '@/components/TitleLanguageField.vue'
import TitleIllustrationField from '@/components/TitleIllustrationField.vue'
import TitleCollectionsField from '@/components/TitleCollectionsField.vue'
import MetadataFieldWithDiff from '@/components/MetadataFieldWithDiff.vue'
import type { BaseTitleCollection, Title, TitleUpdate } from '@/types/title'
import type { CollectionLight } from '@/types/collections'
import type { Book } from '@/types/book'
import { computed, inject, ref, watch } from 'vue'
import constants, { TITLE_METADATA_FIELDS, type TitleMetadataFieldKey } from '@/constants'
import type { Config } from '@/config'
import { base64ByteSize } from '@/utils/format'
import { getImageDataUrl } from '@/utils/image'

interface Props {
  title?: Title | null
  inDialog?: boolean
  latestBook?: Book | null
  collections: CollectionLight[]
  collectionsDisabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: null,
  inDialog: false,
  latestBook: null,
  collections: () => [],
  collectionsDisabled: false,
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
})

const originalCollections = ref<BaseTitleCollection[]>([])

const isEditMode = computed(() => props.title !== null && props.title.id !== '')

// Book metadata comparison
type BookMetadataFields = Record<TitleMetadataFieldKey, string | undefined>

const bookMetadata = computed<BookMetadataFields | null>(() => {
  if (!props.latestBook?.zim_metadata) return null
  const metadata = props.latestBook.zim_metadata
  return {
    name: metadata.Name as string | undefined,
    title: metadata.Title as string | undefined,
    creator: metadata.Creator as string | undefined,
    publisher: metadata.Publisher as string | undefined,
    description: metadata.Description as string | undefined,
    long_description: metadata.LongDescription as string | undefined,
    language: metadata.Language as string | undefined,
    license: metadata.License as string | undefined,
    illustration_48x48_at_1: metadata['Illustration_48x48@1'] as string | undefined,
    relation: metadata.Relation as string | undefined,
    source: metadata.Source as string | undefined,
  }
})

const isFieldDifferent = (field: keyof BookMetadataFields) => {
  if (!bookMetadata.value || !isEditMode.value) return false
  const bookValue = bookMetadata.value[field]
  const titleValue = formData.value[field as keyof typeof formData.value]
  if (bookValue === undefined) return false
  return bookValue !== titleValue
}

const hasAnyDifferences = computed(() => {
  if (!bookMetadata.value || !isEditMode.value) return false
  return TITLE_METADATA_FIELDS.some((field) => isFieldDifferent(field))
})

const useBookValue = (field: keyof BookMetadataFields) => {
  if (!bookMetadata.value) return
  const value = bookMetadata.value[field]
  if (value !== undefined) {
    ;(formData.value[field as keyof typeof formData.value] as string | null) = value
  }
}

const useAllBookValues = () => {
  if (!bookMetadata.value) return
  TITLE_METADATA_FIELDS.forEach((field) => {
    if (isFieldDifferent(field)) useBookValue(field)
  })
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
