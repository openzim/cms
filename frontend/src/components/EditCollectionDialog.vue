<template>
  <CollectionFormDialog v-model="isOpen" :collection="collection" @updated="handleUpdated" />
</template>

<script setup lang="ts">
import CollectionFormDialog from '@/components/CollectionFormDialog.vue'
import type { Collection } from '@/types/collections'
import { computed } from 'vue'

interface Props {
  modelValue: boolean
  collection: Collection | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  updated: [updatedCollection: { id: string; name: string }]
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

function handleUpdated(updatedCollection: { id: string; name: string }) {
  emit('updated', updatedCollection)
}
</script>
