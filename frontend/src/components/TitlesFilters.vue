<template>
  <v-card flat class="mb-4">
    <v-card-text>
      <v-row no-gutters class="justify-end">
        <v-col cols="12" sm="4">
          <slot name="actions" />
        </v-col>
      </v-row>
      <v-row class="align-center">
        <v-col cols="12" sm="4">
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
        <v-col cols="12" sm="4">
          <v-select
            v-model="localFilters.collection_name"
            :items="collectionsOptions"
            label="Collection"
            placeholder="Select a collection..."
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col v-if="hasActiveFilters" cols="12" sm="4">
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
import { ref, watch, computed } from 'vue'

// Props
interface Props {
  filters: {
    name: string
    collection_name: string
  }
  collections: string[]
}

const props = defineProps<Props>()

// Define emits
const emit = defineEmits<{
  filtersChanged: [
    filters: {
      name: string
      collection_name: string
    },
  ]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref<{ name: string; collection_name: string | null }>({
  name: props.filters.name,
  collection_name: props.filters.collection_name || null,
})

const collectionsOptions = computed(() => {
  return props.collections.map((collection) => ({
    title: collection,
    value: collection,
  }))
})

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      name: newFilters.name,
      collection_name: newFilters.collection_name,
    }
  },
  { deep: true },
)

const hasActiveFilters = computed(() => {
  return props.filters.name.length > 0 || props.filters.collection_name.length > 0
})

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    name: localFilters.value.name,
    collection_name: localFilters.value.collection_name || '',
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
