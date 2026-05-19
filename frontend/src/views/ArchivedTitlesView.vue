<template>
  <!-- Error Message for permissions -->
  <ErrorMessage :message="error" v-if="error" :closable="false" />

  <div v-if="canRestore">
    <TitlesBaseView route-name="archived-titles" :archived="true" :show-selection="canRestore">
      <template #actions="{ selectedTitles, restoringText, handleRestoreTitles }">
        <RestoreArchivedTitlesButton
          v-if="canRestore"
          :can-restore="canRestore"
          :restoring-text="restoringText"
          :count="selectedTitles.length"
          @restore-titles="handleRestoreTitles"
        />
      </template>
    </TitlesBaseView>
  </div>
</template>

<script setup lang="ts">
import TitlesBaseView from '@/components/TitlesBaseView.vue'
import RestoreArchivedTitlesButton from '@/components/RestoreArchivedTitlesButton.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'

import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

// Stores
const authStore = useAuthStore()

// Computed properties
const canRestore = computed(() => authStore.hasPermission('title', 'archive'))
const error = computed(() =>
  !canRestore.value ? 'You do not have permission to view archived titles.' : null,
)
</script>
