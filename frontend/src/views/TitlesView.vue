<template>
  <TitlesBaseView route-name="titles" :show-selection="canArchiveOrMerge">
    <template
      #actions="{
        selectedTitles,
        archivingText,
        handleArchiveTitles,
        mergingText,
        handleMergeTitles,
      }"
    >
      <ArchiveTitlesButton
        v-if="canArchive"
        :can-archive="canArchive"
        :archiving-text="archivingText"
        :count="selectedTitles.length"
        @archive-titles="handleArchiveTitles"
      />
      <MergeTitlesButton
        v-if="canMerge"
        :merging-text="mergingText"
        :count="selectedTitles.length"
        @merge-titles="handleMergeTitles"
      />
    </template>
  </TitlesBaseView>
</template>

<script setup lang="ts">
import TitlesBaseView from '@/components/TitlesBaseView.vue'
import ArchiveTitlesButton from '@/components/ArchiveTitlesButton.vue'
import MergeTitlesButton from '@/components/MergeTitlesButton.vue'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const authStore = useAuthStore()
const canArchive = computed(() => authStore.hasPermission('title', 'archive'))
const canMerge = computed(
  () => authStore.hasPermission('title', 'update') && authStore.hasPermission('title', 'delete'),
)
const canArchiveOrMerge = computed(() => canArchive.value || canMerge.value)
</script>
