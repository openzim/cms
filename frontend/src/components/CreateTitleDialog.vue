<template>
  <TitleFormDialog
    v-model="isOpen"
    :available-flavours="availableFlavours"
    :collections="collections"
    @created="handleCreated"
  />
</template>

<script setup lang="ts">
import TitleFormDialog from '@/components/TitleFormDialog.vue'
import type { CollectionLight } from '@/types/collections'
import { computed } from 'vue'

interface Props {
  modelValue: boolean
  availableFlavours: string[]
  collections: CollectionLight[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: []
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

function handleCreated() {
  emit('created')
}
</script>
