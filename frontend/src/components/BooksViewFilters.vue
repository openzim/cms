<template>
  <v-card flat class="mb-4">
    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6" md="4">
          <v-text-field
            v-model="localFilters.name"
            label="Name"
            placeholder="Search by name..."
            variant="outlined"
            density="compact"
            hide-details
            @change="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-select
            v-model="localFilters.flavour"
            label="Flavour"
            :items="formattedFlavourOptions"
            placeholder="Select flavour"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            :loading="loadingFlavours"
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-select
            v-model="localFilters.status"
            label="Status"
            :items="statusOptions"
            variant="outlined"
            density="compact"
            hide-details
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-select
            v-model="localFilters.collection"
            label="Collection"
            :items="formattedCollectionOptions"
            placeholder="Select collection"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            :loading="loadingCollections"
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-menu v-model="beforeMenu" :close-on-content-click="false" location="bottom start">
            <template #activator="{ props: menuProps }">
              <v-text-field
                v-bind="menuProps"
                :model-value="localFilters.before"
                label="Before"
                placeholder="Select date"
                variant="outlined"
                density="compact"
                hide-details
                readonly
                prepend-inner-icon="mdi-calendar"
                :clearable="!!localFilters.before"
                @click:clear="clearDate('before')"
              />
            </template>
            <v-date-picker
              :model-value="localFilters.before || null"
              :max="maxDate"
              color="primary"
              @update:model-value="setDate('before', $event)"
            />
          </v-menu>
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-menu v-model="afterMenu" :close-on-content-click="false" location="bottom start">
            <template #activator="{ props: menuProps }">
              <v-text-field
                v-bind="menuProps"
                :model-value="localFilters.after"
                label="After"
                placeholder="Select date"
                variant="outlined"
                density="compact"
                hide-details
                readonly
                prepend-inner-icon="mdi-calendar"
                :clearable="!!localFilters.after"
                @click:clear="clearDate('after')"
              />
            </template>
            <v-date-picker
              :model-value="localFilters.after || null"
              :max="maxDate"
              color="primary"
              @update:model-value="setDate('after', $event)"
            />
          </v-menu>
        </v-col>
        <v-col
          v-if="hasActiveFilters"
          cols="12"
          class="d-flex flex-sm-row flex-column align-sm-center"
        >
          <v-btn size="small" variant="outlined" @click="handleClearFilters">
            <v-icon size="small" class="mr-1">mdi-close-circle</v-icon>
            clear filters
          </v-btn>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { toISODate } from '@/utils/format'
import { computed, ref, watch } from 'vue'

// Filters
interface Filters {
  name: string
  flavour: string
  status: string
  collection: string
  before: string
  after: string
}

// Props
interface Props {
  filters: Filters
  flavourOptions?: string[]
  loadingFlavours?: boolean
  collectionOptions?: string[]
  loadingCollections?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  flavourOptions: () => [],
  loadingFlavours: false,
  collectionOptions: () => [],
  loadingCollections: false,
})

// Define emits
const emit = defineEmits<{
  filtersChanged: [filters: Filters]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref<Filters>({
  name: props.filters.name,
  flavour: props.filters.flavour,
  status: props.filters.status,
  collection: props.filters.collection,
  before: props.filters.before,
  after: props.filters.after,
})

// Calendar menu states
const beforeMenu = ref(false)
const afterMenu = ref(false)

// Dates in the future cannot be selected
const maxDate = new Date()

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = { ...newFilters }
  },
)

const formattedFlavourOptions = computed(() => {
  return props.flavourOptions.map((option) => ({
    title: option,
    value: option,
  }))
})

const formattedCollectionOptions = computed(() => {
  return props.collectionOptions.map((option) => ({
    title: option,
    value: option,
  }))
})

const statusOptions = [
  { title: 'Active', value: 'active' },
  { title: 'Quarantine', value: 'quarantine' },
  { title: 'Staging', value: 'staging' },
  { title: 'Published', value: 'prod' },
  { title: 'To Be Deleted', value: 'to_delete' },
  { title: 'Deleted', value: 'deleted' },
  { title: 'All', value: 'all' },
]

const hasActiveFilters = computed(() => {
  return (
    props.filters.name.length > 0 ||
    props.filters.flavour.length > 0 ||
    props.filters.status !== 'active' ||
    props.filters.collection.length > 0 ||
    props.filters.before.length > 0 ||
    props.filters.after.length > 0
  )
})

// The date pickers work with dates, but the filters (and the query) hold ISO date strings
function setDate(key: 'before' | 'after', value: unknown) {
  localFilters.value[key] = toISODate(value as Date | string | null)
  if (key === 'before') {
    beforeMenu.value = false
  } else {
    afterMenu.value = false
  }
  emitFilters()
}

function clearDate(key: 'before' | 'after') {
  localFilters.value[key] = ''
  emitFilters()
}

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', { ...localFilters.value })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
