import { createStore } from 'vuex'

const store = createStore({
  state () {
    return {
      loading: false,
    }
  },
  mutations: {
    setLoading (state, value) { // toggle GUI loader
      state.loading = value;
    },
  }
})

export default store
