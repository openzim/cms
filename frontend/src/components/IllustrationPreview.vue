<template>
  <div class="d-flex flex-column flex-grow-1">
    <v-img v-if="src" v-bind="$attrs" :src="src" :width="width" :alt="alt" class="rounded border" />
    <span v-if="sizeText" class="text-caption text-grey-darken-1 mt-1">{{ sizeText }}</span>
    <slot v-else name="empty">
      <strong v-if="emptyText">{{ emptyText }}</strong>
    </slot>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { base64ByteSize } from '@/utils/format'
import { getImageDataUrl } from '@/utils/image'

defineOptions({ inheritAttrs: false })

interface Props {
  /** Base64-encoded illustration, with or without a `data:` prefix */
  illustration?: string | null
  width?: number | string
  alt?: string
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  illustration: null,
  width: 48,
  alt: 'Illustration',
  emptyText: '',
})

const dimensions = ref<{ width: number; height: number } | null>(null)

watch(
  () => props.illustration,
  (illustration) => {
    dimensions.value = null
    const src = getImageDataUrl(illustration)
    if (!src) return
    const image = new Image()
    image.onload = () => {
      dimensions.value = { width: image.width, height: image.height }
    }
    image.src = src
  },
  { immediate: true },
)

const src = computed(() => getImageDataUrl(props.illustration))

const sizeText = computed(() => {
  if (!props.illustration) return ''
  const size = `${base64ByteSize(props.illustration)} bytes`
  const dims = dimensions.value
  if (!dims) return size
  return `${size} (${dims.width} × ${dims.height} px)`
})
</script>
