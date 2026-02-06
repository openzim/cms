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
  }
}

const props = defineProps<Props>()

// Define emits
const emit = defineEmits<{
  filtersChanged: [
    filters: {
      id: string
    },
  ]
  clearFilters: []
}>()

// Local filters state
const localFilters = ref({
  id: props.filters.id,
})

// Watch for prop changes and update local state
watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      id: newFilters.id,
    }
  },
  { deep: true },
)

const hasActiveFilters = computed(() => {
  return props.filters.id.length > 0
})

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    id: localFilters.value.id,
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
