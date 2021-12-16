<template>
  <div>
    <div>
      <h2>{{ $route.params.ident }}</h2>
    </div>
    <div>
      <table class="table table-hover">
        <tbody v-if="data">
          <tr>
            <td>Name</td>
            <td>{{ data.ident }}</td>
          </tr>
          <tr>
            <td>Title</td>
            <td>{{ data.metadata.Title }}</td>
          </tr>
          <tr>
            <td>Creator</td>
            <td>{{ data.metadata.Creator }}</td>
          </tr>
          <tr>
            <td>Publisher</td>
            <td>{{ data.metadata.Publisher }}</td>
          </tr>
          <tr>
            <td>Date</td>
            <td>{{ data.metadata.Date }}</td>
          </tr>
          <tr>
            <td>Description</td>
            <td>{{ data.metadata.Description }}</td>
          </tr>
          <tr>
            <td>Flavour</td>
            <td>{{ data.metadata.Flavour }}</td>
          </tr>
          <tr>
            <td>Language</td>
            <td>{{ data.metadata.Language }}</td>
          </tr>
          <tr>
            <td>Tags</td>
            <td>{{ data.metadata.Tags }}</td>
          </tr>
          <tr>
            <td>Counter</td>
            <td>{{ data.metadata.Counter }}</td>
          </tr>
          <tr>
            <td>Scraper</td>
            <td>{{ data.metadata.Scraper }}</td>
          </tr>
          <tr>
            <td>Illustration_48x48</td>
            <td>
              <img
                :src="'data:image/png;base64,' + data.metadata.Illustration_48x48"
                alt="base64 image"
              >
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import Common from '../Common.mixin.js'

export default {
  name: 'TitleDetail',
  mixins: [Common],
  data () {
    return {
      data: null
    }
  },
  created () {
    const parent = this
    this.startLoading()

    const url = `/titles/${this.$route.params.ident}`

    console.log(`url: ${url}`)

    parent.triggered = true
    this.queryAPI('GET', url).then(function (response) {
      parent.data = response.data
      parent.endLoading()
    })
  }
}
</script>
