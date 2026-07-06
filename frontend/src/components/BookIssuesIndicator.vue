<template>
  <v-menu
    v-if="book.issues && book.issues.length"
    :close-on-content-click="false"
    v-model="menuOpen"
  >
    <template #activator="{ props: menuProps }">
      <v-chip
        v-bind="menuProps"
        size="x-small"
        color="warning"
        variant="flat"
        style="width: fit-content"
      >
        <v-icon size="x-small" class="mr-1">mdi-alert</v-icon>
        {{ book.issues.length }}
      </v-chip>
    </template>

    <v-list class="pa-2" density="compact">
      <v-list-item
        v-for="(warning, index) in book.issues"
        :key="index"
        class="py-0"
        style="min-height: unset"
      >
        <template #prepend>
          <span class="mr-2">•</span>
        </template>
        <v-list-item-title class="text-wrap">{{ warning }}</v-list-item-title>
      </v-list-item>

      <div v-if="canViewBookIssues">
        <v-divider class="my-0" />
        <v-btn
          color="primary"
          variant="elevated"
          size="small"
          block
          :to="{
            name: 'book-detail-tab',
            params: { id: book.id, selectedTab: 'issues' },
          }"
          @click="menuOpen = false"
        >
          <v-icon size="small" class="mr-1">mdi-alert-circle</v-icon>
          View Issues
        </v-btn>
      </div>
    </v-list>
  </v-menu>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Book, BookLight } from '@/types/book'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const menuOpen = ref(false)

defineProps<{
  book: Book | BookLight
}>()

const canViewBookIssues = computed(() => {
  return authStore.hasPermission('book', 'update')
})
</script>
