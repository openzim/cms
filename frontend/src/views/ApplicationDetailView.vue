<template>
  <v-container>
    <div v-if="!dataLoaded && loadingStore.isLoading" class="text-center pa-8">
      <v-progress-circular indeterminate size="64" />
      <div class="mt-4 text-body-large">{{ loadingStore.loadingText }}</div>
    </div>

    <div v-if="dataLoaded">
      <div class="mb-4">
        <h2 class="text-title-large mb-2">{{ name }}</h2>

        <div v-if="application" class="d-flex flex-wrap align-center ga-2">
          <router-link
            :to="{ name: 'title-detail', params: { id: application.title_id } }"
            class="text-decoration-none"
          >
            <v-chip size="small" variant="tonal" color="primary" prepend-icon="mdi-bookshelf">
              {{ application.title_name }}
            </v-chip>
          </router-link>

          <v-chip size="small" variant="tonal" prepend-icon="mdi-tag-outline">
            {{ flavourLabel(application.flavour) }}
          </v-chip>

          <v-chip
            size="small"
            variant="tonal"
            :prepend-icon="store === 'android' ? 'mdi-android' : 'mdi-apple'"
          >
            {{ storeLabel(store) }}
          </v-chip>
        </div>
      </div>

      <v-tabs
        v-model="currentTab"
        class="mb-4"
        color="primary"
        slider-color="primary"
        show-arrows
        :grow="!smAndDown"
      >
        <v-tab
          base-color="primary"
          :value="store"
          :to="{
            name: 'app-detail',
            params: { name, store },
          }"
        >
          <v-icon class="mr-2">{{ store === 'android' ? 'mdi-android' : 'mdi-apple' }}</v-icon>
          {{ storeLabel(store) }}
        </v-tab>

        <v-tab
          v-if="canUpdate"
          base-color="primary"
          value="history"
          :to="{
            name: 'app-detail-tab',
            params: { name, store, selectedTab: 'history' },
          }"
        >
          <v-icon class="mr-2">mdi-history</v-icon>
          History
        </v-tab>

        <v-tab
          v-if="canUpdate"
          base-color="primary"
          value="edit"
          :to="{
            name: 'app-detail-tab',
            params: { name, store, selectedTab: 'edit' },
          }"
        >
          <v-icon class="mr-2">mdi-pencil</v-icon>
          Edit
        </v-tab>

        <v-tab
          v-if="canDelete"
          base-color="primary"
          value="delete"
          :to="{
            name: 'app-detail-tab',
            params: { name, store, selectedTab: 'delete' },
          }"
        >
          <v-icon class="mr-2">mdi-delete</v-icon>
          Delete
        </v-tab>
      </v-tabs>

      <v-window v-model="currentTab">
        <v-window-item :value="store">
          <template v-if="application && application.store === store">
            <div
              v-if="canManagePublishers || canPublish"
              class="d-flex flex-column flex-sm-row justify-end ga-2 mb-4"
            >
              <v-btn
                v-if="canManagePublishers"
                color="primary"
                variant="elevated"
                prepend-icon="mdi-account-key"
                @click="showPublishersDialog = true"
              >
                Manage Publication Access
              </v-btn>

              <v-btn
                v-if="canPublish"
                color="success"
                variant="elevated"
                :prepend-icon="store === 'android' ? 'mdi-android' : 'mdi-apple'"
                :loading="publicationsRef?.publishing"
                :disabled="
                  !application?.enabled ||
                  publicationsRef?.publishing ||
                  publicationsRef?.hasOngoing
                "
                @click="publicationsRef?.publish()"
              >
                Publish to {{ storeLabel(store) }}
              </v-btn>
            </div>

            <ApplicationPublications
              ref="publicationsRef"
              :title-id="application.title_id"
              :flavour="application.flavour"
              :name="application.name"
              :store="store"
              :enabled="application.enabled"
              :can-publish="canPublish"
            />
          </template>
          <v-alert v-else type="info" density="compact" variant="tonal">
            No {{ storeLabel(store) }} application is configured for '{{ name }}'.
          </v-alert>
        </v-window-item>

        <v-window-item value="history">
          <ApplicationHistory
            v-if="canUpdate"
            :history="applicationHistoryStore.history"
            :has-more="canLoadMoreHistory"
            :loading="loadingHistory"
            :paginator="applicationHistoryStore.paginator"
            :name="name"
            :store="store"
            @load="loadHistory"
            @revert="handleRevert"
          />
        </v-window-item>

        <v-window-item value="edit">
          <v-card flat>
            <v-card-text>
              <template v-if="canUpdate && application">
                <v-form ref="formRef" v-model="formValid" @submit.prevent="handleUpdate">
                  <v-text-field
                    v-model="editName"
                    label="Application name"
                    hint="Branded app identifier (e.g. tunisie)"
                    persistent-hint
                    :rules="nameRules"
                    variant="outlined"
                    density="compact"
                    class="mb-4"
                  />

                  <v-switch
                    v-model="editEnabled"
                    :label="editEnabled ? 'Enabled for publication' : 'Disabled for publication'"
                    color="primary"
                    hide-details
                  />

                  <v-alert
                    v-if="saveError"
                    type="error"
                    density="compact"
                    variant="tonal"
                    class="mt-4"
                  >
                    {{ saveError }}
                  </v-alert>

                  <div class="d-flex justify-end mt-4">
                    <v-btn
                      color="primary"
                      variant="elevated"
                      :loading="saving"
                      :disabled="!formValid || saving"
                      @click="handleUpdate"
                    >
                      Save
                    </v-btn>
                  </div>
                </v-form>
              </template>
              <v-alert v-else type="info" density="compact" variant="tonal">
                {{
                  canUpdate
                    ? `No ${storeLabel(store)} application is configured for '${name}'.`
                    : 'You do not have permission to edit this application.'
                }}
              </v-alert>
            </v-card-text>
          </v-card>
        </v-window-item>

        <v-window-item value="delete">
          <v-card flat>
            <v-card-text>
              <template v-if="canDelete && application">
                <v-text-field
                  v-model="deleteConfirmation"
                  :label="`Type '${application.name}' to confirm`"
                  variant="outlined"
                  density="compact"
                  class="mt-4"
                  hide-details
                />

                <div class="d-flex justify-end mt-4">
                  <v-btn
                    color="error"
                    variant="elevated"
                    :disabled="deleteConfirmation !== application.name"
                    @click="deleteOpen = true"
                  >
                    Delete application
                  </v-btn>
                </div>
              </template>
              <v-alert v-else type="info" density="compact" variant="tonal">
                {{
                  canDelete
                    ? `No ${storeLabel(store)} application is configured for '${name}'.`
                    : 'You do not have permission to delete this application.'
                }}
              </v-alert>
            </v-card-text>
          </v-card>
        </v-window-item>
      </v-window>
    </div>

    <PublicationPublishersDialog
      v-if="application"
      v-model="showPublishersDialog"
      :title-id="application.title_id"
    />

    <ConfirmDialog
      v-model="showConfirmDialog"
      title="Confirm Application Update"
      confirm-text="Save Changes"
      cancel-text="Cancel"
      confirm-color="primary"
      icon="mdi-pencil"
      icon-color="primary"
      :max-width="600"
      :loading="saving"
      @confirm="handleConfirmUpdate"
      @cancel="handleCancelUpdate"
    >
      <template #content>
        <div class="mb-4">
          <h3 class="text-title-large mb-2">Changes Summary</h3>
          <p class="text-body-medium text-medium-emphasis mb-3">
            Please review the changes below and optionally add a comment describing what you've
            modified.
          </p>
        </div>

        <div class="mb-4">
          <DiffViewer :differences="enhancedApplicationDifferences" />
        </div>

        <div>
          <v-textarea
            v-model.trim="pendingComment"
            label="Comment (optional)"
            variant="outlined"
            auto-grow
            rows="3"
            persistent-hint
          />
        </div>
      </template>
    </ConfirmDialog>

    <ConfirmDialog
      v-model="deleteOpen"
      title="Delete application"
      confirm-text="Delete"
      confirm-color="error"
      icon="mdi-delete"
      icon-color="error"
      :loading="deleting"
      @confirm="deleteApplication"
      @cancel="deleteOpen = false"
    >
      <template #content>
        <div class="mb-4">You are about to delete this application:</div>
        <div class="d-flex flex-column ga-1">
          <div><strong>Title:</strong> {{ application?.title_name }}</div>
          <div>
            <strong>Flavour:</strong> {{ application ? flavourLabel(application.flavour) : '' }}
          </div>
          <div><strong>Store:</strong> {{ storeLabel(store) }}</div>
          <div><strong>Name:</strong> {{ application?.name }}</div>
        </div>
      </template>
    </ConfirmDialog>
  </v-container>
