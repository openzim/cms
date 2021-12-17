<template>
  <main>
    <NavBar />
    <router-view class="container" />
  </main>
</template>

<script>
import axios from 'axios'

import Constants from './constants.js'
import NavBar from './components/NavBar.vue'

export default {
  name: 'App',
  components: { NavBar },
  computed: {
    axios () { // prefixed axios object with API url
      const headers = {}
      return axios.create({
        baseURL: Constants.backend_api,
        headers: headers,
        paramsSerializer: Constants.params_serializer
      })
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
}
</style>
