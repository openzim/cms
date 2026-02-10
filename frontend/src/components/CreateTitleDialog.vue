<template>
  <v-dialog v-model="isOpen" max-width="800px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Create New Title</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            label="Title Name"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
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
          :disabled="!formValid || loading"
        >
          Create Title
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useCollectionsStore } from '@/stores/collections'
import { useTitleStore } from '@/stores/title'
import type { BaseTitleCollection, TitleCreate } from '@/types/title'
import { computed, onMounted, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: []
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

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

watch(isOpen, async (newValue) => {
  if (newValue && collectionNames.value.length === 0) {
    await fetchCollections()
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
    await titleStore.createTitle(formData.value)
    emit('created')
    resetForm()
    isOpen.value = false
  } catch (err) {
    console.error('Failed to create title', err)
    error.value = titleStore.errors.join(', ') || 'Failed to create title'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  resetForm()
  isOpen.value = false
}

function resetForm() {
  formData.value = {
    name: '',
    maturity: 'dev',
    collection_titles: [],
  }
  error.value = ''
  formRef.value?.resetValidation()
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
