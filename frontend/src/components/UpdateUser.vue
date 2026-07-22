<template>
  <v-card class="mb-4">
    <v-card-text>
      <v-form ref="formRef" @submit.prevent="submitForm">
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="form.display_name"
              label="Display Name"
              hint="User's display name"
              placeholder="Display Name"
              variant="outlined"
              density="compact"
              persistent-hint
              :validate-on="'blur'"
              :rules="[rules.required, rules.minLength(3)]"
            />
          </v-col>

          <v-col cols="12" md="6">
            <v-select
              v-model="form.role"
              :items="roles"
              label="Role"
              variant="outlined"
              density="compact"
            />
          </v-col>

          <v-col cols="12" v-if="form.role === 'collection-editor'">
            <v-autocomplete
              v-model="form.collections"
              :items="collectionNames"
              label="Collections"
              multiple
              chips
              closable-chips
              variant="outlined"
              density="compact"
              hint="Select the collections this user can access"
              persistent-hint
            />
          </v-col>
        </v-row>

        <template v-if="hasLocalAuth">
          <v-divider class="my-4"></v-divider>
          <div class="text-subtitle-1 mb-2 font-weight-bold">Local Authentication</div>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="form.username"
                label="Username"
                hint="Username for local authentication"
                placeholder="username"
                variant="outlined"
                density="compact"
                persistent-hint
                :validate-on="'blur'"
                :rules="props.user.has_password ? [rules.required, rules.minLength(3)] : []"
              />
            </v-col>

            <v-col cols="12" md="6">
              <v-text-field
                v-model="form.password"
                label="New Password"
                hint="Password for local authentication (leave unchanged to keep current, clear to remove)"
                placeholder="Enter new password"
                variant="outlined"
                density="compact"
                persistent-hint
                :validate-on="'blur'"
                :rules="form.password !== PASSWORD_PLACEHOLDER ? [rules.minLength(8)] : []"
                append-inner-icon="mdi-refresh"
                @click:append-inner="generateNewPassword"
              />
            </v-col>
          </v-row>
        </template>

        <template v-if="hasOauth">
          <v-divider class="my-4"></v-divider>
          <div class="text-subtitle-1 mb-2 font-weight-bold">External Identity Provider</div>
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field
                v-model="form.idp_sub"
                label="IDP Sub (UUID)"
                hint="Identifier issued by external identity provider."
                placeholder="00000000-0000-0000-0000-000000000000"
                variant="outlined"
                density="compact"
                persistent-hint
                :validate-on="'blur'"
              />
            </v-col>
          </v-row>
        </template>

        <v-row class="mt-4">
          <v-col cols="12">
            <v-btn type="submit" color="primary" variant="elevated" :disabled="!hasChanges" block>
              Update User Profile
            </v-btn>
          </v-col>
        </v-row>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'

import type { Config } from '@/config'
import constants from '@/constants'
import { generatePassword } from '@/utils/browsers'
import type { User } from '@/types/user'

// Props
interface Props {
  user: User
  collectionNames: string[]
  initialCollections?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  initialCollections: () => [],
})

const emit = defineEmits<{
  (
    e: 'submit',
    payload: {
      userPayload: {
        username?: string | null
        display_name?: string
        role?: (typeof constants.ROLES)[number]
        scope?: Record<string, Record<string, boolean>>
        idp_sub?: string | null
        collections?: string[] | null
      } | null
      password?: string | null
    },
  ): void
}>()

const roles = constants.ROLES
const config = inject<Config>(constants.config)

const hasLocalAuth = computed(
  () => config?.LOGIN_MODES.includes('local') || !!props.user.username || props.user.has_password,
)

const hasOauth = computed(() => config?.LOGIN_MODES.includes('oauth') || !!props.user.idp_sub)

const PASSWORD_PLACEHOLDER = '******'

// Form validation rules
const rules = {
  required: (value: string) => !!value || 'This field is required',
  minLength: (min: number) => (value: string) =>
    !value || value.length >= min || `This field must be at least ${min} characters long`,
}

// Reactive data
const form = ref({
  username: '',
  display_name: '',
  role: '' as (typeof constants.ROLES)[number],
  password: '',
  idp_sub: '',
  collections: [] as string[],
})

const passwordChanged = computed(() => {
  return form.value.password !== (props.user.has_password ? PASSWORD_PLACEHOLDER : '')
})

const payload = computed(() => {
  const result: {
    username?: string | null
    display_name?: string
    role?: (typeof constants.ROLES)[number]
    scope?: Record<string, Record<string, boolean>>
    idp_sub?: string | null
    collections?: string[] | null
  } = {}

  // Only include username if it has changed
  if (form.value.username !== (props.user.username || '')) {
    result.username = form.value.username.trim() ? form.value.username.trim() : null
  }

  if (form.value.display_name !== props.user.display_name) {
    result.display_name = form.value.display_name
  }

  if (form.value.role !== props.user.role) {
    result.role = form.value.role
  }

  // Only include idp_sub if it has changed
  if (form.value.idp_sub !== (props.user.idp_sub || '')) {
    result.idp_sub = form.value.idp_sub.trim() ? form.value.idp_sub : null
  }

  // Include collections if role is collection-editor and they differ from initial,
  // or if the role has just been changed to collection-editor
  if (form.value.role === 'collection-editor') {
    const roleChanged = form.value.role !== props.user.role
    const initial = props.initialCollections
    const current = form.value.collections
    const collectionsChanged =
      initial.length !== current.length || !initial.every((c) => current.includes(c))
    if (roleChanged || collectionsChanged) {
      result.collections = current
    }
  } else if (form.value.role !== props.user.role && props.user.role === 'collection-editor') {
    result.collections = null
  }

  // If we're sending collections, always include the role
  if ('collections' in result) {
    result.role = form.value.role
  }

  if (Object.keys(result).length === 0) {
    return null
  }

  return result
})

const generateNewPassword = () => {
  form.value.password = generatePassword(8)
}

// Form ref for validation
const formRef = ref()

// Methods
const hasChanges = computed(() => {
  return payload.value !== null || passwordChanged.value
})

const submitForm = async () => {
  const { valid } = await formRef.value?.validate()
  if (!valid) return

  emit('submit', {
    userPayload: payload.value,
    password: passwordChanged.value
      ? form.value.password.trim()
        ? form.value.password.trim()
        : null
      : undefined,
  })
}

const initializeForm = () => {
  if (!props.user) return

  const role = constants.ROLES.includes(props.user.role as (typeof constants.ROLES)[number])
    ? (props.user.role as (typeof constants.ROLES)[number])
    : 'global-editor'

  form.value = {
    username: props.user.username || '',
    display_name: props.user.display_name || '',
    role,
    password: props.user.has_password ? PASSWORD_PLACEHOLDER : '',
    idp_sub: props.user.idp_sub || '',
    collections: role === 'collection-editor' ? [...props.initialCollections] : [],
  }
}

// Watch for user changes to reinitialize form
watch(
  () => props.user,
  () => {
    initializeForm()
  },
  { deep: true },
)

watch(
  () => form.value.role,
  (newRole) => {
    if (newRole !== 'collection-editor') {
      form.value.collections = []
    }
  },
)

watch(
  () => props.initialCollections,
  (newCollections) => {
    if (form.value.role === 'collection-editor') {
      form.value.collections = [...newCollections]
    }
  },
)

onMounted(() => {
  initializeForm()
})
</script>
