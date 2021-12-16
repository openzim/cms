export default {
  methods: {
    queryAPI (method, path, data, config) {
      console.debug('queryAPI', method, path)
      if (data === undefined) { data = {} }
      if (config === undefined) { config = {} }

      // returning straight request/promise
      config.method = method
      config.url = path
      config.data = data
      return this.$root.axios(config)
    },
    startLoading () {
      this.$store.commit('setLoading', true)
    },
    endLoading () {
      this.$store.commit('setLoading', false)
    }
  },
  computed: {
    publicPath () { return process.env.BASE_URL } // for static files linking
  }
}
