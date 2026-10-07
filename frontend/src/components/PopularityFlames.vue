<template>
  <div :aria-label="`Popularity: ${popularity} out of 100`">
    <v-icon
      v-for="index in 5"
      :key="index"
      size="small"
      :color="index <= flames ? 'orange' : 'grey-lighten-1'"
    >
      mdi-fire
    </v-icon>
    <span class="text-caption text-medium-emphasis ml-1">{{ popularity }}/100</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  popularity: number
}>()

// 1..100 popularity mapped to 1..5 flames (one per quintile)
const flames = computed(() => Math.min(5, Math.max(0, Math.ceil(props.popularity / 20))))
</script>
