import type { Config } from '@/config'
import type { InjectionKey } from 'vue'

export default {
  config: Symbol() as InjectionKey<Config>,
  COOKIE_LIFETIME_EXPIRY: '10y', // 10 years
  // Notification constants
  NOTIFICATION_DEFAULT_DURATION: 5000, // 5 seconds
  NOTIFICATION_ERROR_DURATION: 8000, // 8 seconds for errors
  NOTIFICATION_SUCCESS_DURATION: 3000, // 3 seconds for success
}
