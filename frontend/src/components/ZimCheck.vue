<template>
  <div class="zimcheck">
    <p
      class="position-relative"
    >
      <span
        class="me-2 btn btn-sm btn-neutral"
        :class="success ? 'alert-success': 'alert-danger'"
      >
        zimcheck {{ book.zimcheck.zimcheck_version }}
        <font-awesome-icon
          v-if="success"
          icon="check"
          size="sm"
        />
        <font-awesome-icon
          v-else
          icon="times"
          size="sm"
        />
      </span>
      <button
        class="btn btn-sm btn-neutral me-2"
        @click="seen = !seen"
      >
        <font-awesome-icon
          v-if="seen"
          icon="toggle-on"
          size="sm"
        />
        <font-awesome-icon
          v-else
          icon="toggle-off"
          size="sm"
        />
        toggle details
      </button>
      <span
        v-for="(value, name) in logsData"
        :key="name"
        class="btn btn-sm btn-light position-relative me-4"
      >
        {{ name }}
        <span
          class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger"
        >
          {{ value }}
        </span>
      </span>
    </p>
    <div class="table-responsive">
      <table
        v-show="seen"
        class="table table-sm table-striped table-responsive"
      >
        <tbody>
          <tr>
            <th>
              check
            </th>
            <th>
              level
            </th>
            <th>
              message
            </th>
          </tr>
          <tr
            v-for="log in book.zimcheck.logs"
            id="hide"
            :key="log"
          >
            <td>
              {{ log.check }}
            </td>
            <td>
              {{ log.level }}
            </td>
            <td>
              {{ log.message }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
<script type="text/javascript">
export default {
  name: 'ZimCheck',
  props: {
    book: {
      type: Object,
      default (rawProps) {
        return {}
      }
    }
  },
  data () {
    return {
      logsData: {},
      seen: false
    }
  },
  computed: {
    success () {
      return this.book && this.book.zimcheck.status === true
    }
  },
  created () {
    if (!this.book) {
      return
    }
    for (const log of this.book.zimcheck.logs) {
      this.logsData[log.check] = (this.logsData[log.check] || 0) + 1
    }
  }
}
</script>
