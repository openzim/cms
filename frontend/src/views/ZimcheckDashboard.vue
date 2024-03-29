<template>
  <div class="container">
    <h2>ZimCheck Dashboard</h2>
    <div
      v-show="scraperData"
      class="container"
    >
      <div class="row">
        <div
          v-for="[check, total] in checkTotals"
          :key="check"
          class="col btn btn-light position-relative me-1"
        >
          {{ check }}
          <hr>
          <span
            class="badge"
            :class="isError(check) ? 'bg-danger': 'bg-warning'"
          >
            {{ $filters.numberToHuman(total) }}
          </span>
        </div>
      </div>
    </div>
    <hr>
    <table
      v-if="scraperData"
      class="table table-sm table-striped table-responsive"
    >
      <thead>
        <tr>
          <th>
            Scraper
          </th>
          <th
            v-for="check in checkTotals.keys()"
            :key="check"
          >
            {{ check }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="[scraper, checks] in scraperData"
          :key="scraper"
        >
          <th>
            {{ scraper }}
          </th>
          <td
            v-for="[check, total] in checkTotals"
            :key="check"
          >
            <span
              v-if="total === 0"
            >
              -
            </span>
            <span
              v-else-if="!checks[check]"
            >
              0 %
            </span>
            <span
              v-else
            >
              {{ Math.round((checks[check] * 100) / total) }} %
            </span>
          </td>
        </tr>
      </tbody>
    </table>
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
  name: 'ZimcheckDashboard',
  components: {
    ErrorMessage
  },
  mixins: [Common],
  data () {
    return {
      scraperData: null,
      checkTotals: new Map(),
      // list of known check we want to display values for (can be extended)
      knownChecks: new Map([
        ['checksum', 'error'],
        ['integrity', 'error'],
        ['empty', 'error'],
        ['metadata', 'error'],
        ['favicon', 'error'],
        ['main_page', 'error'],
        ['redundant', 'warning'],
        ['url_internal', 'error'],
        ['url_external', 'error'],
        ['redirect', 'error']
      ]),
      error: null // error message generated by API
    }
  },
  created () {
    const parent = this
    this.startLoading()

    const url = '/zimcheck'

    this.queryAPI('GET', url)
      .then(function (response) {
        parent.knownChecks.forEach((value, key) => parent.checkTotals.set(key, 0))
        parent.scraperData = new Map(Object.entries(response.data.checkData).sort((a, b) => a[0].localeCompare(b[0])))
        for (const data of parent.scraperData.values()) {
          for (const [check, value] of Object.entries(data)) {
            parent.checkTotals.set(check, (parent.checkTotals.get(check) || 0) + value)
          }
        }
      })
      .catch(function (error) {
        parent.standardErrorHandling(error)
      })
      .finally(function () {
        parent.endLoading()
      })
  },
  methods: {
    isError (check) {
      if (this.knownChecks.get(check) === 'error') {
        return true
      } else {
        return false
      }
    }
  }
}
</script>
