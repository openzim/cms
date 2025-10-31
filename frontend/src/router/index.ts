import InboxView from '@/views/InboxView.vue'
import NotFoundView from '@/views/NotFound.vue'
import SupportUsView from '@/views/SupportUs.vue'
import SignInView from '@/views/SignInView.vue'
import { createRouter, createWebHistory } from 'vue-router'
import TitlesView from '@/views/TitlesView.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    redirect: { name: 'inbox' },
  },
  {
    path: '/support-us',
    name: 'support',
    component: SupportUsView,
    meta: { title: 'CMS | Support Us' },
  },
  {
    path: '/sign-in',
    name: 'sign-in',
    component: SignInView,
    meta: { title: 'CMS | Sign In' },
  },
  {
    path: '/inbox',
    name: 'inbox',
    component: InboxView,
    meta: { title: 'CMS | Inbox' },
  },
  {
    path: '/titles',
    name: 'titles',
    component: TitlesView,
    meta: { title: 'CMS | Titles' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: '404',
    component: NotFoundView,
    meta: { title: 'CMS | Page Not Found' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Add global navigation guard to update title
router.beforeEach((to, from, next) => {
  // Update document title
  if (to.meta.title) {
    if (typeof to.meta.title === 'function') {
      // Handle dynamic titles with route parameters
      document.title = to.meta.title(to)
    } else {
      // Handle static titles
      document.title = to.meta.title as string
    }
  } else {
    document.title = 'CMS' // fallback
  }
  next()
})

export default router
