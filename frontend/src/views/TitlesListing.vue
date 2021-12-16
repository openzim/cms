<template>
  <div>
    <table class="table">
      <thead>
        <tr>
          <th>Title</th>
        </tr>
      </thead>
      <tbody v-if="data">
        <tr
          v-for="title in data.items"
          :key="title.ident"
        >
          <td>
            <router-link :to="{ name: 'title', params: { ident: title.ident } }">
              {{ title.ident }}
            </router-link>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import Common from '../Common.mixin.js'

export default {
  name: 'TitlesListing',
  mixins: [Common],
  data () {
    return {
      data: null
    }
  },
  created () {
    const parent = this
    this.startLoading()

    const url = '/titles'

    parent.triggered = true
    this.queryAPI('GET', url).then(function (response) {
      parent.data = response.data
      parent.endLoading()
    })
  }
}
</script>
