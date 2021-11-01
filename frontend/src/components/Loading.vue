<!-- Loading feedback to inform network operation is ongoing

  - displayed as a spinner on top of the logo
  - displayed based on store's loading status -->

<template>
  <span v-if="should_display" class="main-loader">
    <font-awesome-icon icon="spinner" size="lg" spin />
  </span>
</template>

<script type="text/javascript">
  export default {
    name: 'Loading',
    computed: {
      should_display() {
        return this.$store.state.loading;
      },
    }
  }
</script>

<style type="text/css" scoped>
.main-loader {
  color: white;
  position: relative;
  top: 0;
  left: 0;
  margin: -2rem;
  padding: .25rem;
}
</style>
