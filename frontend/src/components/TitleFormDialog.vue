<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">{{ isEditMode ? 'Edit Title' : 'Create New Title' }}</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            label="Title Name"
            :rules="isEditMode ? [] : [rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
            :disabled="isEditMode"
            :readonly="isEditMode"
          />

          <v-select
            v-model="formData.maturity"
            label="Maturity"
            :items="maturityOptions"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />

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
            specified. Beware of potential impact of removing a book from a location already in use
            by the library or currently being downloaded by users.
          </v-alert>
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
          {{ isEditMode ? 'Save Changes' : 'Create Title' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useCollectionsStore } from '@/stores/collections'
import { useTitleStore } from '@/stores/title'
import type { BaseTitleCollection, Title, TitleCreate } from '@/types/title'
import { computed, onMounted, ref, watch } from 'vue'

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
  updated: []
}>()

const titleStore = useTitleStore()
const collectionsStore = useCollectionsStore()

const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const loadingCollections = ref(false)
const error = ref('')

const maturityOptions = ['dev', 'robust']

const formData = ref<TitleCreate>({
  name: '',
  maturity: 'dev',
  collection_titles: [],
})

const originalCollections = ref<BaseTitleCollection[]>([])

const isEditMode = computed(() => props.title !== null)

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const collectionNames = computed(() => {
  return collectionsStore.collections.map((collection) => collection.name)
})

const getAvailableCollections = (currentIndex: number) => {
  // Get collections that are already used by other collection titles
  const usedCollections = new Set<string>()
  formData.value.collection_titles.forEach((ct, index) => {
    if (index !== currentIndex && ct.collection_name) {
      usedCollections.add(ct.collection_name)
    }
  })

  return collectionNames.value.filter((name) => !usedCollections.has(name))
}

const canAddMoreCollections = computed(() => {
  // Check if there are any collections that haven't been used yet
  const usedCollections = new Set<string>()
  formData.value.collection_titles.forEach((ct) => {
    if (ct.collection_name) {
      usedCollections.add(ct.collection_name)
    }
  })

  return collectionNames.value.length > usedCollections.size
})

const getAvailablePaths = (collectionName: string) => {
  if (!collectionName) return []

  const selectedCollection = collectionsStore.collections.find(
    (collection) => collection.name === collectionName,
  )

  return selectedCollection?.paths || []
}

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

  const maturityChanged = formData.value.maturity !== props.title?.maturity
  return maturityChanged || hasCollectionChanges.value
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

watch(
  () => props.title,
  (newTitle) => {
    if (newTitle) {
      resetFormToTitle(newTitle)
    }
  },
  { immediate: true },
)

watch(isOpen, async (newValue) => {
  if (newValue && collectionNames.value.length === 0) {
    await fetchCollections()
  }
  if (newValue) {
    if (props.title) {
      resetFormToTitle(props.title)
    } else {
      resetForm()
    }
  }
})

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
  }

  originalCollections.value = collections.map((c) => ({ ...c }))
  error.value = ''
  formRef.value?.resetValidation()
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

async function handleSubmit() {
  if (!formValid.value) return

  loading.value = true
  error.value = ''

  try {
    if (isEditMode.value && props.title) {
      await titleStore.updateTitle(props.title.id, {
        maturity: formData.value.maturity,
        collection_titles: formData.value.collection_titles,
      })
      emit('updated')
    } else {
      await titleStore.createTitle(formData.value)
      emit('created')
    }
    resetForm()
    isOpen.value = false
  } catch (err) {
    console.error(`Failed to ${isEditMode.value ? 'update' : 'create'} title`, err)
    error.value =
      titleStore.errors.join(', ') || `Failed to ${isEditMode.value ? 'update' : 'create'} title`
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  resetForm()
  isOpen.value = false
}

function resetForm() {
  if (isEditMode.value && props.title) {
    resetFormToTitle(props.title)
  } else {
    formData.value = {
      name: '',
      maturity: 'dev',
      collection_titles: [],
    }
    originalCollections.value = []
    error.value = ''
    formRef.value?.resetValidation()
  }
}

onMounted(async () => {
  await fetchCollections()
})
</script>

<style scoped>
.border {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
