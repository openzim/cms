<template>
  <v-dialog :model-value="modelValue" max-width="600" @update:model-value="close">
    <v-card>
      <v-card-title class="text-title-large bg-primary">
        <v-icon class="mr-2">mdi-account-key</v-icon>
        Build Access
      </v-card-title>

      <v-card-text class="pt-4">
        <v-alert v-if="errors.length" type="error" variant="tonal" class="mb-4" density="compact">
          {{ errors.join(', ') }}
        </v-alert>

        <div class="text-title-small mb-2">Users with build access</div>
        <div v-if="builders.length === 0" class="text-body-medium text-medium-emphasis mb-4">
          No user has build access to this title yet. Only admins and global editors can build its
          applications.
        </div>
        <v-list v-else density="compact" class="mb-4">
          <v-list-item v-for="builder in builders" :key="builder.id">
            <v-list-item-title>{{ builder.display_name }}</v-list-item-title>
            <template #append>
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="requestRevoke(builder)"
              />
            </template>
          </v-list-item>
        </v-list>

        <div class="text-title-small mb-2">Grant access to a collection editor</div>
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
          no-data-text="No collection-editor account available"
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
    title="Revoke Build Access"
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
const notificationStore = useNotificationStore()

const errors = ref<string[]>([])
const loading = ref(false)
const granting = ref(false)
const revoking = ref(false)
const showRevokeDialog = ref(false)
const pendingRevoke = ref<User | null>(null)
const selectedAccountId = ref<string | null>(null)
const builders = ref<User[]>([])
const collectionEditorAccounts = ref<User[]>([])

const availableAccounts = computed(() =>
  collectionEditorAccounts.value.filter(
    (account) => !builders.value.some((builder) => builder.id === account.id),
  ),
)

const revokeMessage = computed(() =>
  pendingRevoke.value ? `Revoke build access for "${pendingRevoke.value.display_name}"?` : '',
)

const loadData = async () => {
  loading.value = true
  errors.value = []
  const [accounts, currentBuilders] = await Promise.all([
    titleStore.fetchAvailableAppBuilders(props.titleId),
    titleStore.fetchAppBuilders(props.titleId),
  ])
  collectionEditorAccounts.value = accounts ?? []
  builders.value = currentBuilders
  loading.value = false
}

const grant = async () => {
  if (!selectedAccountId.value) return
  granting.value = true
  const success = await titleStore.grantAppBuilder(props.titleId, selectedAccountId.value)
  granting.value = false
  if (success) {
    notificationStore.showSuccess('Build access granted.')
    selectedAccountId.value = null
    builders.value = await titleStore.fetchAppBuilders(props.titleId)
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
  const success = await titleStore.revokeAppBuilder(props.titleId, pendingRevoke.value.id)
  revoking.value = false
  if (success) {
    notificationStore.showSuccess('Build access revoked.')
    builders.value = await titleStore.fetchAppBuilders(props.titleId)
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
