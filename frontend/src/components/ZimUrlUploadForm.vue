<template>
  <div>
    <v-form ref="formRef" @submit.prevent="handleSubmit">
      <v-text-field
        v-model.trim="url"
        label="ZIM file URL"
        placeholder="https://example.com/file.zim"
        variant="outlined"
        :rules="[rules.required, rules.validUrl]"
        :disabled="state === 'submitting'"
        :error-messages="state === 'error' && errorMessage ? [errorMessage] : []"
        hint="Direct link to a .zim file that Zimfarm can download"
        persistent-hint
        validate-on="submit"
      />

      <div class="d-flex justify-end mt-4">
        <v-btn v-if="state === 'done'" variant="text" color="primary" @click="handleReset">
          <v-icon class="mr-1">mdi-plus</v-icon>
          Upload another
        </v-btn>
        <template v-else>
          <v-btn v-if="state === 'error'" variant="text" class="mr-2" @click="handleReset">
            Cancel
          </v-btn>
          <v-btn
            type="submit"
            variant="elevated"
            color="primary"
            :loading="state === 'submitting'"
            :disabled="!canSubmit"
          >
            <v-icon class="mr-1">mdi-upload</v-icon>
            Upload
          </v-btn>
        </template>
      </div>
    </v-form>

    <v-alert v-if="state === 'done'" type="success" class="mt-3" density="compact">
      URL submitted! Zimfarm is now downloading and processing your ZIM file. It will be imported
      into the CMS shortly. Please, wait for the book to be associated with this title.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useTitleStore } from '@/stores/title'
import { useNotificationStore } from '@/stores/notification'

interface Props {
  titleId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'upload-complete'): void
  (e: 'upload-active', active: boolean): void
}>()

type UrlUploadState = 'idle' | 'submitting' | 'done' | 'error'

const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const formRef = ref()
const url = ref('')
const state = ref<UrlUploadState>('idle')
const errorMessage = ref('')

watch(state, (value) => {
  emit('upload-active', value === 'submitting')
})

function isValidUrl(value: string): boolean {
  try {
    const parsed = new URL(value)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

const rules = {
  required: (value: string) => !!value || 'This field is required',
  validUrl: (value: string) => {
    if (!value) return true
    return isValidUrl(value) || 'Must be a valid http(s) URL'
  },
}

const canSubmit = computed(() => isValidUrl(url.value) && state.value !== 'submitting')

async function handleSubmit() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  state.value = 'submitting'
  errorMessage.value = ''

  try {
    await titleStore.completeZimUploadByUrl(props.titleId, { url: url.value })
    state.value = 'done'
    notificationStore.showSuccess(
      'ZIM file URL submitted successfully! A zimfarm task has been created.',
    )
    emit('upload-complete')
  } catch (err: unknown) {
    const apiErrors = titleStore.errors.length > 0 ? [...titleStore.errors] : []
    const message =
      apiErrors.length > 0
        ? apiErrors.join(', ')
        : err instanceof Error
          ? err.message
          : 'Unknown error'

    console.error('URL upload failed:', err)

    if (apiErrors.length > 0) {
      notificationStore.showErrors(apiErrors)
    } else {
      notificationStore.showError(message)
    }

    errorMessage.value = message
    state.value = 'error'
  }
}

function handleReset() {
  url.value = ''
  errorMessage.value = ''
  state.value = 'idle'
}
</script>
