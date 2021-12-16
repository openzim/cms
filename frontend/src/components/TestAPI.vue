<template>
  <button
    class="btn btn-primary"
    :disabled="triggered"
    @click="trigger"
  >
    {{ text }}
  </button>
</template>

<script type="text/javascript">
import Common from '../Common.mixin.js'

export default {
  name: 'TestAPI',
  mixins: [Common],
  data () {
    return { triggered: false, received: null }
  },
  computed: {
    text () {
      if (!this.triggered) { return 'Test backend API connection' }
      if (!this.received) { return 'Querying backend' }
      return `Requested on ${this.received.requested_on}, backend got it on ${this.received.received_on}.`
    }
  },
  methods: {
    trigger () {
      const parent = this
      this.startLoading()

      const timestamp = parseInt(new Date().getTime() / 1000)
      const url = `/test/${timestamp}`

      parent.triggered = true
      this.queryAPI('GET', url)
        .then(function (response) {
          parent.received = response.data
          parent.endLoading()
        })
    }
  }
}
</script>
