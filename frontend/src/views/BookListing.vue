<template>
  <div class="container">
    <div class="form-group">
      <input
        v-model="selectedBookId"
        type="text"
        class="form-control"
        placeholder="Enter book ID..."
        @change="searchBooks"
      >
    </div>

    <ErrorMessage
      v-if="error"
      :message="error"
    />
  </div>
</template>

<script>
import Common from '../Common.mixin.js'
import ErrorMessage from '../components/ErrorMessage.vue'

export default {
  name: 'BookListing',
  components: {
    ErrorMessage
  },
  mixins: [Common],
  data () {
    return {
      selectedBookId: null,
      books: null,
      error: null
    }
  },
  methods: {
    searchBooks () {
      this.$router.push({ name: 'book', params: { id: this.selectedBookId } })
    }
  }
}
</script>
