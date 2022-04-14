import { createRouter, createWebHistory } from 'vue-router'

import NotFound from './views/NotFound.vue'
import SupportUs from './views/SupportUs.vue'
import TitlesListing from './views/TitlesListing.vue'
import DigestersListing from './views/DigestersListing.vue'
import TitleDetail from './views/TitleDetail.vue'
import BookDetail from './views/BookDetail'
import BookListing from './views/BookListing'

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: { name: 'titles' }
  },
  {
    path: '/titles',
    name: 'titles',
    component: TitlesListing
  },
  {
    path: '/digesters',
    name: 'digesters',
    component: DigestersListing
  },
  {
    path: '/titles/:ident',
    name: 'title',
    component: TitleDetail,
    props: true
  },
  {
    path: '/books',
    name: 'books',
    component: BookListing
  },
  {
    path: '/books/:id',
    name: 'book',
    component: BookDetail,
    props: true
  },
  {
    path: '/support-us',
    name: 'support-us',
    component: SupportUs
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
  linkActiveClass: 'active',
  linkExactActiveClass: 'exact-active'
})

export default router
