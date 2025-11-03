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
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

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

// Emit filters when they change
function emitFilters() {
  emit('filtersChanged', {
    id: localFilters.value.id,
  })
}
</script>