</template>

<script setup lang="ts">
import ApplicationHistory from '@/components/ApplicationHistory.vue'
import ApplicationPublications from '@/components/ApplicationPublications.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import PublicationPublishersDialog from '@/components/PublicationPublishersDialog.vue'
import { useApplicationStore } from '@/stores/application'
import { useApplicationHistoryStore } from '@/stores/applicationHistory'
import { useAuthStore } from '@/stores/auth'
import { useLoadingStore } from '@/stores/loading'
import { useNotificationStore } from '@/stores/notification'
import type { Application, ApplicationUpdate } from '@/types/application'
import type { PublicationStore } from '@/types/publication'
import type { EnhancedDiff } from '@/utils/diff'
import { flavourLabel, storeLabel } from '@/utils/format'
import { diff } from 'deep-diff'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDisplay } from 'vuetify'

interface Props {
  name: string
  store: PublicationStore
  selectedTab?: string
}

const props = defineProps<Props>()

const { smAndDown } = useDisplay()
const router = useRouter()
const loadingStore = useLoadingStore()
const applicationStore = useApplicationStore()
const applicationHistoryStore = useApplicationHistoryStore()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()

const application = ref<Application | null>(null)
const dataLoaded = ref(false)
const currentTab = ref<string>(props.store)

const canUpdate = computed(() => authStore.hasPermission('application', 'update'))
const canDelete = computed(() => authStore.hasPermission('application', 'delete'))
const canPublish = computed(() => authStore.hasPermission('publication', 'create'))
const canManagePublishers = computed(() => authStore.hasPermission('title', 'update'))
const showPublishersDialog = ref(false)
const publicationsRef = ref<InstanceType<typeof ApplicationPublications> | null>(null)

