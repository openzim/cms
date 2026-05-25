<!-- Component for comparing book metadata with title metadata and syncing -->

<template>
  <div class="metadata-sync-container">
    <!-- Header Section -->
    <div class="sync-header mb-4">
      <div class="d-flex align-center justify-space-between">
        <div class="d-flex align-center">
          <v-icon size="large" color="primary" class="mr-3">mdi-compare</v-icon>
          <div>
            <p class="text-body-2 text-medium-emphasis mt-1">
              Compare and sync metadata from the book to the associated title
            </p>
          </div>
        </div>
        <v-btn
          v-if="canUpdateTitle && hasMetadataToSync"
          color="primary"
          variant="elevated"
          size="small"
          @click="syncAllMetadata"
          :loading="syncing"
          class="px-6"
        >
          <v-icon class="mr-2">mdi-sync</v-icon>
          Sync All to Title
        </v-btn>
      </div>
    </div>

    <!-- Alerts Section -->
    <v-alert v-if="!title" type="info" density="comfortable" class="mb-4" variant="tonal">
      <template #prepend>
        <v-icon>mdi-information</v-icon>
      </template>
      No title associated with this book.
    </v-alert>

    <v-alert
      v-if="!canUpdateTitle && title"
      type="warning"
      density="comfortable"
      class="mb-4"
      variant="tonal"
    >
      <template #prepend>
        <v-icon>mdi-alert</v-icon>
      </template>
      You don't have permission to update the title metadata.
    </v-alert>

    <v-alert
      v-if="syncSuccess"
      type="success"
      density="comfortable"
      class="mb-4"
      variant="tonal"
      closable
      @click:close="syncSuccess = ''"
    >
      <template #prepend>
        <v-icon>mdi-check-circle</v-icon>
      </template>
      {{ syncSuccess }}
    </v-alert>

    <!-- Metadata Comparison Table -->
    <v-data-table
      v-if="title"
      :headers="headers"
      :items="comparisonItems"
      :mobile="smAndDown"
      :density="smAndDown ? 'compact' : 'comfortable'"
      :item-class="(item: any) => (item.isDifferent ? 'bg-warning-lighten-4' : '')"
      hide-default-footer
      :items-per-page="-1"
    >
      <template #[`item.fieldLabel`]="{ item }">
        <span class="text-no-wrap font-weight-bold">
          <v-icon size="small" class="mr-2">{{ item.icon }}</v-icon>
          {{ item.fieldLabel }}
        </span>
      </template>

      <template #[`item.bookValue`]="{ item }">
        <v-img
          v-if="item.field === 'illustration_48x48_at_1' && item.bookValue"
          :src="getImageDataUrl(item.bookValue)"
          width="48"
          height="48"
          class="rounded my-2"
        />
        <div v-else :class="item.multiline ? 'text-pre-wrap' : ''">
          <span v-if="item.bookValue">{{ item.bookValue }}</span>
          <span v-else class="text-grey-darken-1 font-italic">Not set</span>
        </div>
      </template>

      <template #[`item.titleValue`]="{ item }">
        <v-img
          v-if="item.field === 'illustration_48x48_at_1' && item.titleValue"
          :src="getImageDataUrl(item.titleValue)"
          width="48"
          height="48"
          class="rounded my-2"
        />
        <div v-else :class="item.multiline ? 'text-pre-wrap' : ''">
          <span v-if="item.titleValue">{{ item.titleValue }}</span>
          <span v-else class="text-grey-darken-1 font-italic">Not set</span>
        </div>
      </template>

      <template #[`item.action`]="{ item }">
        <v-btn
          v-if="item.isDifferent && canUpdateTitle"
          size="small"
          variant="tonal"
          color="primary"
          @click="syncField(item.field)"
          :loading="syncing"
        >
          <v-icon size="small" class="mr-1">mdi-arrow-right</v-icon>
          Sync
        </v-btn>
        <v-chip v-else-if="!item.isDifferent" size="small" color="success" variant="flat">
          <v-icon size="small" class="mr-1">mdi-check</v-icon>
          Synced
        </v-chip>
      </template>
    </v-data-table>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useDisplay } from 'vuetify'

import { useTitleStore } from '@/stores/title'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notification'
import type { Book } from '@/types/book'
import type { Title } from '@/types/title'

interface Props {
  book: Book
  title: Title | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  synced: []
}>()

const titleStore = useTitleStore()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()
const { smAndDown } = useDisplay()

const syncing = ref(false)
const syncSuccess = ref('')

const getImageDataUrl = (base64String: string | undefined): string | undefined => {
  if (!base64String) return undefined
  if (base64String.startsWith('data:') || base64String.startsWith('http')) {
    return base64String
  }
  return `data:image/png;base64,${base64String}`
}

// Table headers
const headers = [
  { title: 'Field', key: 'fieldLabel', sortable: false },
  { title: 'Book Metadata', key: 'bookValue', sortable: false },
  { title: 'Title Metadata', key: 'titleValue', sortable: false },
  { title: 'Action', key: 'action', sortable: false, align: 'center' as const },
]

// Extract book metadata for comparison
const bookMetadata = computed(() => {
  const metadata = props.book.zim_metadata || {}
  return {
    title: metadata.Title as string | undefined,
    creator: metadata.Creator as string | undefined,
    publisher: metadata.Publisher as string | undefined,
    description: metadata.Description as string | undefined,
    long_description: metadata.LongDescription as string | undefined,
    language: metadata.Language as string | undefined,
    license: metadata.License as string | undefined,
    illustration_48x48_at_1: metadata['Illustration_48x48@1'] as string | undefined,
  }
})

