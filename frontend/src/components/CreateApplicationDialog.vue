<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-headline-small pa-4 bg-primary">
        <span class="text-white">Create New Application</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid" @submit.prevent="submit">
          <v-autocomplete
            v-model="selectedTitleId"
            :items="titleOptions"
            :loading="loadingTitles"
            item-title="name"
            item-value="id"
            label="Title"
            placeholder="Search for a title..."
            variant="outlined"
            density="compact"
            no-data-text="No titles found"
            :rules="requiredRules"
            @update:search="onTitleSearch"
            @update:model-value="onTitleSelected"
          />

          <v-select
            v-model="flavour"
            :items="flavourOptions"
            item-title="title"
            item-value="value"
            label="Flavour"
            :disabled="!selectedTitleId"
            variant="outlined"
            density="compact"
            no-data-text="No flavours available"
            :rules="flavourRules"
          />

          <v-select
            v-model="store"
            :items="storeOptions"
            label="Store"
            variant="outlined"
            density="compact"
            :rules="requiredRules"
          />

          <v-text-field
            v-model="name"
            label="Application name"
            hint="Branded app identifier (e.g. tunisie)"
            persistent-hint
            :rules="nameRules"
            variant="outlined"
            density="compact"
            class="mt-4"
          />

          <v-switch
            v-model="enabled"
            :label="enabled ? 'Enabled for build' : 'Disabled for build'"
            color="primary"
            hide-details
            class="mt-2"
          />

          <v-alert v-if="error" type="error" density="compact" variant="tonal" class="mt-4">
            {{ error }}
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" :disabled="saving" @click="isOpen = false">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :loading="saving"
          :disabled="!formValid || saving"
          @click="submit"
        >
          Create Application
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useApplicationStore } from '@/stores/application'
import { useTitleStore } from '@/stores/title'
import type { Application, ApplicationCreate } from '@/types/application'
import type { Title, TitleLight } from '@/types/title'
import type { ApplicationStore } from '@/types/appBuild'
import { flavourLabel, storeLabel } from '@/utils/format'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [application: Application]
}>()

const applicationStore = useApplicationStore()
const titleStore = useTitleStore()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const formRef = ref()
const formValid = ref(false)
const loadingTitles = ref(false)
const saving = ref(false)
const error = ref('')

const titleOptions = ref<TitleLight[]>([])
const selectedTitleId = ref<string | null>(null)
const selectedTitle = ref<Title | null>(null)
const flavour = ref<string | null>(null)
const store = ref<ApplicationStore>('android')
const name = ref('')
const enabled = ref(true)

const SEARCH_DEBOUNCE_MS = 300
let searchTimeout: ReturnType<typeof setTimeout> | null = null
let searchRequestId = 0
let lastSearch = ''

const requiredRules = [(value: unknown) => !!value || 'This field is required']
const flavourRules = [
  (value: unknown) => (value !== null && value !== undefined) || 'Flavour is required',
]
const nameRules = [
  (value: unknown) => (typeof value === 'string' && value.trim() !== '') || 'Name is required',
  (value: unknown) =>
    (typeof value === 'string' && /^[a-z0-9_-]+$/.test(value)) ||
    'Only lowercase letters, digits, hyphens and underscores are allowed',
]

const flavourOptions = computed(
  () =>
    selectedTitle.value?.flavours.map((item) => ({
      title: flavourLabel(item.flavour),
      value: item.flavour,
    })) ?? [],
)

const storeOptions = [
  { title: storeLabel('android'), value: 'android' },
  { title: storeLabel('apple'), value: 'apple' },
]

const reset = async () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
    searchTimeout = null
  }
  selectedTitleId.value = null
  selectedTitle.value = null
  flavour.value = null
  store.value = 'android'
  name.value = ''
  enabled.value = true
  error.value = ''
  formValid.value = false
  formRef.value?.resetValidation()
  await loadTitles('')
}

const loadTitles = async (search: string) => {
  const requestId = ++searchRequestId
  loadingTitles.value = true
  try {
    const titles = await titleStore.fetchTitles(
      20,
      0,
      search || undefined,
      undefined,
      false,
      undefined,
      'name',
    )
    if (requestId !== searchRequestId) return
    titleOptions.value = titles ?? []
    lastSearch = search
  } finally {
    if (requestId === searchRequestId) {
      loadingTitles.value = false
    }
  }
}

const onTitleSearch = (search: string) => {
  if (search === lastSearch) return
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    searchTimeout = null
    void loadTitles(search)
  }, SEARCH_DEBOUNCE_MS)
}

const onTitleSelected = async (titleId: string | null) => {
  const titleIdToLoad = titleId
  selectedTitle.value = null
  flavour.value = null
  if (!titleIdToLoad) return

  const title = await titleStore.fetchTitleById(titleIdToLoad, true)
  if (selectedTitleId.value !== titleIdToLoad) return

  selectedTitle.value = title
  if (selectedTitle.value) {
    flavour.value = selectedTitle.value.flavours[0]?.flavour ?? null
  }
}

const submit = async () => {
  if (!selectedTitle.value || flavour.value === null) return

  saving.value = true
  error.value = ''
  try {
    const payload: ApplicationCreate = {
      title_id: selectedTitle.value.id,
      flavour: flavour.value,
      store: store.value,
      enabled: enabled.value,
      name: name.value.trim(),
    }
    const result = await applicationStore.createApplication(payload)
    if (!result) {
      error.value = applicationStore.errors.join(', ') || 'Failed to create application'
      applicationStore.clearErrors()
      return
    }
    emit('created', result)
    isOpen.value = false
  } finally {
    saving.value = false
  }
}

watch(
  () => props.modelValue,
  async (open) => {
    applicationStore.clearErrors()
    if (open) {
      await reset()
    } else if (searchTimeout) {
      clearTimeout(searchTimeout)
      searchTimeout = null
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
})
</script>
