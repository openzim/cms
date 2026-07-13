<template>
  <div>
    <v-row no-gutters class="py-2 align-center">
      <v-col cols="12" sm="4">
        <span class="text-body-1 font-weight-medium">{{
          flavour.flavour === '' ? 'Empty' : flavour.flavour
        }}</span>
      </v-col>
      <v-col cols="12" sm="6">
        <a
          v-if="flavour.recipe_link"
          :href="flavour.recipe_link"
          target="_blank"
          rel="noopener noreferrer"
          class="text-decoration-none"
        >
          <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
          View recipe on Zimfarm
        </a>
        <span v-else class="text-grey">Zimfarm recipe pending</span>
      </v-col>
      <v-col cols="12" sm="2" class="text-right">
        <v-btn
          v-if="canDelete"
          icon="mdi-delete"
          variant="text"
          size="small"
          color="error"
          :disabled="disabled"
          @click="showDialog = true"
        />
      </v-col>
    </v-row>
    <v-divider class="my-2"></v-divider>

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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import type { TitleFlavour } from '@/types/title'

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