const formRef = ref()
const formValid = ref(false)
const saving = ref(false)
const saveError = ref('')
const editName = ref('')
const editEnabled = ref(false)
const deleteOpen = ref(false)
const deleting = ref(false)
const deleteConfirmation = ref('')
const loadingHistory = ref(false)
const showConfirmDialog = ref(false)
const pendingComment = ref('')
const pendingUpdatePayload = ref<ApplicationUpdate | null>(null)

const nameRules = [
  (value: unknown) => (typeof value === 'string' && value.trim() !== '') || 'Name is required',
]

const canLoadMoreHistory = computed(() => {
  const { skip, limit, count } = applicationHistoryStore.paginator
  return skip + limit < count
})

const applicationDifferences = computed(() => {
  if (!application.value || !pendingUpdatePayload.value) return undefined

  const currentApplication = JSON.parse(JSON.stringify(application.value))
  const updatedApplication = JSON.parse(
    JSON.stringify({ ...application.value, ...pendingUpdatePayload.value }),
  )
  return diff(currentApplication, updatedApplication)
})

const enhancedApplicationDifferences = computed(() => {
  if (!applicationDifferences.value) return undefined
  return applicationDifferences.value as EnhancedDiff[]
})

const loadHistory = async ({ limit, skip }: { limit: number; skip: number }) => {
  if (skip > 0 && !canLoadMoreHistory.value) return

  loadingHistory.value = true
  try {
    const response = await applicationHistoryStore.fetchHistory(
      props.name,
      props.store,
      limit,
      skip,
    )
    if (!response) {
      notificationStore.showError(`Failed to ${skip > 0 ? 'load more' : 'load'} history items`)
    }
  } finally {
    loadingHistory.value = false
  }
}

const handleRevert = async (reverted: Application | null) => {
  if (reverted && reverted.name !== props.name) {
    await router.replace({
      name: 'app-detail-tab',
      params: {
        name: reverted.name,
        store: reverted.store,
        selectedTab: 'history',
      },
    })
    return
  }
  await loadData(true)
}

