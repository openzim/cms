<template>
  <div>
    <div>
      <h2>{{ ident }}</h2>
    </div>
    <div>
      <table class="table table-hover">
        <tbody v-if="title_metadata">
          <tr>
            <td>Name</td>
            <td>{{ ident }}</td>
          </tr>
          <tr>
            <td>Title</td>
            <td>{{ title_metadata.Title }}</td>
          </tr>
          <tr>
            <td>Creator</td>
            <td>{{ title_metadata.Creator }}</td>
          </tr>
          <tr>
            <td>Publisher</td>
            <td>{{ title_metadata.Publisher }}</td>
          </tr>
          <tr>
            <td>Date</td>
            <td>{{ title_metadata.Date }}</td>
          </tr>
          <tr>
            <td>Description</td>
            <td>{{ title_metadata.Description }}</td>
          </tr>
          <tr>
            <td>Flavour</td>
            <td>{{ title_metadata.Flavour }}</td>
          </tr>
          <tr>
            <td>Language</td>
            <td>{{ title_metadata.Language }}</td>
          </tr>
          <tr>
            <td>Tags</td>
            <td>{{ title_metadata.Tags }}</td>
          </tr>
          <tr>
            <td>Counter</td>
            <td>{{ title_metadata.Counter }}</td>
          </tr>
          <tr>
            <td>Scraper</td>
            <td>{{ title_metadata.Scraper }}</td>
          </tr>
          <tr>
            <td>Illustration_48x48</td>
            <td>
              <img
                :src="'data:image/png;base64,' + title_metadata.Illustration_48x48"
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
  props: {
    ident: {
      type: String,
      default: null
    }
  },
  data () {
    return {
      title_languages: null,
      title_tags: null,
      title_metadata: null
    }
  },
  created () {
    const parent = this
    this.startLoading()

    const url = `/titles/${this.ident}`

    this.queryAPI('GET', url).then(function (response) {
      parent.title_languages = response.data.languages
      parent.title_tags = response.data.tags
      parent.title_metadata = response.data.metadata
      parent.endLoading()
    })
  }
}
</script>
