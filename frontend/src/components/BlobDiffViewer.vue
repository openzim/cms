<template>
  <div class="blob-diff-viewer">
    <v-card flat variant="outlined">
      <v-card-text class="pa-0">
        <!-- Image comparison -->
        <div class="image-comparison">
          <v-row no-gutters>
            <v-col cols="6" class="pa-4 border-right">
              <div class="text-caption text-medium-emphasis mb-2">Previous</div>
              <IllustrationPreview
                :illustration="oldBlobContent"
                width="100%"
                max-height="400px"
                alt="Previous image/illustration"
              >
                <template #empty>
                  <div class="pa-4 text-center text-medium-emphasis">
                    <v-icon size="large" class="mb-2">mdi-image-off</v-icon>
                    <div class="text-caption">No previous image/illustration</div>
                  </div>
                </template>
              </IllustrationPreview>
            </v-col>
            <v-col cols="6" class="pa-4">
              <div class="text-caption text-medium-emphasis mb-2">Current</div>
              <IllustrationPreview
                :illustration="newBlobContent"
                width="100%"
                max-height="400px"
                alt="Current image/illustration"
              >
                <template #empty>
                  <div class="pa-4 text-center text-medium-emphasis">
                    <v-icon size="large" class="mb-2">mdi-image-off</v-icon>
                    <div class="text-caption">No current image/illustration (removed)</div>
                  </div>
                </template>
              </IllustrationPreview>
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import IllustrationPreview from '@/components/IllustrationPreview.vue'

interface Props {
  oldBlobContent: string | null
  newBlobContent: string | null
  fieldName?: string
}

withDefaults(defineProps<Props>(), {
  fieldName: 'blob',
})
</script>

<style scoped>
.blob-diff-viewer {
  width: 100%;
}

.border-right {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.image-comparison {
  max-height: 600px;
  overflow-y: auto;
}
</style>
