<template>
  <v-dialog v-if="canShow" v-model="isOpen" max-width="700px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Update Recipe on Zimfarm</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-alert
          v-if="error && !permissionDenied"
          type="error"
          variant="tonal"
          class="mb-4"
          closable
          @click:close="clearError"
        >
          {{ error }}
        </v-alert>

        <div v-if="checkingAuth || loading" class="text-center pa-8">
          <v-progress-circular indeterminate size="48" />
          <div class="mt-3 text-body-2 text-medium-emphasis">
            {{ loadingMessage }}
          </div>
        </div>

        <div v-else-if="needsAuth">
          <p class="text-body-2 mb-3">
            You need to authenticate with the Zimfarm API to update the recipe.
          </p>
          <v-text-field
            v-model="username"
            label="Zimfarm Username"
            variant="outlined"
            density="compact"
            class="mb-2"
            :disabled="authLoading"
          />
          <v-text-field
            v-model="password"
            label="Zimfarm Password"
            type="password"
            variant="outlined"
            density="compact"
            class="mb-3"
            :disabled="authLoading"
            @keyup.enter="authenticate"
          />
        </div>

        <!-- Ready: authenticated, show diffs and field selection -->
        <div v-else>
          <v-alert v-if="permissionDenied" type="warning" variant="tonal" class="mb-4">
            You do not have permission to update recipes on the Zimfarm API.
          </v-alert>

          <template v-if="!permissionDenied">
            <p class="text-body-2 text-medium-emphasis mb-2">
              The following title metadata values differ from the current recipe configuration.
              Select the fields you would like to update on Zimfarm.
            </p>

            <p class="text-body-2 mb-3" v-if="props.recipeLink">
              <a
                :href="props.recipeLink"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary"
              >
                View Recipe on Zimfarm <v-icon size="x-small">mdi-open-in-new</v-icon>
              </a>
            </p>

            <!-- Field selection checkboxes -->
            <div v-if="Object.keys(fieldSelection).length > 0" class="mb-4">
              <v-label class="text-body-2 font-weight-bold mb-2 d-block">Fields to update:</v-label>
              <v-checkbox
                v-for="key in Object.keys(fieldSelection)"
                :key="key"
                v-model="fieldSelection[key]"
                :label="key"
                density="compact"
                hide-details
              />
            </div>

            <DiffViewer v-if="diffs.length" :differences="diffs" class="mb-4" />
            <p v-else class="text-body-2 text-medium-emphasis mb-4">
              No configuration differences detected.
            </p>
          </template>
        </div>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" :disabled="loading || checkingAuth" @click="close"> Skip </v-btn>

        <!-- Auth form actions -->
        <template v-if="needsAuth">
          <v-btn
            color="primary"
            variant="elevated"
            :loading="authLoading"
            :disabled="!username || !password"
            @click="authenticate"
          >
            Authenticate
          </v-btn>
        </template>

        <v-btn v-if="canUpdateRecipe" color="primary" variant="elevated" @click="onConfirm">
          Update Recipe
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Confirmation dialog shown before asking for credentials -->
  <ConfirmDialog
    v-model="showAuthConfirm"
    title="Update Recipe on Zimfarm"
    confirm-text="Proceed"
    cancel-text="Cancel"
    confirm-color="primary"
    icon="mdi-information-outline"
    icon-color="info"
    @confirm="onAuthConfirm"
    @cancel="onAuthCancel"
  >
    <template #content>
      <p class="mb-3">
        The following changes have been detected. Would you like to update the recipe on Zimfarm?
      </p>
      <DiffViewer :differences="allDiffs" />
    </template>
  </ConfirmDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'
import { ZIM_METADATA_TO_CMS_FIELD } from '@/utils/recipe'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import DiffViewer from '@/components/DiffViewer.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import { useZimfarmRecipeStore } from '@/stores/zimfarm/recipe'
import type { BookPromotionAction } from '@/types/book'
import type { User } from '@/types/user'
import type { OfflinerDefinitionFlag, OfflinerDefinitionSpec } from '@/types/zimfarm/offliner'

