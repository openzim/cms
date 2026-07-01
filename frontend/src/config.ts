import constants from '@/constants'
import httpRequest from '@/utils/httpRequest'
import type { PiniaPluginContext } from 'pinia'
import { inject } from 'vue'

export interface Config {
  CMS_API: string
  MATOMO_ENABLED: boolean
  MATOMO_HOST: string
  MATOMO_SITE_ID: number
  MATOMO_TRACKER_FILE_NAME: string
  OAUTH_BASE_URL: string
  LOGIN_MODES: Array<string>
  MEDIA_COUNT_INCREASE_THRESHOLD: number | undefined
  MEDIA_COUNT_DECREASE_THRESHOLD: number | undefined
  ARTICLE_COUNT_INCREASE_THRESHOLD: number | undefined
  ARTICLE_COUNT_DECREASE_THRESHOLD: number | undefined
  ZIM_TITLE_MAX_LENGTH: number | undefined
  ZIM_DESCRIPTION_MAX_LENGTH: number | undefined
}

export const ConfigService = {
  api: (baseURL: string, additional_headers?: object) =>
    httpRequest({
      baseURL: baseURL,
      headers: { ...additional_headers },
    }),

  getStaticConfig: function () {
    return this.api('/config.json').get<null, Config>('')
  },

  getApiConfig: function (cmsApi: string) {
    return this.api(`${cmsApi}/config`).get<null, Config>('')
  },

  getConfig: function () {
    return this.getStaticConfig().then((staticConfig: Config) =>
      this.getApiConfig(staticConfig.CMS_API)
        .then(
          (apiConfig: Config) =>
            ({
              ...apiConfig,
              ...staticConfig,
            }) as Config,
        )
        .catch((error) => {
          console.error('Failed to load API context settings:', error)
          return staticConfig as Config
        }),
    )
  },
}

declare module 'pinia' {
  export interface PiniaCustomProperties {
    config: Config
  }
}

export function configPlugin({ store }: PiniaPluginContext) {
  const config = inject<Config>(constants.config)
  if (config) {
    store.config = config
  }
}

export default ConfigService.getConfig.bind(ConfigService)
