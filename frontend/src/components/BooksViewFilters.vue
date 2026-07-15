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
    flavour: string
    status: string
  }
  flavourOptions?: string[]
  loadingFlavours?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  flavourOptions: () => [],
  loadingFlavours: false,
})

// Define emits
const emit = defineEmits<{
  filtersChanged: [
    filters: {
      name: string
      flavour: string
      status: string
    },
  ]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref({
  name: props.filters.name,
  flavour: props.filters.flavour,
  status: props.filters.status,
})

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      name: newFilters.name,
      flavour: newFilters.flavour,
      status: newFilters.status,
    }
  },
)

const formattedFlavourOptions = computed(() => {
  return props.flavourOptions.map((option) => ({
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
    props.filters.status !== 'active'
  )
})

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    name: localFilters.value.name,
    flavour: localFilters.value.flavour,
    status: localFilters.value.status,
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
