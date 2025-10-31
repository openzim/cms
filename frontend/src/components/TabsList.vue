<template>
  <div>
    <v-tabs v-model="activeTab" color="primary" slider-color="primary" class="mb-4">
      <v-tab
        base-color="primary"
        v-for="tabOption in tabOptions"
        :key="tabOption.value"
        :value="tabOption.value"
        class="text-none text-subtitle-2"
        @click="$emit('tab-changed', tabOption.value)"
      >
        {{ tabOption.label }}
      </v-tab>
    </v-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  activeTab: string
  tabOptions: { value: string; label: string }[]
}>()

defineEmits<{
  'tab-changed': [activeTab: string]
}>()

// Reactive data
const activeTab = ref(props.activeTab)

// Watch for prop changes to update active tab
watch(
  () => props.activeTab,
  (newTab) => {
    activeTab.value = newTab
  },
)
</script>
