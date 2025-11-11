<template>
  <v-dialog v-model="isOpen" max-width="600px" persistent>
    <v-card>
      <v-card-title class="text-h5 pa-4 bg-primary">
        <span class="text-white">Create New Title</span>
      </v-card-title>

      <v-card-text class="pt-4">
        <v-form ref="formRef" v-model="formValid">
          <v-text-field
            v-model="formData.name"
            label="Title Name"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />

          <v-text-field
            v-model="formData.producer_unique_id"
            label="Producer Unique ID (Zimfarm Recipe ID)"
            :rules="[rules.required]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
            hint="This is the Zimfarm recipe ID"
            persistent-hint
          />

          <v-autocomplete
            v-model="formData.dev_warehouse_path_ids"
            :items="warehousePathStore.warehousePathOptions"
            item-title="displayText"
            item-value="value"
            label="Dev Warehouse Paths"
            :rules="[ruleDevWarehouseRequired]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
            :loading="loadingWarehousePaths"
            multiple
            chips
            closable-chips
            hint="Select at least one dev warehouse path"
            persistent-hint
          />

          <v-autocomplete
            v-model="formData.prod_warehouse_path_ids"
            :items="warehousePathStore.warehousePathOptions"
            item-title="displayText"
            item-value="value"
            label="Prod Warehouse Paths"
            :rules="[ruleProdWarehouseRequired]"
            variant="outlined"
            density="comfortable"
            class="mb-2"
            :loading="loadingWarehousePaths"
            multiple
            chips
            closable-chips
            hint="Select at least one prod warehouse path"
            persistent-hint
          />

          <v-checkbox
            v-model="formData.in_prod"
            label="In Production"
            density="comfortable"
            hide-details
          />
        </v-form>

        <v-alert v-if="error" type="error" class="mt-4" density="compact">
          {{ error }}
        </v-alert>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn variant="text" @click="handleCancel" :disabled="loading">Cancel</v-btn>
        <v-btn
          color="primary"
          variant="elevated"
          @click="handleSubmit"
          :loading="loading"
          :disabled="!formValid || loading"
        >
          Create Title
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useTitleStore } from '@/stores/title'
import { useWarehousePathStore } from '@/stores/warehousePath'
import type { TitleCreate } from '@/types/title'
import { computed, onMounted, ref, watch } from 'vue'

interface Props {
  modelValue: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: []
}>()

const titleStore = useTitleStore()
const warehousePathStore = useWarehousePathStore()

const formRef = ref()
const formValid = ref(false)
const loading = ref(false)
const loadingWarehousePaths = ref(false)
const error = ref('')

const formData = ref<TitleCreate>({
  name: '',
  producer_unique_id: '',
  dev_warehouse_path_ids: [],
  prod_warehouse_path_ids: [],
  in_prod: false,
})

const isOpen = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const rules = {
  required: (value: string) => !!value || 'This field is required',
}

const ruleDevWarehouseRequired = (value: string[]) =>
  (value && value.length > 0) || 'At least one dev warehouse path is required'

const ruleProdWarehouseRequired = (value: string[]) =>
  (value && value.length > 0) || 'At least one prod warehouse path is required'

async function fetchWarehousePaths() {
  loadingWarehousePaths.value = true
  try {
    await warehousePathStore.fetchWarehousePaths()

    // Set default dev warehouse path to /.hidden/dev if it exists
    if (warehousePathStore.defaultDevPath) {
      formData.value.dev_warehouse_path_ids = [warehousePathStore.defaultDevPath.path_id]
    }
  } catch (err) {
    console.error('Failed to fetch warehouse paths', err)
    error.value = 'Failed to load warehouse paths'
  } finally {
    loadingWarehousePaths.value = false
  }
}

async function handleSubmit() {
  if (!formValid.value) return

  loading.value = true
  error.value = ''

  try {
    await titleStore.createTitle(formData.value)
    emit('created')
    resetForm()
    isOpen.value = false
  } catch (err) {
    console.error('Failed to create title', err)
    error.value = titleStore.errors.join(', ') || 'Failed to create title'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  resetForm()
  isOpen.value = false
}

function resetForm() {
  formData.value = {
    name: '',
    producer_unique_id: '',
    dev_warehouse_path_ids: [],
    prod_warehouse_path_ids: [],
    in_prod: false,
  }
  error.value = ''
  formRef.value?.resetValidation()
}

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      fetchWarehousePaths()
    }
  },
)

onMounted(() => {
  if (props.modelValue) {
    fetchWarehousePaths()
  }
})
</script>
