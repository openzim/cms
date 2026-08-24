<template>
  <v-dialog v-model="isOpen" max-width="800px" persistent scrollable>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Promote Book</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <div v-if="loadingDryRun" class="text-center pa-8">
          <v-progress-circular indeterminate size="48" />
          <div class="mt-3 text-body-2 text-medium-emphasis">
            Analyzing book promotion requirements...
          </div>
        </div>

        <v-alert v-else-if="dryRunError" type="error" variant="tonal" class="mb-4">
          {{ dryRunError }}
        </v-alert>

        <v-alert
          v-else-if="actions.length === 0"
          type="success"
          variant="tonal"
          icon="mdi-check-circle"
        >
          No actions are needed to promote this book. It can be moved directly to prod.
        </v-alert>

        <div v-else>
          <p class="text-body-2 text-medium-emphasis mb-4">
            The following actions are needed to promote this book. Required actions are always
            performed. You may uncheck optional actions to skip them.
          </p>

          <v-expansion-panels variant="accordion" multiple>
            <v-expansion-panel
              v-for="(action, index) in actions"
              :key="index"
              :value="index"
              :class="action.requirement !== 'information' ? 'border-warning' : ''"
            >
              <template #title>
                <div class="d-flex align-center ga-2 flex-grow-1">
                  <v-checkbox
                    v-if="action.requirement !== 'information'"
                    :model-value="action.requirement === 'mandatory' || actionChecked[index]"
                    :disabled="action.requirement !== 'optional'"
                    color="warning"
                    density="compact"
                    hide-details
                    class="flex-grow-0"
                    @click.stop="toggleAction(index)"
                    @update:model-value="
                      (v) => {
                        if (action.requirement === 'optional' && v !== null)
                          actionChecked[index] = v
                      }
                    "
                  />
                  <v-icon
                    :color="action.requirement !== 'information' ? 'warning' : 'info'"
                    size="small"
                    class="flex-grow-0"
                  >
                    {{
                      action.requirement !== 'information' ? 'mdi-alert-circle' : 'mdi-information'
                    }}
                  </v-icon>
                  <span class="text-body-2 text-capitalize flex-grow-0">
                    {{ formatActionKind(action.kind) }}
                  </span>
                  <v-chip
                    size="x-small"
                    class="ml-2 flex-grow-0 text-capitalize"
                    :color="action.requirement !== 'information' ? 'warning' : 'info'"
                    variant="flat"
                  >
                    {{ action.requirement }}
                  </v-chip>
                </div>
              </template>

              <template #text>
                <div class="pb-2">
                  <v-alert
                    :type="action.requirement !== 'information' ? 'warning' : 'info'"
                    variant="tonal"
                    density="compact"
                    class="mb-4"
                  >
                    {{ action.message }}
                  </v-alert>

                  <div v-if="actionChecked[index] || action.requirement === 'mandatory'">
                    <!-- create_title: reuse TitleForm -->
                    <template v-if="action.kind === 'create_title'">
                      <TitleForm
                        :ref="
                          (el) =>
                            setTitleFormRef(index, el as InstanceType<typeof TitleForm> | null)
                        "
                        :title="getSyntheticTitle(index)"
                        :in-dialog="true"
                        :collections="collections"
                      />
                      <div v-if="actionData[index].flavours?.length">
                        <v-divider class="my-4" />
                        <h3 class="text-h6 mb-3">Flavours</h3>
                        <div
                          v-for="(tf, idx) in actionData[index].flavours"
                          :key="idx"
                          class="mb-2"
                        >
                          <div class="d-flex align-center ga-2">
                            <v-chip size="small" label color="primary" variant="tonal">
                              {{ tf.flavour }}
                            </v-chip>
                          </div>
                          <a
                            v-if="tf.recipe_link"
                            :href="tf.recipe_link"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-primary text-decoration-none text-body-2 ml-2 mt-1 d-inline-block"
                          >
                            <v-icon size="x-small" class="mr-1">mdi-open-in-new</v-icon>
                            View recipe on Zimfarm
                          </a>
                        </div>
                      </div>
                    </template>

                    <!-- update_title_metadata -->
                    <template v-else-if="action.kind === 'update_title_metadata'">
                      <div class="d-flex align-center justify-space-between mb-4">
                        <div class="d-flex align-center ga-2">
                          <v-progress-circular
                            v-if="loadingRecipeMetadata"
                            indeterminate
                            size="16"
                            width="2"
                            class="mr-2"
                          />
                        </div>
                        <div class="d-flex align-center ga-2">
                          <v-btn
                            v-if="existingTitle && hasAnyFieldDifferentFromTitle(index)"
                            color="primary"
                            variant="elevated"
                            size="small"
                            prepend-icon="mdi-download"
                            @click="useAllTitleValues(index)"
                          >
                            Use All from Title
                          </v-btn>
                        </div>
                      </div>
                      <v-row v-if="actionData[index]?.title !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'title')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.title"
                            @use="useTitleValue(index, 'title')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].title"
                              @update:model-value="actionData[index].title = $event"
                              label="Title"
                              :max-graphemes="titleMaxLength"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.creator !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'creator')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.creator"
                            @use="useTitleValue(index, 'creator')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].creator"
                              @update:model-value="actionData[index].creator = $event"
                              label="Creator"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.publisher !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'publisher')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.publisher"
                            @use="useTitleValue(index, 'publisher')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].publisher"
                              @update:model-value="actionData[index].publisher = $event"
                              label="Publisher"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.license !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'license')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.license"
                            @use="useTitleValue(index, 'license')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].license"
                              @update:model-value="actionData[index].license = $event"
                              label="License"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.language !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'language')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.language"
                            @use="useTitleValue(index, 'language')"
                          >
                            <TitleLanguageField
                              :model-value="actionData[index].language"
                              @update:model-value="actionData[index].language = $event"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.illustration_48x48_at_1 !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'illustration_48x48_at_1')"
                            diff-label="Different from title which has:"
                            @use="useTitleValue(index, 'illustration_48x48_at_1')"
                          >
                            <TitleIllustrationField
                              :model-value="actionData[index].illustration_48x48_at_1"
                              @update:model-value="
                                actionData[index].illustration_48x48_at_1 = $event
                              "
                            />
                            <template #diff-content>
                              <div class="d-flex flex-column flex-grow-1">
                                <template v-if="existingTitle?.illustration_48x48_at_1">
                                  <v-img
                                    :src="getImageDataUrl(existingTitle.illustration_48x48_at_1)"
                                    width="48"
                                    height="48"
                                    class="rounded border w-100"
                                  />
                                </template>
                                <strong v-else>(no value)</strong>
                              </div>
                            </template>
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.description !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'description')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.description"
                            @use="useTitleValue(index, 'description')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].description"
                              @update:model-value="actionData[index].description = $event"
                              label="Description"
                              textarea
                              :max-graphemes="descriptionMaxLength"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.long_description !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'long_description')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.long_description"
                            @use="useTitleValue(index, 'long_description')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].long_description"
                              @update:model-value="actionData[index].long_description = $event"
                              label="Long Description"
                              textarea
                              :rows="5"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.relation !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'relation')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.relation"
                            @use="useTitleValue(index, 'relation')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].relation"
                              @update:model-value="actionData[index].relation = $event"
                              label="Relation"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                      <v-row v-if="actionData[index]?.source !== undefined">
                        <v-col cols="12">
                          <MetadataFieldWithDiff
                            :show-diff="isFieldDifferentFromTitle(index, 'source')"
                            diff-label="Different from title which has:"
                            :diff-value="existingTitle?.source"
                            @use="useTitleValue(index, 'source')"
                          >
                            <TitleTextField
                              :model-value="actionData[index].source"
                              @update:model-value="actionData[index].source = $event"
                              label="Source"
                            />
                          </MetadataFieldWithDiff>
                        </v-col>
                      </v-row>
                    </template>

                    <!-- update_title_maturity -->
                    <template v-else-if="action.kind === 'update_title_maturity'">
                      <TitleMaturityField
                        :model-value="actionData[index].maturity"
                        @update:model-value="actionData[index].maturity = $event"
                      />
                    </template>

                    <!-- set_title_collections -->
                    <template v-else-if="action.kind === 'set_title_collections'">
                      <TitleCollectionsField
                        :model-value="actionData[index].collection_titles || []"
                        @update:model-value="actionData[index].collection_titles = $event"
                        :collections="collections"
                      />
                    </template>

                    <!-- restore_title: read-only -->
                    <template v-else-if="action.kind === 'restore_title'">
                      <div class="text-body-2">
                        <strong>Titles to restore:</strong>
                        <v-chip
                          v-for="(name, tIdx) in actionData[index].title_names || []"
                          :key="tIdx"
                          size="small"
                          class="ml-1"
                          label
                        >
                          {{ name }}
                        </v-chip>
                      </div>
                    </template>

                    <!-- create_title_flavour -->
                    <template v-else-if="action.kind === 'create_title_flavour'">
                      <div class="text-body-2">
                        <strong>Flavour to add:</strong>
                        <v-chip size="small" class="ml-1" label color="primary" variant="tonal">
                          {{ actionData[index].flavour }}
                        </v-chip>
                      </div>
                      <div v-if="actionData[index].recipe_link" class="text-body-2 mt-2">
                        <a
                          :href="actionData[index].recipe_link"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="text-primary"
                        >
                          <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
                          View recipe on Zimfarm
                        </a>
                      </div>
                    </template>

                    <template v-else-if="action.kind === 'update_flavour_recipe'">
                      <div v-if="actionData[index].recipe_link" class="text-body-2">
                        <a
                          :href="actionData[index].recipe_link"
                          target="_blank"
                          rel="noopener noreferrer"
                          class="text-primary"
                        >
                          <v-icon size="small" class="mr-1">mdi-open-in-new</v-icon>
                          View new recipe on Zimfarm
                        </a>
                      </div>
                    </template>
                  </div>

                  <v-alert
                    v-else-if="action.requirement === 'optional'"
                    type="warning"
                    variant="tonal"
                    density="compact"
                    icon="mdi-alert-circle"
                  >
                    This optional action will be skipped.
                  </v-alert>
                </div>
              </template>
            </v-expansion-panel>
          </v-expansion-panels>

          <v-alert v-if="submitError" type="error" variant="tonal" class="mt-4" closable>
            {{ submitError }}
          </v-alert>
        </div>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="submitting">Cancel</v-btn>
        <v-btn
          v-if="!loadingDryRun && !dryRunError"
          color="primary"
          variant="elevated"
          @click="actions.length > 0 ? handleSubmit() : executePromote()"
          :loading="submitting"
          :disabled="submitting || (actions.length > 0 && !hasAnyActionChecked)"
        >
          Promote Book
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <ConfirmDialog
    v-model="showConfirmDialog"
    title="Promote Book"
    confirm-text="Proceed"
    confirm-color="primary"
    icon="mdi-alert-circle"
    icon-color="warning"
    :loading="submitting"
    @confirm="executePromote"
  >
    <template #content>
      <p class="mb-3">
        Are you sure you want to promote this book? The following actions will be performed so that
        book can be moved to prod:
      </p>
      <div v-for="(action, i) in selectedActionsForConfirm" :key="i" class="mb-4">
        <div class="d-flex align-center ga-2 mb-2">
          <v-icon :color="action.requirement !== 'information' ? 'warning' : 'info'" size="small">
            {{ action.requirement !== 'information' ? 'mdi-alert-circle' : 'mdi-check-circle' }}
          </v-icon>
          <span class="text-body-2 text-capitalize">{{ action.kind }}</span>
          <v-chip
            size="x-small"
            :color="action.requirement !== 'information' ? 'warning' : 'info'"
            variant="flat"
            class="text-capitalize"
          >
            {{ action.requirement }}
          </v-chip>
        </div>
        <DiffViewer
          v-if="isDiffableAction(action.actionKind) && titleDiffs[action.index]?.length"
          :differences="titleDiffs[action.index]"
        />
        <div
          v-else-if="isDiffableAction(action.actionKind) && !titleDiffs[action.index]"
          class="text-body-2 text-medium-emphasis ml-8"
        >
          No changes to display.
        </div>
      </div>
    </template>
  </ConfirmDialog>

  <RecipeUpdateDialog
    v-if="recipeOfflinerDefFlag && recipeOfflinerDefSpec"
    v-model="showRecipeUpdateDialog"
    :recipe-metadata="recipeMetadata"
    :actions="actions"
    :action-data="actionData"
    :def-flag="recipeOfflinerDefFlag"
    :def-spec="recipeOfflinerDefSpec"
    :recipe-link="props.book?.recipe_link"
  />
