<template>
  <div class="d-flex flex-column flex-grow-1">
    <v-img v-if="src" v-bind="$attrs" :src="src" :width="width" :alt="alt" class="rounded border" />
    <span v-if="sizeText" class="text-body-small text-grey-darken-1 mt-1">{{ sizeText }}</span>
    <span
      v-if="digest && showDigest"
      class="text-body-small text-grey-darken-1 mt-1 font-monospace"
    >
      {{ digest }}
    </span>
    <slot v-else name="empty">
      <strong v-if="emptyText">{{ emptyText }}</strong>
    </slot>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import constants from '@/constants'
import type { Config } from '@/config'
import { base64ByteSize } from '@/utils/format'
import {
  fetchImageAsDataUrl,
  getIllustrationUrl,
  getImageDataUrl,
  isIllustrationHexDigest,
} from '@/utils/image'

defineOptions({ inheritAttrs: false })

interface Props {
  /**
   * Illustration value: either a hexadecimal digest or base64-encoded image,
   * with or without a `data:` prefix.
   */
  illustration?: string | null
  /** Whether to display the illustration digest below the image. */
  showDigest?: boolean
  width?: number | string
  alt?: string
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  illustration: null,
  showDigest: false,
  width: 48,
  alt: 'Illustration',
  emptyText: '',
})

const config = inject<Config | null>(constants.config, null)
const src = ref<string | undefined>(undefined)
const byteSize = ref<number | undefined>(undefined)
const dimensions = ref<{ width: number; height: number } | null>(null)

const digest = computed(() =>
  isIllustrationHexDigest(props.illustration) ? props.illustration : null,
)

let loadId = 0

watch(
  () => props.illustration,
  async (illustration) => {
    const currentLoad = ++loadId
    src.value = undefined
    byteSize.value = undefined
    dimensions.value = null

    if (!illustration) return

    const currentDigest = isIllustrationHexDigest(illustration) ? illustration : null
    if (currentDigest) {
      if (!config) return
      const dataUrl = await fetchImageAsDataUrl(getIllustrationUrl(config.CMS_API, currentDigest))
      if (currentLoad !== loadId || !dataUrl) return
      src.value = dataUrl
      byteSize.value = base64ByteSize(dataUrl)
    } else {
      src.value = getImageDataUrl(illustration)
      byteSize.value = base64ByteSize(illustration)
    }

    if (!src.value) return
    const image = new Image()
    image.onload = () => {
      if (currentLoad !== loadId) return
      dimensions.value = { width: image.width, height: image.height }
    }
    image.src = src.value
  },
  { immediate: true },
)

const sizeText = computed(() => {
  if (byteSize.value === undefined) return ''
  const size = `${byteSize.value} bytes`
  const dims = dimensions.value
  if (!dims) return size
  return `${size} (${dims.width} × ${dims.height} px)`
})
</script>
