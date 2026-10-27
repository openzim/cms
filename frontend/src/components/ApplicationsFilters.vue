<template>
  <v-card flat class="mb-4">
    <v-card-text>
      <v-row class="align-center">
        <v-col cols="12" sm="4">
          <v-text-field
            v-model="localFilters.name"
            label="Name"
            placeholder="Search by application name..."
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @change="emitFilters"
            @click:clear="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="4">
          <v-select
            v-model="localFilters.store"
            :items="storeOptions"
            label="Store"
            placeholder="Select a store..."
            variant="outlined"
            density="compact"
            hide-details
            clearable
            @update:model-value="emitFilters"
          />
        </v-col>
        <v-col cols="12" sm="4">
          <slot name="actions" />
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
import { storeLabel } from '@/utils/format'
import { computed, ref, watch } from 'vue'

interface Filters {
  name: string
  store: string
}

const props = defineProps<{
  filters: Filters
}>()

const emit = defineEmits<{
  filtersChanged: [filters: Filters]
  clearFilters: []
}>()

const localFilters = ref<{ name: string; store: string | null }>({
  name: props.filters.name,
  store: props.filters.store || null,
})

const storeOptions = [
  { title: storeLabel('android'), value: 'android' },
  { title: storeLabel('apple'), value: 'apple' },
]

const hasActiveFilters = computed(() => {
  return props.filters.name.length > 0 || props.filters.store.length > 0
})

watch(
  () => props.filters,
  (newFilters) => {
    localFilters.value = {
      name: newFilters.name,
      store: newFilters.store || null,
    }
  },
  { deep: true },
)

function emitFilters() {
  emit('filtersChanged', {
    name: localFilters.value.name,
    store: localFilters.value.store || '',
  })
}

function handleClearFilters() {
  emit('clearFilters')
}
</script>
