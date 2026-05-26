<template>
  <v-card flat class="mb-4">
    <v-card-text>
      <v-row>
        <v-col cols="12" sm="6" md="3">
          <v-text-field
            v-model="localFilters.id"
            label="ID"
            placeholder="Search by ID..."
            variant="outlined"
            density="compact"
            hide-details
            @change="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="3">
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
        <v-col cols="12" sm="6" md="3">
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
        <v-col cols="12" sm="6" md="3">
          <v-select
            v-model="localFilters.needs_attention"
            label="Needs Attention"
            :items="needsAttentionOptions"
            placeholder="Select needs attention"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="6" md="3">
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
    id: string
    name: string
    flavour: string
    needs_attention: string
    location_kind: string
  }
  locationKindOptions?: string[]
  flavourOptions?: string[]
  loadingFlavours?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  locationKindOptions: () => ['quarantine', 'staging', 'prod'],
  flavourOptions: () => [],
  loadingFlavours: false,
})

// Define emits
const emit = defineEmits<{
  filtersChanged: [
    filters: {
      id: string
      name: string
      flavour: string
      needs_attention: string
      location_kind: string
    },
  ]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref({
  id: props.filters.id,
  name: props.filters.name,
  flavour: props.filters.flavour,
  needs_attention: props.filters.needs_attention,
  location_kind: props.filters.location_kind,
})

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      id: newFilters.id,
      name: newFilters.name,
      flavour: newFilters.flavour,
      needs_attention: newFilters.needs_attention,
      location_kind: newFilters.location_kind,
    }
  },
)

const formattedLocationKindOptions = computed(() => {
  return props.locationKindOptions.map((option) => ({
    title: option.charAt(0).toUpperCase() + option.slice(1),
    value: option,
  }))
})

const formattedFlavourOptions = computed(() => {
  return props.flavourOptions.map((option) => ({
    title: option,
    value: option,
  }))
})

const needsAttentionOptions = [
  { title: 'All', value: 'all' },
  { title: 'Yes', value: 'yes' },
  { title: 'No', value: 'no' },
]

const hasActiveFilters = computed(() => {
  return (
    props.filters.id.length > 0 ||
    props.filters.name.length > 0 ||
    props.filters.flavour.length > 0 ||
    props.filters.needs_attention.length > 0 ||
    props.filters.location_kind.length > 0
  )
})

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    id: localFilters.value.id,
    name: localFilters.value.name,
    flavour: localFilters.value.flavour,
    needs_attention: localFilters.value.needs_attention,
    location_kind: localFilters.value.location_kind,
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
