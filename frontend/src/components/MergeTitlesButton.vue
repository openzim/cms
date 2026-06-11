<template>
  <v-btn
    :color="isDisabled ? undefined : 'blue-darken-1'"
    variant="elevated"
    size="small"
    :loading="isMerging"
    :disabled="isDisabled"
    @click="emit('merge-titles')"
  >
    <v-icon size="small" class="mr-1">mdi-merge</v-icon>
    {{ isMerging ? mergingText : `Merge ${nbTitles} selected title${nbTitles !== 1 ? 's' : ''}` }}
  </v-btn>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  mergingText: string | null
  count: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'merge-titles': []
}>()

const nbTitles = computed(() => props.count)
const isDisabled = computed(() => nbTitles.value < 2)
const isMerging = computed(() => Boolean(props.mergingText))
</script>
