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
            v-model="localFilters.location_kind"
            label="Location"
            :items="formattedLocationKindOptions"
            placeholder="Select location kind"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-select
            v-model="localFilters.flag"
            label="Flag"
            :items="flagOptions"
            placeholder="Select flag"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-text-field
            v-model="localFilters.scraper"
            label="Scraper"
            placeholder="Search by scraper..."
            variant="outlined"
            density="compact"
            hide-details
            @change="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-select
            v-model="localFilters.issue"
            label="Issue"
            :items="issueOptions"
            placeholder="Select issue"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="emitFilters"
          />
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
import { computed, ref, watch } from 'vue'

// Props
interface Props {
  filters: {
    name: string
    location_kind: string
    flag: string
    scraper: string
    issue: string
  }
  locationKindOptions?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  locationKindOptions: () => [],
})

// Define emits
const emit = defineEmits<{
  filtersChanged: [
    filters: {
      name: string
      location_kind: string
      flag: string
      scraper: string
      issue: string
    },
  ]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref({
  name: props.filters.name,
  location_kind: props.filters.location_kind,
  flag: props.filters.flag,
  scraper: props.filters.scraper,
  issue: props.filters.issue,
})

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      name: newFilters.name,
      location_kind: newFilters.location_kind,
      flag: newFilters.flag,
      scraper: newFilters.scraper,
      issue: newFilters.issue,
    }
  },
)

const formattedLocationKindOptions = computed(() => {
  return props.locationKindOptions.map((option) => ({
    title: option.charAt(0).toUpperCase() + option.slice(1),
    value: option,
  }))
})

const flagOptions = [
  { title: 'Needs File Operation', value: 'needs_file_operation' },
  { title: 'Needs Processing', value: 'needs_processing' },
  { title: 'Has Error', value: 'has_error' },
  { title: 'Pending Title', value: 'no_title' },
]

const issueOptions = [
  { title: 'Bad Metadata', value: 'bad metadata' },
  { title: 'Article Count', value: 'article count' },
  { title: 'Media Count', value: 'media count' },
  { title: 'Invalid Language Code', value: 'invalid language code' },
  { title: 'Flavour Mismatch', value: 'flavour mismatch' },
  { title: 'Zimcheck Error', value: 'zimcheck error' },
]

const hasActiveFilters = computed(() => {
  return (
    props.filters.name.length > 0 ||
    props.filters.location_kind.length > 0 ||
    props.filters.flag?.length > 0 ||
    props.filters.scraper.length > 0 ||
    props.filters.issue?.length > 0
  )
})

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    name: localFilters.value.name,
    location_kind: localFilters.value.location_kind,
    flag: localFilters.value.flag,
    scraper: localFilters.value.scraper,
    issue: localFilters.value.issue,
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
