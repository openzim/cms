<template>
  <p
    v-if="message"
    class="alert alert-danger"
  >
    {{ message }}
  </p>
</template>

<script type="text/javascript">
export default {
  name: 'ErrorMessage',
  props: {
    message: {
      type: String,
      default: null
    }
  }
}
</script>
