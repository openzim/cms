<template>
  <v-dialog :model-value="modelValue" max-width="600" @update:model-value="close">
    <v-card>
      <v-card-title class="text-h6 bg-primary">
        <v-icon class="mr-2">mdi-account-key</v-icon>
        Upload Access
      </v-card-title>

      <v-card-text class="pt-4">
        <v-alert v-if="errors.length" type="error" variant="tonal" class="mb-4" density="compact">
          {{ errors.join(', ') }}
        </v-alert>

        <div class="text-subtitle-2 mb-2">Users with upload access</div>
        <div v-if="uploaders.length === 0" class="text-body-2 text-medium-emphasis mb-4">
          No user has upload access to this title yet.
        </div>
        <v-list v-else density="compact" class="mb-4">
          <v-list-item v-for="uploader in uploaders" :key="uploader.id">
            <v-list-item-title>{{ uploader.display_name }}</v-list-item-title>
            <template #append>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="requestRevoke(uploader)"
              />
            </template>
          </v-list-item>
        </v-list>

        <div class="text-subtitle-2 mb-2">Grant access to a title-uploader</div>
        <v-autocomplete
          v-model="selectedAccountId"
          :items="availableAccounts"
          item-title="display_name"
          item-value="id"
          label="User"
          variant="outlined"
          density="compact"
          hide-details
          :loading="loading"
          no-data-text="No title-uploader account available"
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" :disabled="granting" @click="close">Close</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          :disabled="!selectedAccountId"
          :loading="granting"
          @click="grant"
        >
          Grant access
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="showRevokeDialog"
    title="Revoke Upload Access"
    :message="revokeMessage"
    confirm-text="Revoke"
    icon="mdi-account-remove"
    icon-color="error"
    :loading="revoking"
    @confirm="confirmRevoke"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useNotificationStore } from '@/stores/notification'
import { useTitleStore } from '@/stores/title'
import { useUserStore } from '@/stores/user'
import type { User } from '@/types/user'

interface Props {
  modelValue: boolean
  titleId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const titleStore = useTitleStore()
const userStore = useUserStore()
const notificationStore = useNotificationStore()

const errors = ref<string[]>([])
const loading = ref(false)
const granting = ref(false)
const revoking = ref(false)
const showRevokeDialog = ref(false)
const pendingRevoke = ref<User | null>(null)
const selectedAccountId = ref<string | null>(null)
const uploaders = ref<User[]>([])
const titleUploaderAccounts = ref<User[]>([])

const availableAccounts = computed(() =>
  titleUploaderAccounts.value.filter(
    (account) => !uploaders.value.some((uploader) => uploader.id === account.id),
  ),
)

const revokeMessage = computed(() =>
  pendingRevoke.value ? `Revoke upload access for "${pendingRevoke.value.display_name}"?` : '',
)

const loadData = async () => {
  loading.value = true
  errors.value = []
  const [accounts, currentUploaders] = await Promise.all([
    userStore.fetchUsers(0, 200, undefined, false, false, 'title-uploader'),
    titleStore.fetchTitleUploaders(props.titleId),
  ])
  titleUploaderAccounts.value = accounts ?? []
  uploaders.value = currentUploaders
  loading.value = false
}

const grant = async () => {
  if (!selectedAccountId.value) return
  granting.value = true
  const success = await titleStore.grantTitleUploader(props.titleId, selectedAccountId.value)
  granting.value = false
  if (success) {
    notificationStore.showSuccess('Upload access granted.')
    selectedAccountId.value = null
    uploaders.value = await titleStore.fetchTitleUploaders(props.titleId)
  } else {
    errors.value = titleStore.errors
  }
}

const requestRevoke = (account: User) => {
  pendingRevoke.value = account
  showRevokeDialog.value = true
}

const confirmRevoke = async () => {
  if (!pendingRevoke.value) return
  revoking.value = true
  const success = await titleStore.revokeTitleUploader(props.titleId, pendingRevoke.value.id)
  revoking.value = false
  if (success) {
    notificationStore.showSuccess('Upload access revoked.')
    uploaders.value = await titleStore.fetchTitleUploaders(props.titleId)
  } else {
    errors.value = titleStore.errors
  }
  pendingRevoke.value = null
}

const close = () => {
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      selectedAccountId.value = null
      await loadData()
    }
  },
)
</script>
