// Boostrap5
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap'

// CMS styles
import '../public/assets/styles.css'

// main app
import { createApp } from 'vue'
import App from './App.vue'

// VueRouter
import router from './router.js'

// Vuex Store
import store from './store.js'

// Font Awesome
import { library } from '@fortawesome/fontawesome-svg-core'
import { faArrowCircleLeft, faCarrot, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

// matomo (stats.kiwix.org)
import VueMatomo from 'vue-matomo'

import filters from './filters'

const app = createApp(App)
app.use(router)
app.use(store)
library.add(faArrowCircleLeft)
library.add(faCarrot)
library.add(faSpinner)
app.component('FontAwesomeIcon', FontAwesomeIcon)
app.use(VueMatomo, {
  host: 'https://stats.kiwix.org',
  siteId: 12,
  trackerFileName: 'matomo',
  router: router
})
app.config.globalProperties.$filters = filters

// Sugar extensions
// import Sugar from 'sugar'
// Sugar.extend({namespaces: [Array, Object, String]});

app.mount('#app')