const loadData = async (fetchHistory: boolean = false) => {
  dataLoaded.value = false
  loadingStore.startLoading('Fetching application...')
  try {
    application.value = await applicationStore.fetchApplication(props.name, props.store)
    dataLoaded.value = true

    if (fetchHistory) {
      applicationHistoryStore.clearHistory()
      await loadHistory({ limit: applicationHistoryStore.paginator.limit, skip: 0 })
    }
  } finally {
    loadingStore.stopLoading()
  }
}

const resetForm = () => {
  editName.value = application.value?.name ?? ''
  editEnabled.value = application.value?.enabled ?? false
  saveError.value = ''
  showConfirmDialog.value = false
  pendingUpdatePayload.value = null
  pendingComment.value = ''
  formRef.value?.resetValidation()
}

const handleUpdate = () => {
  const currentApplication = application.value
  if (!currentApplication) return

  const newName = editName.value.trim()
  if (!newName) {
    saveError.value = 'Name is required'
    return
  }

  saveError.value = ''
  const updatePayload: ApplicationUpdate = {
    name: newName,
    enabled: editEnabled.value,
  }

  const current = JSON.parse(JSON.stringify(currentApplication))
  const updated = JSON.parse(JSON.stringify({ ...currentApplication, ...updatePayload }))
  const differences = diff(current, updated)

  if (!differences || differences.length === 0) {
    notificationStore.showInfo('No changes detected')
    return
  }

  pendingUpdatePayload.value = updatePayload
  pendingComment.value = ''
  showConfirmDialog.value = true
}

const handleConfirmUpdate = async () => {
  const currentApplication = application.value
  if (!currentApplication || !pendingUpdatePayload.value) return

  saving.value = true
  saveError.value = ''
  try {
    const result = await applicationStore.updateApplication(
      currentApplication.name,
      currentApplication.store,
      {
        ...pendingUpdatePayload.value,
        comment: pendingComment.value || undefined,
      },
    )
    if (!result) {
      saveError.value = applicationStore.errors.join(', ') || 'Failed to save application'
      showConfirmDialog.value = false
      return
    }

    notificationStore.showSuccess('Application saved')
    showConfirmDialog.value = false
    pendingUpdatePayload.value = null
    pendingComment.value = ''

    if (result.name !== props.name) {
      await router.replace({
        name: 'app-detail-tab',
        params: {
          name: result.name,
          store: result.store,
          selectedTab: props.selectedTab ?? 'edit',
        },
      })
    } else {
      await loadData()
    }
  } finally {
    saving.value = false
  }
}

const handleCancelUpdate = () => {
  showConfirmDialog.value = false
  pendingUpdatePayload.value = null
  pendingComment.value = ''
}

const deleteApplication = async () => {
  const currentApplication = application.value
  if (!currentApplication) return

  deleting.value = true
  try {
    const success = await applicationStore.deleteApplication(
      currentApplication.name,
      currentApplication.store,
    )
    if (!success) {
      notificationStore.showErrors(applicationStore.errors)
      return
    }
    notificationStore.showSuccess('Application deleted')
    await router.push({ name: 'apps' })
  } finally {
    deleting.value = false
    deleteOpen.value = false
  }
}

watch(
  () => [props.store, props.selectedTab],
  () => {
    if (props.selectedTab === 'history' && canUpdate.value) {
      currentTab.value = 'history'
    } else if (props.selectedTab === 'edit' && canUpdate.value) {
      currentTab.value = 'edit'
    } else if (props.selectedTab === 'delete' && canDelete.value) {
      currentTab.value = 'delete'
    } else {
      currentTab.value = props.store
    }
  },
  { immediate: true },
)

watch(currentTab, async (tab) => {
  if (tab !== 'delete') {
    deleteConfirmation.value = ''
  }
  if (tab === 'history') {
    await loadData(true)
  }
})

watch(
  application,
  () => {
    deleteConfirmation.value = ''
    resetForm()
  },
  { immediate: true },
)

watch(
  () => [props.name, props.store],
  async () => {
    await loadData(currentTab.value === 'history')
  },
)

onMounted(() => loadData(currentTab.value === 'history'))
</script>
