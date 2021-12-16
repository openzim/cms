<template>
  <header class="p-3 bg-dark text-white">
    <div class="container">
      <div class="d-flex flex-wrap align-items-center justify-content-center justify-content-lg-start">
        <a class="d-flex align-items-center mb-2 mb-lg-0 text-white text-decoration-none">
          <div class="icon">
            <img
              class="logo"
              alt="openZIM logo"
              :src="publicPath + 'assets/logo.svg'"
            >
            <LoadingIndicator />
          </div>
        </a>

        <ul class="nav col-12 col-lg-auto me-lg-auto mb-2 justify-content-center mb-md-0">
          <li class="nav-item">
            <router-link
              class="nav-link px-2"
              :to="{ name: 'titles' }"
            >
              Titles
            </router-link>
          </li>
          <li class="nav-item">
            <router-link
              class="nav-link px-2"
              :to="{ name: 'home' }"
            >
              Digesters
            </router-link>
          </li>
          <li class="nav-item">
            <router-link
              class="btn btn-light btn-sm mt-1 mb-1 support"
              :to="{ name: 'support-us' }"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                width="16"
                height="16"
                style="color: rgb(234, 74, 170) !important; fill: currentColor;"
              ><path
                fill-rule="evenodd"
                d="M4.25 2.5c-1.336 0-2.75 1.164-2.75 3 0 2.15 1.58 4.144 3.365 5.682A20.565 20.565 0 008 13.393a20.561 20.561 0 003.135-2.211C12.92 9.644 14.5 7.65 14.5 5.5c0-1.836-1.414-3-2.75-3-1.373 0-2.609.986-3.029 2.456a.75.75 0 01-1.442 0C6.859 3.486 5.623 2.5 4.25 2.5zM8 14.25l-.345.666-.002-.001-.006-.003-.018-.01a7.643 7.643 0 01-.31-.17 22.075 22.075 0 01-3.434-2.414C2.045 10.731 0 8.35 0 5.5 0 2.836 2.086 1 4.25 1 5.797 1 7.153 1.802 8 3.02 8.847 1.802 10.203 1 11.75 1 13.914 1 16 2.836 16       5.5c0 2.85-2.045 5.231-3.885 6.818a22.08 22.08 0 01-3.744 2.584l-.018.01-.006.003h-.002L8 14.25zm0 0l.345.666a.752.752 0 01-.69 0L8 14.25z"
              /></svg> Support us
            </router-link>
          </li>
        </ul>

        <div class="text-end">
          <button
            type="button"
            class="btn btn-outline-light me-2"
          >
            Sign-in
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import LoadingIndicator from './LoadingIndicator.vue'
import Common from '../Common.mixin.js'

export default {
  name: 'NavBar',
  components: { LoadingIndicator },
  mixins: [Common]
}
</script>

<style scoped>
  header {
    margin-bottom: 1rem;
  }
  img.logo {
    width:  2rem;
    height: 2rem;
  }
  .support {
    margin-left: 1rem;
  }
  .support.active {
    background-color: rgb(234, 74, 170);
    border-color: rgb(234, 74, 170);
    color: white;
  }
  .support.active svg {
    fill: white !important;
  }
  .nav-link {
    --bs-text-opacity: 1;
    color: rgba(var(--bs-white-rgb),var(--bs-text-opacity)) !important;
  }
  .nav-link.active {
    --bs-text-opacity: 1;
    color: rgba(var(--bs-secondary-rgb),var(--bs-text-opacity)) !important;
  }
</style>
