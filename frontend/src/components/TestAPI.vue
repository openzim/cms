<template>
  <button @click="trigger" :disabled="triggered">{{ text }}</button>
</template>

<script type="text/javascript">
  import axios from 'axios'

  export default {
    name: 'TestAPI',
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
        let backend_api = window.environ.BACKEND_API || "https://api.cms.openzim.org/v1";
        let timestamp = parseInt(new Date().getTime() / 1000);
        let url = `${backend_api}/test/${timestamp}`;
        console.log(`Requesting ${url}…`);

        let parent = this;
        parent.triggered = true;

        axios.get(url)
          .then(function(response) {
            parent.received = response.data;
          });
      },
    }
};
</script>

<style type="text/css">
</style>
