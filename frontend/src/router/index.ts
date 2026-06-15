import InboxView from '@/views/InboxView.vue'
import NotFoundView from '@/views/NotFound.vue'
import SupportUsView from '@/views/SupportUs.vue'
import SignInView from '@/views/SignInView.vue'
import OAuthCallbackView from '@/views/OAuthCallbackView.vue'
import UsersView from '@/views/UsersView.vue'
import UserView from '@/views/UserView.vue'
import CollectionsView from '@/views/CollectionsView.vue'
import CollectionView from '@/views/CollectionView.vue'
import ArchivedTitlesView from '@/views/ArchivedTitlesView.vue'
import BackupBooksView from '@/views/BackupBooksView.vue'
import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'
import TitlesView from '@/views/TitlesView.vue'
import TitleView from '@/views/TitleView.vue'
import BookView from '@/views/BookView.vue'
import BooksView from '@/views/BooksView.vue'
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
    path: '/books',
    name: 'books',
    component: BooksView,
    meta: { title: 'CMS | Books' },
  },
  {
    path: '/books/backups',
    name: 'backup-books',
    component: BackupBooksView,
    meta: { title: 'CMS | Backup Books', parentNavigation: 'books' },
  },
  {
    path: '/titles',
    name: 'titles',
    component: TitlesView,
    meta: { title: 'CMS | Titles' },
  },
  {
    path: '/titles/archives',
    name: 'archived-titles',
    component: ArchivedTitlesView,
    meta: { title: 'CMS | Archived Titles', parentNavigation: 'titles' },
  },
  {
    path: '/title/:id',
    name: 'title-detail',
    component: TitleView,
    props: true,
    meta: {
      parentNavigation: 'titles',
      title: (to: RouteLocationNormalized) => `CMS | Title • ${to.params.id}`,
    },
  },
  {
    path: '/title/:id/:selectedTab',
    name: 'title-detail-tab',
    component: TitleView,
    props: true,
    meta: {
      parentNavigation: 'titles',
      title: (to: RouteLocationNormalized) => `CMS | Title • ${to.params.id}`,
    },
  },
  {
    path: '/book/:id',
    name: 'book-detail',
    component: BookView,
    props: true,
    meta: {
      parentNavigation: 'books',
      title: (to: RouteLocationNormalized) => `CMS | Book • ${to.params.id}`,
    },
  },
  {
    path: '/book/:id/:selectedTab',
    name: 'book-detail-tab',
    component: BookView,
    props: true,
    meta: {
      parentNavigation: 'books',
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
    path: '/users/:userId',
    name: 'user-detail',
    component: UserView,
    props: true,
    meta: {
      parentNavigation: 'users',
      title: (to: RouteLocationNormalized) => `CMS | User • ${to.params.userId}`,
    },
  },
  {
    path: '/users/:userId/:selectedTab',
    name: 'user-detail-tab',
    component: UserView,
    props: true,
    meta: {
      parentNavigation: 'users',
      title: (to: RouteLocationNormalized) => `CMS | User • ${to.params.userId}`,
    },
  },
  {
    path: '/users',
    name: 'users',
    component: UsersView,
    meta: { title: 'CMS | Users' },
  },
  {
    path: '/collections',
    name: 'collections',
    component: CollectionsView,
    meta: { title: 'CMS | Collections' },
  },
  {
    path: '/collection/:id',
    name: 'collection-detail',
    component: CollectionView,
    props: true,
    meta: {
      parentNavigation: 'collections',
      title: (to: RouteLocationNormalized) => `CMS | Collection • ${to.params.id}`,
    },
  },
  {
    path: '/collection/:id/:selectedTab',
    name: 'collection-detail-tab',
    component: CollectionView,
    props: true,
    meta: {
      parentNavigation: 'collections',
      title: (to: RouteLocationNormalized) => `CMS | Collection • ${to.params.id}`,
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
