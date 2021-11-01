// Boostrap5
import "bootstrap/dist/css/bootstrap.min.css"
import "bootstrap"

// CMS styles
import '../public/assets/styles.css'

// main app
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App);

// VueRouter
import router from './router.js'
app.use(router);

// Vuex Store
import store from './store.js'
app.use(store);

// Font Awesome
import { library } from '@fortawesome/fontawesome-svg-core'
import { faArrowCircleLeft, faCarrot, faSpinner } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'
library.add(faArrowCircleLeft);
library.add(faCarrot);
library.add(faSpinner);
app.component('font-awesome-icon', FontAwesomeIcon);

// matomo (stats.kiwix.org)
import VueMatomo from 'vue-matomo'
app.use(VueMatomo, {
  host: 'https://stats.kiwix.org',
  siteId: 12,
  trackerFileName: 'matomo',
  router: router,
});

// Sugar extensions
// import Sugar from 'sugar'
// Sugar.extend({namespaces: [Array, Object, String]});

app.mount('#app')
