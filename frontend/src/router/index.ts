import InboxView from '@/views/InboxView.vue'
import NotFoundView from '@/views/NotFound.vue'
import SupportUsView from '@/views/SupportUs.vue'
import SignInView from '@/views/SignInView.vue'
import OAuthCallbackView from '@/views/OAuthCallbackView.vue'
import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import TitlesView from '@/views/TitlesView.vue'
import TitleView from '@/views/TitleView.vue'
import BookView from '@/views/BookView.vue'
import ZimfarmNotificationView from '@/views/ZimfarmNotificationView.vue'

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
    path: '/oauth/callback',
    name: 'oauth-callback',
    component: OAuthCallbackView,
    meta: { title: 'CMS | Authenticating...' },
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
    path: '/title/:id',
    name: 'title-detail',
    component: TitleView,
    props: true,
    meta: {
      title: (to: RouteLocationNormalized) => `CMS | Title • ${to.params.id}`,
    },
  },
  {
    path: '/book/:id',
    name: 'book-detail',
    component: BookView,
    props: true,
    meta: {
      title: (to: RouteLocationNormalized) => `CMS | Book • ${to.params.id}`,
    },
  },
  {
    path: '/zimfarm-notification/:id',
    name: 'zimfarm-notification-detail',
    component: ZimfarmNotificationView,
    props: true,
    meta: {
      title: (to: RouteLocationNormalized) => `CMS | Zimfarm Notification • ${to.params.id}`,
    },
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
