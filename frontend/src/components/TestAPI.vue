<template>
  <button class="btn btn-primary" @click="trigger" :disabled="triggered">{{ text }}</button>
</template>

<script type="text/javascript">
import Common from '../Common.mixin.js'

export default {
  name: 'TestAPI',
  mixins: [Common],
  data() {
    return {triggered: false, received: null};
  },
  computed: {
    text() {
      if (!this.triggered)
        return "Test backend API connection";
      if (!this.received)
        return "Querying backend";
      return `Requested on ${this.received.requested_on}, backend got it on ${this.received.received_on}.`;
    }
  },
  methods: {
    trigger() {
      let parent = this;
      this.startLoading();

      let timestamp = parseInt(new Date().getTime() / 1000);
      let url = `/test/${timestamp}`;

      parent.triggered = true;
      this.queryAPI("GET", url)
        .then(function(response) {
          parent.received = response.data;
          parent.endLoading();
        });
    },
  }
};
</script>
