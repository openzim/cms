<template>
  <v-card elevation="2" class="mb-3 border">
    <v-card-title class="d-flex flex-column align-start pa-4 pb-2">
      <div class="d-flex align-center flex-wrap w-100">
        <div class="text-subtitle-1 font-weight-medium">
          {{ flavour.flavour === '' ? 'Empty' : flavour.flavour }}
        </div>
      </div>

      <div class="d-flex align-center flex-wrap mt-2 ga-2">
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
    </v-card-title>

    <v-card-actions class="pa-3 justify-end">
      <v-tooltip v-if="canDelete" location="top">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            icon="mdi-delete"
            variant="text"
            size="small"
            color="error"
            :disabled="disabled"
            @click="showDialog = true"
          />
        </template>
        <span>Delete flavour</span>
      </v-tooltip>
    </v-card-actions>

    <ConfirmDialog
      v-model="showDialog"
      title="Delete Flavour"
      confirm-text="Delete Flavour"
      cancel-text="Cancel"
      confirm-color="error"
      icon="mdi-delete"
      icon-color="error"
      :max-width="500"
      @confirm="handleConfirm"
      @cancel="showDialog = false"
    >
      <template #content>
        <p class="mb-3">
          Are you sure you want to delete the flavour
          <strong>{{ flavour.flavour === '' ? 'Empty' : flavour.flavour }}</strong
          >?
        </p>
        <p class="text-body-2 text-medium-emphasis">
          Books belonging to this title with this flavour will be marked for deletion. This action
          cannot be undone.
        </p>
      </template>
    </ConfirmDialog>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import type { TitleFlavour } from '@/types/title'
import { formatDt } from '@/utils/format'

interface Props {
  flavour: TitleFlavour
  canDelete?: boolean
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  canDelete: false,
  disabled: false,
})

const emit = defineEmits<{
  delete: [flavour: string]
}>()

const showDialog = ref(false)

const handleConfirm = () => {
  showDialog.value = false
  emit('delete', props.flavour.flavour)
}
</script>
