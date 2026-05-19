<template>
  <TitlesBaseView route-name="titles" :show-selection="canArchive">
    <template #actions="{ selectedTitles, archivingText, handleArchiveTitles }">
      <ArchiveTitlesButton
        v-if="canArchive"
        :can-archive="canArchive"
        :archiving-text="archivingText"
        :count="selectedTitles.length"
        @archive-titles="handleArchiveTitles"
      />
    </template>
  </TitlesBaseView>
</template>

<script setup lang="ts">
import TitlesBaseView from '@/components/TitlesBaseView.vue'
import ArchiveTitlesButton from '@/components/ArchiveTitlesButton.vue'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const authStore = useAuthStore()
const canArchive = computed(() => authStore.hasPermission('title', 'archive'))
</script>
