<template>
  <div>
    <table class="table">
      <thead>
        <tr><th>ID</th><th>Title</th><th>Description</th></tr>
      </thead>
      <tbody>
        <tr><td>1ED522CE-CF0E-4878-8B7D-FC59818B050F</td><td>Sample</td><td>n/a</td></tr>
      </tbody>
    </table>
    <TestAPI />
  </div>
</template>

<script>
import TestAPI from '../components/TestAPI.vue'

export default {
  name: 'TitlesListing',
  components: {TestAPI},
}
</script>
