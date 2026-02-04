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
          <v-select
            v-model="localFilters.location_kind"
            label="Location"
            :items="formattedLocationKindOptions"
            placeholder="Select location kind"
            variant="outlined"
            density="compact"
            hide-details
            :clearable="hasActiveFilters"
            @update:model-value="emitFilters"
            @click:clear="handleClearFilters"
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
    location_kind: string
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
      id: string
      location_kind: string
    },
  ]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref({
  id: props.filters.id,
  location_kind: props.filters.location_kind,
})

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      id: newFilters.id,
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

const hasActiveFilters = computed(() => {
  return props.filters.id.length > 0 || props.filters.location_kind.length > 0
})

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    id: localFilters.value.id,
    location_kind: localFilters.value.location_kind,
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
