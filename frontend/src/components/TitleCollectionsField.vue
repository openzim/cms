<template>
  <div>
    <div class="d-flex align-center justify-space-between mb-4">
      <h3 class="text-h6">Collections</h3>
      <v-btn
        v-if="!disabled"
        color="primary"
        variant="text"
        size="small"
        prepend-icon="mdi-plus"
        @click="addCollectionTitle"
        :disabled="loading || !canAddMoreCollections"
      >
        Add Collection
      </v-btn>
    </div>

    <v-alert v-if="modelValue.length === 0" type="info" density="compact" class="mb-4">
      No collections added.
    </v-alert>

    <div v-for="(ct, index) in modelValue" :key="index" class="mb-4 pa-3 border rounded">
      <div class="d-flex align-center mb-2">
        <span class="text-subtitle-2 flex-grow-1">Collection #{{ Number(index) + 1 }}</span>
        <v-btn
          v-if="!disabled"
          icon="mdi-delete"
          size="x-small"
          variant="text"
          color="error"
          @click="removeCollectionTitle(Number(index))"
        />
      </div>

      <v-select
        v-model="ct.collection_name"
        label="Collection"
        :items="getAvailableCollections(Number(index))"
        :rules="[rules.required]"
        variant="outlined"
        density="comfortable"
        class="mb-2"
        :loading="loading"
        :disabled="disabled"
        @update:model-value="handleCollectionChange(Number(index))"
      />

      <v-select
        v-model="ct.path"
        label="Path"
        :items="getAvailablePaths(ct.collection_name)"
        :rules="[rules.required]"
        variant="outlined"
        density="comfortable"
        :disabled="disabled || !ct.collection_name"
        :hint="!ct.collection_name ? 'Please select a collection first' : ''"
        persistent-hint
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CollectionLight } from '@/types/collections'
import type { BaseTitleCollection } from '@/types/title'
import { computed } from 'vue'

interface Props {
  modelValue: BaseTitleCollection[]
  collections: CollectionLight[]
  loading?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
})

const emit = defineEmits<{
  'update:modelValue': [value: BaseTitleCollection[]]
}>()

const rules = {
  required: (value: unknown) => !!value || 'This field is required',
}

const collectionNames = computed(() => {
  return props.collections.map((c) => c.name)
})

const canAddMoreCollections = computed(() => {
  const usedCollections = new Set<string>()
  props.modelValue.forEach((ct) => {
    if (ct.collection_name) usedCollections.add(ct.collection_name)
  })
  return collectionNames.value.length > usedCollections.size
})

function getAvailableCollections(currentIndex: number): string[] {
  const usedCollections = new Set<string>()
  props.modelValue.forEach((ct, index) => {
    if (index !== currentIndex && ct.collection_name) usedCollections.add(ct.collection_name)
  })
  return collectionNames.value.filter((name) => !usedCollections.has(name))
}

function getAvailablePaths(collectionName: string): string[] {
  if (!collectionName) return []
  const col = props.collections.find((c) => c.name === collectionName)
  return col?.paths || []
}

function addCollectionTitle() {
  emit('update:modelValue', [...props.modelValue, { collection_name: '', path: '' }])
}

function removeCollectionTitle(index: number) {
  const updated = [...props.modelValue]
  updated.splice(index, 1)
  emit('update:modelValue', updated)
}

function handleCollectionChange(index: number) {
  const updated = [...props.modelValue]
  updated[index] = { ...updated[index], path: '' }
  emit('update:modelValue', updated)
}
</script>

<style scoped>
.border {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>
