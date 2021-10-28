<template>
  <img alt="openZIM logo" :src="publicPath + 'assets/logo.svg'" />
  <p><TestAPI /></p>
</template>

<script>

import TestAPI from './components/TestAPI.vue'

export default {
  name: 'App',
  components: {TestAPI},
  computed: {
    publicPath() { return process.env.BASE_URL; },  // for static files linking
  },
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin: 1em;
}
img {
    width: 10em;
  }
</style>
