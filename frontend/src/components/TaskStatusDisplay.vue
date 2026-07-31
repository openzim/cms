<template>
  <div :class="['d-flex', 'ga-1', layoutClass]">
    <span>
      <v-btn
        v-if="zimfarmLink"
        :href="zimfarmLink"
        class="text-decoration-none text-no-wrap text-none"
        target="_blank"
        append-icon="mdi-open-in-new"
        size="small"
        variant="text"
      >
        <code :class="statusClass">{{ status }}</code
        >,
        {{ fromNow(computedTimestamp) }}
      </v-btn>
      <span v-else class="text-no-wrap">
        <code :class="statusClass">{{ status }}</code
        >,
        {{ fromNow(computedTimestamp) }}
      </span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { fromNow } from '@/utils/format'
import { computed } from 'vue'
import { useDisplay } from 'vuetify'

// Props
interface Props {
  status: string
  updatedAt?: string | null
  zimfarmLink?: string | null
  layout?: 'row' | 'column'
  justifyOnSmall?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  updatedAt: null,
  zimfarmLink: null,
  layout: 'row',
  justifyOnSmall: true,
})

const { smAndDown } = useDisplay()

// Computed properties
const layoutClass = computed(() => {
  const classes = props.layout === 'column' ? 'flex-column' : 'flex-row flex-wrap align-center'
  return smAndDown.value && props.justifyOnSmall ? `${classes} justify-end` : classes
})

const computedTimestamp = computed(() => {
  return props.updatedAt || ''
})

const statusClass = computed(() => {
  const status = props.status.toLowerCase()
  if (status === 'succeeded') return 'text-success'
  if (['failed', 'canceled', 'cancel_requested', 'canceling'].includes(status))
    return 'text-pink-accent-2'
  return 'text-warning'
})
</script>
