import { createRouter, createWebHistory } from 'vue-router'

import NotFound from './views/NotFound.vue'
import SupportUs from './views/SupportUs.vue'
import TitlesListing from './views/TitlesListing.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: {name: 'titles'},
  },
  {
    path: '/titles',
    name: 'titles',
    component: TitlesListing,
  },
  {
    path: '/support-us',
    name: 'support-us',
    component: SupportUs,
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound
  },
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
  linkActiveClass: "active",
  linkExactActiveClass: "exact-active",
})

export default router
