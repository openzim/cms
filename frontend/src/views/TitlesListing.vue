<template>
  <div>
    <table class="table">
      <thead>
        <tr>
          <th>Title</th>
        </tr>
      </thead>
      <tbody v-if="titles">
        <tr
          v-for="title in titles"
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
      titles: null
    }
  },
  created () {
    const parent = this
    this.startLoading()

    const url = '/titles'

    this.queryAPI('GET', url).then(function (response) {
      parent.titles = response.data.items
      parent.endLoading()
    })
  }
}
</script>
