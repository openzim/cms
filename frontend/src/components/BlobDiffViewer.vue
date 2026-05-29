<template>
  <div class="blob-diff-viewer">
    <v-card flat variant="outlined">
      <v-card-text class="pa-0">
        <!-- Image comparison -->
        <div class="image-comparison">
          <v-row no-gutters>
            <v-col cols="6" class="pa-4 border-right">
              <div class="text-caption text-medium-emphasis mb-2">Previous</div>
              <div v-if="!oldBlobContent" class="pa-4 text-center text-medium-emphasis">
                <v-icon size="large" class="mb-2">mdi-image-off</v-icon>
                <div class="text-caption">No previous image/illustration</div>
              </div>
              <v-img
                v-else
                :src="oldBlobDataUri"
                max-height="400px"
                contain
                alt="Previous image/illustration"
                class="border rounded"
              />
            </v-col>
            <v-col cols="6" class="pa-4">
              <div class="text-caption text-medium-emphasis mb-2">Current</div>
              <div v-if="!newBlobContent" class="pa-4 text-center text-medium-emphasis">
                <v-icon size="large" class="mb-2">mdi-image-off</v-icon>
                <div class="text-caption">No current image/illustration (removed)</div>
              </div>
              <v-img
                v-else
                :src="newBlobDataUri"
                max-height="400px"
                contain
                alt="Current image/illustration"
                class="border rounded"
              />
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  oldBlobContent: string | null
  newBlobContent: string | null
  fieldName?: string
}

const props = withDefaults(defineProps<Props>(), {
  fieldName: 'blob',
})

// Convert base64 strings to data URIs for image display
const oldBlobDataUri = computed(() => {
  if (!props.oldBlobContent) return ''
  // Assume PNG format by default, could be enhanced to detect mime type
  return `data:image/png;base64,${props.oldBlobContent}`
})

const newBlobDataUri = computed(() => {
  if (!props.newBlobContent) return ''
  return `data:image/png;base64,${props.newBlobContent}`
})
</script>

<style scoped>
.blob-diff-viewer {
  width: 100%;
}

.border-right {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.border {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.image-comparison {
  max-height: 600px;
  overflow-y: auto;
}
</style>