const canUpdateTitle = computed(() => {
  return (
    authStore.hasPermission('title', 'update') &&
    props.title &&
    !props.title.archived &&
    !props.book.title_archived
  )
})

type MetadataField =
  | 'title'
  | 'creator'
  | 'publisher'
  | 'description'
  | 'long_description'
  | 'language'
  | 'license'
  | 'illustration_48x48_at_1'

const isDifferent = (field: MetadataField): boolean => {
  if (!props.title) return false
  const bookValue = bookMetadata.value[field]
  const titleValue = props.title[field]
  if (bookValue == null && titleValue == null) return false
  if (bookValue == null || titleValue == null) return true
  return bookValue !== titleValue
}

// Comparison items for the data table
const comparisonItems = computed(() => {
  if (!props.title) return []

  const fieldConfigs: Array<{
    field: MetadataField
    fieldLabel: string
    icon: string
    multiline?: boolean
  }> = [
    { field: 'title', fieldLabel: 'Title', icon: 'mdi-format-title' },
    { field: 'creator', fieldLabel: 'Creator', icon: 'mdi-account' },
    { field: 'publisher', fieldLabel: 'Publisher', icon: 'mdi-domain' },
    { field: 'description', fieldLabel: 'Description', icon: 'mdi-text', multiline: true },
    {
      field: 'long_description',
      fieldLabel: 'Long Description',
      icon: 'mdi-text-long',
      multiline: true,
    },
    { field: 'language', fieldLabel: 'Language', icon: 'mdi-translate' },
    { field: 'license', fieldLabel: 'License', icon: 'mdi-license' },
    {
      field: 'illustration_48x48_at_1',
      fieldLabel: 'Illustration',
      icon: 'mdi-image',
    },
  ]

  return fieldConfigs.map((config) => ({
    field: config.field,
    fieldLabel: config.fieldLabel,
    icon: config.icon,
    multiline: config.multiline || false,
    bookValue: bookMetadata.value[config.field],
    titleValue: props.title![config.field],
    isDifferent: isDifferent(config.field),
  }))
})

const hasMetadataToSync = computed(() => {
  if (!props.title) return false
  const fields: MetadataField[] = [
    'title',
    'creator',
    'publisher',
    'description',
    'long_description',
    'language',
    'license',
    'illustration_48x48_at_1',
  ]
  return fields.some((field) => isDifferent(field))
})

const syncField = async (field: MetadataField) => {
  if (!props.title) return

  syncing.value = true
  syncSuccess.value = ''

  try {
    const updatePayload: Partial<Title> = {}

    const bookValue = bookMetadata.value[field]
    if (bookValue !== undefined && bookValue !== null) {
      updatePayload[field] = bookValue
    }

    const updated = await titleStore.updateTitle(props.title.id, updatePayload)
    if (updated) {
      syncSuccess.value = `${field} synced successfully!`
      notificationStore.showSuccess(`${field} synced successfully!`)
      emit('synced')
    } else {
      const errorMsg =
        titleStore.errors.length > 0 ? titleStore.errors.join(', ') : 'Failed to sync field'
      notificationStore.showError(`Failed to sync ${field}: ${errorMsg}`)
    }
  } catch (error) {
    const errorMsg =
      titleStore.errors.length > 0
        ? titleStore.errors.join(', ')
        : error instanceof Error
          ? error.message
          : 'Unknown error occurred'
    notificationStore.showError(`Failed to sync ${field}: ${errorMsg}`)
  } finally {
    syncing.value = false
  }
}

const syncAllMetadata = async () => {
  if (!props.title) return

  syncing.value = true
  syncSuccess.value = ''

  try {
    const updatePayload: Partial<Title> = {}

    const fields: MetadataField[] = [
      'title',
      'creator',
      'publisher',
      'description',
      'long_description',
      'language',
      'license',
      'illustration_48x48_at_1',
    ]

    for (const field of fields) {
      if (isDifferent(field)) {
        const bookValue = bookMetadata.value[field]
        if (bookValue !== undefined && bookValue !== null) {
          updatePayload[field] = bookValue
        }
      }
    }

    if (Object.keys(updatePayload).length === 0) {
      syncSuccess.value = 'No differences to sync'
      notificationStore.showInfo('No differences to sync')
      return
    }

    const updated = await titleStore.updateTitle(props.title.id, updatePayload)
    if (updated) {
      const successMsg = `Successfully synced ${Object.keys(updatePayload).length} field(s) to title!`
      syncSuccess.value = successMsg
      notificationStore.showSuccess(successMsg)
      emit('synced')
    } else {
      const errorMsg =
        titleStore.errors.length > 0 ? titleStore.errors.join(', ') : 'Failed to sync metadata'
      notificationStore.showError(`Failed to sync metadata: ${errorMsg}`)
    }
  } catch (error) {
    const errorMsg =
      titleStore.errors.length > 0
        ? titleStore.errors.join(', ')
        : error instanceof Error
          ? error.message
          : 'Unknown error occurred'
    notificationStore.showError(`Failed to sync metadata: ${errorMsg}`)
  } finally {
    syncing.value = false
  }
}
</script>
