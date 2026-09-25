<template>
  <v-card elevation="2" class="border">
    <div class="d-flex flex-column align-start pa-2">
      <div class="text-subtitle-1 font-weight-medium">
        {{ flavour.flavour === '' ? 'Empty' : flavour.flavour }}
      </div>

      <div class="d-flex align-center flex-wrap mt-1 ga-1">
        <v-chip
          v-if="flavour.recipe_id"
          size="small"
          variant="tonal"
          :color="flavour.recipe_link ? 'success' : 'warning'"
        >
          {{ flavour.recipe_link ? 'Recipe available' : 'Recipe pending' }}
        </v-chip>

        <v-chip v-if="flavour.recipe_link" size="small" variant="outlined">
          <v-icon start size="small">mdi-open-in-new</v-icon>
          <a
            :href="flavour.recipe_link"
            target="_blank"
            rel="noopener noreferrer"
            class="text-decoration-none text-inherit"
            >View recipe</a
          >
        </v-chip>

        <v-chip v-if="flavour.is_rotten" size="small" variant="tonal" color="error">
          <v-icon start size="small">mdi-alert-circle</v-icon>
          Rotten
        </v-chip>

        <v-chip v-if="flavour.last_book_added_at" size="small" variant="outlined">
          <v-icon start size="small">mdi-calendar-plus</v-icon>
          Last book: {{ formatDt(flavour.last_book_added_at, 'ff') }}
        </v-chip>
      </div>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import type { TitleFlavour } from '@/types/title'
import { formatDt } from '@/utils/format'

interface Props {
  flavour: TitleFlavour
}

defineProps<Props>()
</script>

<style scoped>
.border {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
}
</style>
