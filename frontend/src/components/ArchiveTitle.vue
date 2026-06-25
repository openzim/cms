<template>
  <v-alert
    :type="isArchived ? 'info' : 'warning'"
    variant="tonal"
    class="mb-4 mx-auto"
    width="auto"
  >
    <div class="text-body-1 mb-2">
      <template v-if="isArchived">
        You are about to <strong>restore</strong> title <code>{{ name }}</code
        >. This will make it available again for normal use.
      </template>
      <template v-else>
        You are about to <strong>archive</strong> title <code>{{ name }}</code
        >. This will delete title books, hide title from the main title list but preserve title
        configuration data in archive.
      </template>
    </div>

    <v-form @submit.prevent="confirmAction">
      <v-row dense>
        <v-col cols="12">
          <span class="text-body-2"> Please type the title name to confirm: </span>
        </v-col>

        <v-col cols="12" sm="6">
          <v-text-field
            v-model="formName"
            placeholder="Type title name here"
            density="compact"
            variant="outlined"
            hide-details
            autofocus
          />
        </v-col>

        <v-col cols="12" sm="6">
          <v-btn
            type="submit"
            :disabled="!ready"
            :color="isArchived ? 'info' : 'warning'"
            variant="elevated"
            class="mr-2"
          >
            {{ isArchived ? 'Restore' : 'Archive' }} title
          </v-btn>
        </v-col>
      </v-row>
    </v-form>

    <!-- Archive/Restore Confirm Dialog -->
    <ConfirmDialog
      v-model="showConfirmDialog"
      :title="`${isArchived ? 'Restore' : 'Archive'} title`"
      :confirm-text="isArchived ? 'Restore' : 'Archive'"
      cancel-text="Cancel"
      :confirm-color="isArchived ? 'info' : 'warning'"
      :icon="isArchived ? 'mdi-archive-arrow-up' : 'mdi-archive'"
      :max-width="600"
      :icon-color="isArchived ? 'info' : 'warning'"
      @confirm="handleConfirmAction"
      @cancel="showConfirmDialog = false"
    >
      <template #content>
        <div>
          <p class="text-body-2 text-medium-emphasis">
            {{
              isArchived
                ? `You are about to restore title '${name}'. This will make it available again for normal use.`
                : `You are about to archive title '${name}'. This will delete title books, hide title from the main title list but preserve title configuration data in archive.`
            }}
          </p>
        </div>
      </template>
    </ConfirmDialog>
  </v-alert>
</template>

<script setup lang="ts">
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { computed, ref } from 'vue'

// Props
const props = defineProps<{
  name: string
  isArchived: boolean
}>()

const emit = defineEmits<{
  (e: 'archive-title'): void
  (e: 'restore-title'): void
}>()

// Reactive data
const formName = ref('')
const showConfirmDialog = ref(false)

// Computed properties
const ready = computed(() => props.name && formName.value && props.name === formName.value)

// Methods
const confirmAction = () => {
  if (ready.value) {
    showConfirmDialog.value = true
  }
}

const handleConfirmAction = () => {
  if (props.isArchived) {
    emit('restore-title')
  } else {
    emit('archive-title')
  }
  showConfirmDialog.value = false
  formName.value = '' // Reset form name for next use
}
</script>
