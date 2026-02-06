<!-- Authentication Page

  - gets username and password
  - authenticates on the API
  - retrieve and store token in store
  - handles own login/error
  - save token info in cookie if asked to remember -->

<template>
  <v-container class="fill-height">
    <v-row justify="center" align="center">
      <v-col cols="12" sm="8" md="6" lg="4">
        <v-card class="elevation-12">
          <v-card-text class="text-center pa-4">
            <!-- Logo -->
            <div class="mb-3">
              <img src="/assets/logo.svg" alt="CMS Logo" width="48" height="48" />
            </div>

            <h1 class="text-h5 mb-4 font-weight-medium">Please sign in</h1>

            <v-btn
              variant="outlined"
              color="primary"
              size="large"
              block
              class="mb-4 kiwix-btn"
              @click="signInWithKiwix"
            >
              <span class="flex-grow-1">Sign in with Kiwix</span>
              <img src="/assets/kiwix-icon.svg" alt="Kiwix" class="kiwix-icon" />
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRoute } from 'vue-router'

const route = useRoute()
const authStore = useAuthStore()

const signInWithKiwix = async () => {
  // Store current route for redirect after authentication
  const redirect = route.query.redirect as string
  if (redirect) {
    sessionStorage.setItem('auth_redirect', redirect)
  }
  await authStore.authenticate()
}
</script>

<style scoped>
.v-card {
  border-radius: 8px;
}

.v-text-field {
  border-radius: 6px;
}

.v-btn {
  border-radius: 6px;
  text-transform: none;
  font-weight: 500;
}

.kiwix-icon {
  width: 24px;
  height: 24px;
  margin-left: 8px;
}
</style>
