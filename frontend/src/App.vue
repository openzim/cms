<script setup lang="ts">
import type { NavigationItem } from '@/components/NavBar.vue'
import NavBar from '@/components/NavBar.vue'
import NotificationSystem from '@/components/NotificationSystem.vue'
import { useLoadingStore } from '@/stores/loading'
import { onMounted, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'

// Store and router
const loadingStore = useLoadingStore()

const router = useRouter()
const ready = ref(false)

onMounted(async () => {
  loadingStore.startLoading('Loading application data...')

  loadingStore.stopLoading()
  ready.value = true
})

const navigationItems: NavigationItem[] = [
  {
    name: 'inbox',
    label: 'Inbox',
    route: 'inbox',
    icon: 'mdi-inbox',
    disabled: false,
    show: true,
  },
  {
    name: 'titles',
    label: 'Titles',
    route: 'titles',
    icon: 'mdi-bookshelf',
    disabled: false,
    show: true,
  },
]

const handleSignOut = () => {
  // authStore.logout()
  router.push({ name: 'home' })
}
</script>

<template>
  <v-app>
    <NotificationSystem />
    <header>
      <NavBar
        :navigation-items="navigationItems"
        :username="null"
        :is-logged-in="false"
        :access-token="null"
        :is-loading="loadingStore.isLoading"
        :loading-text="loadingStore.loadingText"
        @sign-out="handleSignOut"
      />
    </header>

    <v-main>
      <v-container>
        <RouterView v-if="ready" />
        <div v-else class="d-flex align-center justify-center" style="height: 80vh">
          <v-progress-circular indeterminate size="70" width="7" color="primary" />
        </div>
      </v-container>
    </v-main>
  </v-app>
</template>
