<template>
  <TitleFormDialog v-model="isOpen" :title="title" @updated="handleUpdated" />
</template>

<script setup lang="ts">
import TitleFormDialog from '@/components/TitleFormDialog.vue'
import type { Title } from '@/types/title'
import { computed } from 'vue'

interface Props {
  modelValue: boolean
  title: Title | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  updated: []
}>()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

function handleUpdated() {
  emit('updated')
}
</script>