</template>

<script setup lang="ts">
import TitleTextField from '@/components/TitleTextField.vue'
import TitleLanguageField from '@/components/TitleLanguageField.vue'
import TitleIllustrationField from '@/components/TitleIllustrationField.vue'
import TitleCollectionsField from '@/components/TitleCollectionsField.vue'
import TitleMaturityField from '@/components/TitleMaturityField.vue'
import TitleForm from '@/components/TitleForm.vue'
import MetadataFieldWithDiff from '@/components/MetadataFieldWithDiff.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useBookStore } from '@/stores/book'
import { useTitleStore } from '@/stores/title'
import { useNotificationStore } from '@/stores/notification'
import { useZimfarmRecipeStore } from '@/stores/zimfarm/recipe'
import { useZimfarmOfflinerStore } from '@/stores/zimfarm/offliner'
import constants, { TITLE_METADATA_FIELDS, type TitleMetadataFieldKey } from '@/constants'
import type { Config } from '@/config'
import type { Book, BookPromotionAction } from '@/types/book'
import type { CollectionLight } from '@/types/collections'
import type { Title } from '@/types/title'
import type { OfflinerDefinitionFlag, OfflinerDefinitionSpec } from '@/types/zimfarm/offliner'
import { diff } from 'deep-diff'
import type { EnhancedDiff } from '@/utils/diff'
import { getImageDataUrl } from '@/utils/image'
import { extractRecipeMetadataValues } from '@/utils/recipe'
import httpRequest from '@/utils/httpRequest'
import DiffViewer from '@/components/DiffViewer.vue'
import RecipeUpdateDialog from '@/components/RecipeUpdateDialog.vue'
import { computed, inject, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
  book: Book | null
  collections: CollectionLight[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  promoted: []
}>()

const config = inject<Config>(constants.config)!
const bookStore = useBookStore()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()
const recipeStore = useZimfarmRecipeStore()
const offlinerStore = useZimfarmOfflinerStore()

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const titleMaxLength = config.ZIM_TITLE_MAX_LENGTH ?? 30
const descriptionMaxLength = config.ZIM_DESCRIPTION_MAX_LENGTH ?? 80

// State
const loadingDryRun = ref(false)
const dryRunError = ref<string | null>(null)
const actions = ref<BookPromotionAction[]>([])
const actionChecked = ref<Record<number, boolean>>({})
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const actionData = ref<Record<number, Record<string, any>>>({})
const existingTitle = ref<Title | null>(null)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const showConfirmDialog = ref(false)
const loadingRecipeMetadata = ref(false)

/** Resolved recipe metadata values keyed by CMS field name. */
const recipeMetadata = ref<Record<string, string | null>>({})
const recipeOfflinerDefFlag = ref<OfflinerDefinitionFlag | null>(null)
const recipeOfflinerDefSpec = ref<OfflinerDefinitionSpec | null>(null)
const showRecipeUpdateDialog = ref(false)

const hasRecipeMetadataDifferences = computed(() => {
  if (Object.values(recipeMetadata.value).every((v) => v == null)) return false

  const metaAction = actions.value.find((a) => a.kind === 'update_title_metadata')
  if (!metaAction) return false

  const index = actions.value.indexOf(metaAction)
  const newData = actionData.value[index]
  if (!newData) return false

  for (const field of TITLE_METADATA_FIELDS) {
    if (newData[field] === undefined) continue

    // A null recipe value means the scraper auto-computes this flag, so it is
    // not a real difference
    const oldValue = recipeMetadata.value[field] ?? null
    if (oldValue === null) continue

    if (newData[field] !== oldValue) return true
  }
  return false
})

const hasAnyActionChecked = computed(() => {
  // Allow promoting when all actions are purely informational
  if (actions.value.length > 0 && actions.value.every((a) => a.requirement === 'information'))
    return true
  return actions.value.some(
    (action, index) => action.requirement === 'mandatory' || actionChecked.value[index],
  )
})

const selectedActionsForConfirm = computed(() => {
  return actions.value
    .filter(
      (action, index) =>
        action.requirement === 'mandatory' ||
        action.requirement === 'information' ||
        actionChecked.value[index],
    )
    .map((action) => {
      const index = actions.value.indexOf(action)
      return {
        kind: formatActionKind(action.kind),
        actionKind: action.kind,
        requirement: action.requirement,
        index,
      }
    })
})

const titleDiffs = computed(() => {
  if (!existingTitle.value) return {} as Record<number, EnhancedDiff[]>

  const diffs: Record<number, EnhancedDiff[]> = {}

  actions.value.forEach((action, index) => {
    const data = actionData.value[index]
    if (!data) return

    let current: Record<string, unknown>
    let next: Record<string, unknown>

    switch (action.kind) {
      case 'update_title_metadata': {
        current = {}
        next = {}
        for (const key of Object.keys(data)) {
          current[key] = existingTitle.value![key as keyof Title] ?? null
          next[key] = data[key] ?? null
        }
        break
      }
      case 'update_title_maturity': {
        current = { maturity: existingTitle.value!.maturity }
        next = { maturity: data.maturity }
        break
      }
      case 'set_title_collections': {
        current = {
          collections: existingTitle.value!.collections.map((c) => ({
            collection_name: c.collection_name,
            path: c.path,
          })),
        }
        next = { collections: data.collection_titles ?? [] }
        break
      }
      case 'restore_title': {
        current = { archived: existingTitle.value!.archived }
        next = { archived: false }
        break
      }
      case 'create_title_flavour': {
        const existingFlavours = existingTitle.value!.flavours.map((f) => f.flavour)
        const newFlavour = data.flavour as string
        current = { flavours: existingFlavours }
        next = { flavours: [...existingFlavours, newFlavour] }
        break
      }
      case 'update_flavour_recipe': {
        const existingFlavour = existingTitle.value!.flavours.find(
          (f) => f.flavour === props.book?.flavour,
        )
        current = { recipe_id: existingFlavour?.recipe_id ?? null }
        next = { recipe_id: data.recipe_id }
        break
      }
      default:
        return
    }

    const differences = diff(current, next)
    if (differences) {
      diffs[index] = differences.map((d) => {
        const enhanced: EnhancedDiff = { ...d }
        if (d.path?.includes('illustration_48x48_at_1')) {
          enhanced.isBlob = true
        }
        return enhanced
      }) as EnhancedDiff[]
    }
  })

  return diffs
})

const DIFFABLE_ACTION_KINDS = [
  'update_title_metadata',
  'update_title_maturity',
  'set_title_collections',
  'restore_title',
  'create_title_flavour',
  'update_flavour_recipe',
] as const

function isDiffableAction(kind: string): boolean {
  return (DIFFABLE_ACTION_KINDS as readonly string[]).includes(kind)
}

// TitleForm refs for create_title actions
const titleFormRefs = ref<Record<number, InstanceType<typeof TitleForm> | null>>({})

function setTitleFormRef(index: number, el: InstanceType<typeof TitleForm> | null) {
  titleFormRefs.value[index] = el
}

function getSyntheticTitle(index: number): Title {
  const data = actionData.value[index] || {}

  return {
    id: '',
    name: data.name || '',
    maturity: data.maturity || 'stable',
    archived: false,
    title: data.title || null,
    creator: data.creator || null,
    publisher: data.publisher || null,
    description: data.description || null,
    language: data.language || null,
    illustration_48x48_at_1: data.illustration_48x48_at_1 || null,
    long_description: null,
    license: null,
    relation: null,
    source: null,
    flavours: [],
    events: [],
    books: [],
    collections: [],
  }
}

function formatActionKind(kind: string): string {
  return kind.replace(/_/g, ' ')
}

function toggleAction(index: number) {
  if (actions.value[index].requirement !== 'optional') return
  actionChecked.value[index] = !actionChecked.value[index]
}

// Fields that can be compared between the action data and the existing title
type TitleMetadataFields = Record<TitleMetadataFieldKey, string | undefined>

function isFieldDifferentFromTitle(index: number, field: keyof TitleMetadataFields): boolean {
  if (!existingTitle.value) return false
  const titleValue = existingTitle.value[field]
  const actionValue = actionData.value[index]?.[field]
  if (titleValue === undefined) return false
  return titleValue !== actionValue
}

function useTitleValue(index: number, field: keyof TitleMetadataFields): void {
  if (!existingTitle.value) return
  const value = existingTitle.value[field]
  if (value !== undefined) {
    actionData.value[index][field] = value
  }
}

const hasAnyFieldDifferentFromTitle = (index: number): boolean => {
  if (!existingTitle.value) return false
  return TITLE_METADATA_FIELDS.some(
    (field) =>
      actionData.value[index]?.[field] !== undefined && isFieldDifferentFromTitle(index, field),
  )
}

function useAllTitleValues(index: number): void {
  TITLE_METADATA_FIELDS.forEach((field) => {
    if (actionData.value[index]?.[field] !== undefined && isFieldDifferentFromTitle(index, field)) {
      useTitleValue(index, field)
    }
  })
}

async function loadRecipeMetadata(recipeId: string) {
  const recipe = await recipeStore.fetchRecipe(recipeId)
  if (!recipe) {
    console.warn('Failed to fetch recipe:', recipeId)
    return
  }

  const [defFlag, defSpec] = await Promise.all([
    offlinerStore.fetchOfflinerDefinitionFlag(recipe.offliner, recipe.version),
    offlinerStore.fetchOfflinerDefinitionSpec(recipe.offliner, recipe.version),
  ])

  if (!defFlag || !defSpec) {
    console.warn('Failed to fetch offliner definitions for', recipe.offliner, recipe.version)
    return
  }

  recipeMetadata.value = extractRecipeMetadataValues(defFlag, defSpec, recipe.config.offliner)
  recipeOfflinerDefFlag.value = defFlag
  recipeOfflinerDefSpec.value = defSpec

  // If the illustration is a URL, fetch it upfront and convert to base64. This is
  // because zimfarm API accepts blobs as bas64 strings and our blob diff viewer
  // also uses base64 strings when showing comparison
  const illustrationValue = recipeMetadata.value['illustration_48x48_at_1']
  if (illustrationValue && illustrationValue.startsWith('http')) {
    try {
      const service = httpRequest({})
      const blob = await service.get<unknown, Blob>(illustrationValue, {
        responseType: 'blob',
      })
      if (blob) {
        const dataUrl: string = await new Promise((resolve, reject) => {
          const reader = new FileReader()
          reader.onloadend = () => resolve(reader.result as string)
          reader.onerror = () => reject(reader.error)
          reader.readAsDataURL(blob)
        })
        recipeMetadata.value['illustration_48x48_at_1'] = dataUrl.includes(',')
          ? dataUrl.split(',')[1]
          : dataUrl
      } else {
        recipeMetadata.value['illustration_48x48_at_1'] = null
        notificationStore.showError('Failed to fetch recipe illustration')
      }
    } catch {
      recipeMetadata.value['illustration_48x48_at_1'] = null
      notificationStore.showError('Failed to fetch recipe illustration')
    }
  }
}

watch(isOpen, async (newValue) => {
  if (newValue && props.book) await loadDryRun()
})

async function loadDryRun() {
  if (!props.book) return

  loadingDryRun.value = true
  dryRunError.value = null
  existingTitle.value = null
  actions.value = []
  actionChecked.value = {}
  actionData.value = {}
  recipeMetadata.value = {}

  if (props.book.title_id) {
    existingTitle.value = await titleStore.fetchTitleById(props.book.title_id)
  }

  try {
    const result = await bookStore.promoteBook(props.book.id, true)
    if (!result) {
      dryRunError.value = bookStore.errors.join(', ') || 'Failed to analyze promotion requirements'
      return
    }

    actions.value = result.actions
    actions.value.forEach((action, index) => {
      actionData.value[index] = JSON.parse(JSON.stringify(action.data))
      actionChecked.value[index] = action.requirement !== 'information'
    })
  } catch (err) {
    console.error('Failed to load promotion actions', err)
    dryRunError.value = 'An unexpected error occurred while analyzing promotion requirements'
  } finally {
    loadingDryRun.value = false
  }

  // Fetch recipe metadata if we have an update_title_metadata action
  if (props.book.recipe_id && actions.value.some((a) => a.kind === 'update_title_metadata')) {
    loadingRecipeMetadata.value = true
    try {
      await loadRecipeMetadata(props.book.recipe_id)
    } catch (err) {
      console.error('Failed to resolve recipe metadata', err)
    } finally {
      loadingRecipeMetadata.value = false
    }
  }
}

function handleSubmit() {
  if (!props.book) return
  showConfirmDialog.value = true
}

async function executePromote() {
  if (!props.book) return

  submitting.value = true
  submitError.value = null

  try {
    const selectedActions = actions.value
      .filter(
        (action, index) =>
          action.requirement === 'mandatory' ||
          action.requirement === 'information' ||
          actionChecked.value[index],
      )
      .map((action) => {
        const originalIndex = actions.value.indexOf(action)
        let data = actionData.value[originalIndex] || action.data

        // For create_title, read back from TitleForm
        if (action.kind === 'create_title' && titleFormRefs.value[originalIndex]) {
          const formData = titleFormRefs.value[originalIndex]!.getFormData()
          data = { ...formData }
        }

        return {
          kind: action.kind,
          data,
          requirement: action.requirement,
        }
      })

    const result = await bookStore.promoteBook(props.book.id, false, { actions: selectedActions })
    if (!result) {
      submitError.value = bookStore.errors.join(', ') || 'Failed to promote book'
      return
    }

    emit('promoted')
    isOpen.value = false

    if (hasRecipeMetadataDifferences.value && props.book.recipe_id) {
      showRecipeUpdateDialog.value = true
    }
  } catch (err) {
    console.error('Failed to promote book', err)
    submitError.value = 'An unexpected error occurred while promoting the book'
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  isOpen.value = false
}
</script>

<style scoped>
.border-warning {
  border-left: 3px solid rgb(var(--v-theme-warning));
}
</style>