const props = defineProps<{
  modelValue: boolean
  recipeMetadata: Record<string, string | null>
  actions: BookPromotionAction[]
  actionData: Record<number, Record<string, unknown>>
  defFlag: OfflinerDefinitionFlag
  defSpec: OfflinerDefinitionSpec
  recipeLink: string | null | undefined
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const recipeStore = useZimfarmRecipeStore()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const canShow = ref(false)
const checkingAuth = ref(false)
const loading = ref(false)
const loadingMessage = ref('')
const error = ref<string | null>(null)
const permissionDenied = ref(false)
const needsAuth = ref(false)
const showAuthConfirm = ref(false)
const authLoading = ref(false)
const username = ref('')
const password = ref('')

// Tracks which fields the user wants to update
const fieldSelection = ref<Record<string, boolean>>({})

const allDiffs = computed(() => {
  if (Object.values(props.recipeMetadata).every((v) => v == null)) return []

  const metaAction = props.actions.find((a) => a.kind === 'update_title_metadata')
  if (!metaAction) return []

  const index = props.actions.indexOf(metaAction)
  const newData = props.actionData[index]
  if (!newData) return []

  const oldData: Record<string, unknown> = {}
  const nextData: Record<string, unknown> = {}
  const blobDataKeys = new Set<string>()

  for (const zimMeta of props.defSpec.schema.zimMetadata) {
    const cmsField = ZIM_METADATA_TO_CMS_FIELD[zimMeta.metadata]
    if (!cmsField || newData[cmsField] === undefined) continue

    const flag = props.defFlag.flags.find((f) => f.key === zimMeta.flag)
    if (!flag) continue

    oldData[flag.data_key] = props.recipeMetadata[cmsField] ?? null
    nextData[flag.data_key] = newData[cmsField]

    if (flag.type === 'blob') {
      blobDataKeys.add(flag.data_key)
    }
  }

  const differences = diff(oldData, nextData)
  return (
    ((differences || []) as EnhancedDiff[])
      .filter((d) => d.kind !== undefined)
      // When a recipe flag is not set (null), its value was auto-computed by the
      // scraper. Don't treat that as a difference.
      .filter((d) => !(d.kind === 'E' && d.lhs === null))
      .map((d) => {
        const enhanced: EnhancedDiff = { ...d }
        if (d.path && d.path.length > 0 && blobDataKeys.has(String(d.path[0]))) {
          enhanced.isBlob = true
        }
        return enhanced
      })
  )
})

const diffs = computed(() => {
  return allDiffs.value.filter((d) => {
    if (!d.path || d.path.length === 0) return true
    return fieldSelection.value[String(d.path[0])] !== false
  })
})

const zimfarmUser = ref<User | null>(null)

const hasSelectedFields = computed(() => {
  return Object.values(fieldSelection.value).some((v) => v)
})

const canUpdateRecipe = computed(() => {
  return zimfarmUser.value?.scope?.recipes?.update === true && hasSelectedFields.value
})

watch(isOpen, async (open) => {
  if (open) {
    error.value = null
    permissionDenied.value = false
    needsAuth.value = false
    username.value = ''
    password.value = ''

    const selection: Record<string, boolean> = {}
    for (const d of diffs.value) {
      if (d.path && d.path.length > 0) {
        selection[String(d.path[0])] = true
      }
    }
    fieldSelection.value = selection

    canShow.value = false
    zimfarmUser.value = null
    showAuthConfirm.value = false
    await checkAuthAndPermissions()
  } else {
    canShow.value = false
  }
})

async function checkAuthAndPermissions(showPermissionWarning = false) {
  checkingAuth.value = true
  loadingMessage.value = 'Checking authentication...'
  error.value = null
  permissionDenied.value = false

  try {
    const isLocal = authStore.tokenType == 'local'

    if (isLocal && !authStore.zimfarmProvider?.user) {
      if (allDiffs.value.length > 0) {
        showAuthConfirm.value = true
      } else {
        needsAuth.value = true
        canShow.value = true
      }
      return
    }

    loadingMessage.value = 'Checking permissions...'
    const service = await authStore.getZimfarmApiService('auth')
    const zimfarmUserResult = (await service.get('/me')) as User | null
    zimfarmUser.value = zimfarmUserResult
    if (!zimfarmUserResult?.scope?.recipes?.update) {
      if (showPermissionWarning) {
        permissionDenied.value = true
        canShow.value = true
      } else {
        isOpen.value = false
      }
      return
    }

    canShow.value = true
  } catch (err) {
    console.error('Failed to check recipe update auth', err)
    error.value = 'Failed to verify zimfarm permissions'
    canShow.value = true
  } finally {
    checkingAuth.value = false
  }
}

async function onConfirm() {
  error.value = null
  await updateRecipe()
}

async function authenticate() {
  if (!username.value || !password.value) return

  authLoading.value = true
  error.value = null

  try {
    await authStore.authenticateZimfarm(username.value, password.value)
    if (authStore.zimfarmProvider?.user) {
      needsAuth.value = false
      await checkAuthAndPermissions(true)
    } else {
      error.value = 'Authentication succeeded but user data was not loaded'
    }
  } catch (err) {
    console.error('Zimfarm authentication failed', err)
    error.value = 'Failed to authenticate with Zimfarm'
  } finally {
    authLoading.value = false
  }
}

function buildPayload(blobUrls: Record<string, string>): Record<string, unknown> | null {
  if (Object.values(props.recipeMetadata).every((v) => v == null)) return null

  const metaAction = props.actions.find((a) => a.kind === 'update_title_metadata')
  if (!metaAction) return null

  const index = props.actions.indexOf(metaAction)
  const newData = props.actionData[index]
  if (!newData) return null

  const payload: Record<string, unknown> = {}

  for (const zimMeta of props.defSpec.schema.zimMetadata) {
    const cmsField = ZIM_METADATA_TO_CMS_FIELD[zimMeta.metadata]
    if (!cmsField || newData[cmsField] === undefined) continue

    const flag = props.defFlag.flags.find((f) => f.key === zimMeta.flag)
    if (!flag) continue

    if (!fieldSelection.value[flag.data_key]) continue

    const newValue = newData[cmsField]
    const oldValue = props.recipeMetadata[cmsField]
    if (newValue === oldValue) continue

    // For blob fields, use the uploaded URL instead of the raw base64 value
    payload[flag.data_key] = blobUrls[flag.data_key] ?? newValue
  }

  if (Object.keys(payload).length === 0) return null

  return { flags: { offliner: payload }, comment: 'Update recipe metadata flags from CMS' }
}

async function updateRecipe() {
  const recipe = recipeStore.recipe
  if (!recipe) {
    error.value = 'Recipe data not available'
    return
  }

  loading.value = true
  error.value = null

  try {
    const metaAction = props.actions.find((a) => a.kind === 'update_title_metadata')
    if (!metaAction) {
      error.value = 'No title metadata action found'
      return
    }
    const index = props.actions.indexOf(metaAction)
    const newData = props.actionData[index]
    if (!newData) {
      error.value = 'No action data available'
      return
    }

    // Upload blobs base64 data to zimfarm, and collect the returned URLs.
    const blobUrls: Record<string, string> = {}

    for (const zimMeta of props.defSpec.schema.zimMetadata) {
      const cmsField = ZIM_METADATA_TO_CMS_FIELD[zimMeta.metadata]
      if (!cmsField || newData[cmsField] === undefined) continue

      const flag = props.defFlag.flags.find((f) => f.key === zimMeta.flag)
      if (!flag || flag.type !== 'blob' || !flag.kind) continue

      if (!fieldSelection.value[flag.data_key]) continue

      const newValue = newData[cmsField]
      const oldValue = props.recipeMetadata[cmsField]
      if (newValue === oldValue) continue

      if (typeof newValue !== 'string' || newValue.length === 0) continue

      loadingMessage.value = `Uploading ${flag.data_key}...`

      const blob = await recipeStore.createBlob(recipe.id, {
        flag_name: flag.key,
        kind: flag.kind,
        data: newValue,
        comments: `Update for field ${cmsField}`,
      })

      if (!blob) {
        error.value = recipeStore.errors.join(', ') || `Failed to upload blob for ${flag.data_key}`
        return
      }

      blobUrls[flag.data_key] = blob.url
    }

    loadingMessage.value = 'Building update payload...'
    const payload = buildPayload(blobUrls)
    if (!payload) {
      error.value = 'Failed to build recipe update payload'
      return
    }

    loadingMessage.value = 'Updating recipe...'
    const result = await recipeStore.updateRecipe(recipe.id, payload)
    if (!result) {
      error.value = recipeStore.errors.join(', ') || 'Failed to update recipe'
      return
    }

    notificationStore.showSuccess('Recipe updated successfully')
    isOpen.value = false
  } catch (err) {
    console.error('Failed to update recipe', err)
    error.value = 'An unexpected error occurred while updating recipe'
  } finally {
    loading.value = false
  }
}

function close() {
  isOpen.value = false
}

function onAuthConfirm() {
  showAuthConfirm.value = false
  needsAuth.value = true
  canShow.value = true
}

function onAuthCancel() {
  isOpen.value = false
}

function clearError() {
  error.value = null
}
</script>
