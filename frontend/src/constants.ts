import type { Config } from '@/config'
import type { InjectionKey } from 'vue'

export const TITLE_METADATA_FIELDS = [
  'name',
  'title',
  'creator',
  'publisher',
  'license',
  'language',
  'illustration_48x48_at_1',
  'description',
  'long_description',
  'relation',
  'source',
] as const

export type TitleMetadataFieldKey = (typeof TITLE_METADATA_FIELDS)[number]

export default {
  config: Symbol() as InjectionKey<Config>,
  COOKIE_LIFETIME_EXPIRY: '10y', // 10 years
  TOKEN_STORAGE_KEY: 'cms-auth',
  // User roles
  ROLES: ['viewer', 'collection-editor', 'global-editor', 'admin'] as const,
  // Notification constants
  NOTIFICATION_DEFAULT_DURATION: 5000, // 5 seconds
  NOTIFICATION_ERROR_DURATION: 8000, // 8 seconds for errors
  NOTIFICATION_SUCCESS_DURATION: 3000, // 3 seconds for success
  // Background event polling
  BACKGROUND_EVENT_POLL_INTERVAL: 2000, // 2 seconds
}
