<template>
  <v-btn
    v-if="canArchive"
    color="primary"
    variant="elevated"
    size="small"
    :loading="isArchiving"
    :disabled="isDisabled"
    @click="emit('archive-titles')"
  >
    <v-icon size="small" class="mr-1">mdi-archive</v-icon>
    {{
      isArchiving ? archivingText : `Archive ${nbTitles} selected title${nbTitles !== 1 ? 's' : ''}`
    }}
  </v-btn>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Props
interface Props {
  archivingText: string | null
  canArchive: boolean
  count: number
}

const props = defineProps<Props>()

// Define emits
const emit = defineEmits<{
  'archive-titles': []
}>()

// Computed properties
const nbTitles = computed(() => props.count)
const isDisabled = computed(() => nbTitles.value < 1)
const isArchiving = computed(() => Boolean(props.archivingText))
</script>
