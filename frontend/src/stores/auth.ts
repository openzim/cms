import type { Config } from '@/config'
import { translateErrors } from '@/utils/errors'
import constants from '@/constants'
import httpRequest from '@/utils/httpRequest'
import type { ErrorResponse, OAuth2ErrorResponse } from '@/types/errors'
import { defineStore } from 'pinia'
import { inject, ref, computed } from 'vue'
import type { StoredToken, AuthProviderType } from '@/types/auth'
import { getOAuthConfig } from '@/services/auth/base'
import { OAuthSessionProvider } from '@/services/auth/OAuthSessionProvider'
import { LocalAuthProvider } from '@/services/auth/LocalAuthProvider'
import type { AuthProvider } from '@/services/auth/base'
import type { User } from '@/types/user'

export const useAuthStore = defineStore('auth', () => {
  const errors = ref<string[]>([])
  const token = ref<StoredToken | null>(null)
  const user = ref<User | null>(null)

  const config = inject<Config>(constants.config)

  if (!config) {
    throw new Error('Config is not defined')
  }

  const oauthProvider = new OAuthSessionProvider(getOAuthConfig(config))
  const localauthProvider = new LocalAuthProvider(config.CMS_API)

  const getAuthProvider = (providerType: AuthProviderType): AuthProvider => {
    switch (providerType) {
      case 'oauth':
        if (!oauthProvider) {
          throw new Error('No oauth provider configured.')
        }
        return oauthProvider
      case 'local':
        return localauthProvider
      default:
        throw new Error(`Unknown auth provider type: ${providerType}`)
    }
  }

  // Track refresh state to prevent duplicate requests
  const isRefreshFailed = ref(false)
  const refreshPromise = ref<Promise<StoredToken | null> | null>(null)

  // Computed properties
  const isLoggedIn = computed(() => {
    return token.value !== null && user.value !== null
  })

  const username = computed(() => {
    return user.value?.username || null
  })

  const accessToken = computed(() => {
    return token.value?.access_token || null
  })

  const permissions = computed(() => {
    return user.value?.scope || {}
  })

  const refreshToken = computed(() => {
    return token.value?.refresh_token || null
  })

  const tokenExpiryDate = computed(() => {
    if (!token.value) return null
    return new Date(token.value.expires_time)
  })

  const isTokenExpired = computed(() => {
    if (!tokenExpiryDate.value) return true
    return new Date() >= tokenExpiryDate.value
  })

  const hasPermission = (resource: string, action: string) => {
    if (!token.value) return false
    return user.value?.scope[resource]?.[action] || false
  }

  /**
   * Check if an error is a permanent refresh token failure
   */
  const isPermanentRefreshFailure = (error: unknown): boolean => {
    // Check if it's an OAuth2 error response
    const oauth2Error = error as OAuth2ErrorResponse
    if (oauth2Error?.error === 'invalid_grant' || oauth2Error?.code == 401) {
      return true
    }

    // Check if it's a backend API error response
    const apiError = error as ErrorResponse
    if (apiError?.message) {
      const message = apiError.message.toLowerCase()
      if (
        message.includes('invalid authentication credentials') ||
        message.includes('refresh token expired')
      ) {
        return true
      }
    }

    return false
  }

  const authenticate = async (
    providerType: AuthProviderType,
    username?: string,
    password?: string,
  ) => {
    try {
      const provider = getAuthProvider(providerType)
      await provider.initiateLogin(username, password)
      // Oauth providers typically redirect to a new url as part of the
      // login process. If we are still here, it means this is from the local
      // provider which has stored the token
      const newToken = await provider.loadToken()
      if (!newToken) {
        throw new Error('Invalid authentication token')
      }
      token.value = newToken
      await fetchUserInfo(newToken.access_token)

      errors.value = []
      provider.saveToken(newToken)

      isRefreshFailed.value = false

      return true
    } catch (err: unknown) {
      token.value = null
      user.value = null
      errors.value = translateErrors(err as ErrorResponse)
      return false
    }
  }

  const getApiService = async (baseURL: string) => {
    const token = await loadToken()
    if (!token)
      return httpRequest({
        baseURL: `${config.CMS_API}/${baseURL}`,
      })

    return httpRequest({
      baseURL: `${config.CMS_API}/${baseURL}`,
      headers: {
        Authorization: `Bearer ${token.access_token}`,
      },
    })
  }

  const fetchUserInfo = async (accessToken: string) => {
    try {
      const apiService = httpRequest({
        baseURL: `${config.CMS_API}/auth`,
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
      const response = (await apiService.get('/me')) as User
      user.value = response
      errors.value = []
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      user.value = null
      errors.value = translateErrors(error as ErrorResponse)
    }
  }

  const loadToken = async (): Promise<StoredToken | null> => {
    // If already authenticated and token is still valid, return current token
    if (token.value && tokenExpiryDate.value && tokenExpiryDate.value > new Date()) {
      return token.value
    }

    let storedToken: StoredToken | null = null
    // Try to load from kiwx/local providers as we don't know which
    try {
      if (oauthProvider) {
        storedToken = await oauthProvider.loadToken()
      }

      if (!storedToken) {
        storedToken = await localauthProvider.loadToken()
      }
    } catch (error: unknown) {
      console.error('Failed to load token:', error)
      await logout()
    }
    if (!storedToken) return null

    // Check if token is expired
    const expiry = new Date(storedToken.expires_time)
    const now = new Date()

    if (now > expiry) {
      // Token expired, check if refresh is already in progress
      if (refreshPromise.value) {
        const refreshed = await refreshPromise.value
        if (!refreshed) {
          await logout()
          return null
        }
        token.value = refreshed
        return refreshed
      }
      // Try to refresh
      storedToken = await renewToken(storedToken)
    }

    // Token is still valid
    if (!storedToken) {
      await logout()
      return null
    }
    if (!user.value) {
      await fetchUserInfo(storedToken.access_token)
    }
    token.value = storedToken
    return storedToken
  }

  const renewToken = async (storedToken: StoredToken): Promise<StoredToken | null> => {
    // If refresh has already failed permanently, don't retry
    const provider = getAuthProvider(storedToken.token_type)
    if (isRefreshFailed.value) {
      provider.removeToken()
      return null
    }

    // If a refresh is already in progress, wait for it
    if (refreshPromise.value) {
      return await refreshPromise.value
    }

    if (!storedToken.refresh_token) {
      console.error('No refresh token available')
      return null
    }

    // Create and store the refresh promise to prevent duplicate requests
    refreshPromise.value = provider.refreshAuth(storedToken.refresh_token)

    try {
      const newToken = await refreshPromise.value
      if (!newToken) {
        throw new Error('Unable to refresh token')
      }
      await fetchUserInfo(newToken.access_token)
      isRefreshFailed.value = false
      return newToken
    } catch (error) {
      console.error('Token refresh failed:', error)

      // Check if this is a permanent failure
      if (isPermanentRefreshFailure(error)) {
        isRefreshFailed.value = true
        provider.removeToken()
      }

      token.value = null
      user.value = null
      errors.value = translateErrors(error as ErrorResponse)
      return null
    } finally {
      // Clear the promise once done
      refreshPromise.value = null
    }
  }

  const logout = async () => {
    // If we have a Kiwix token, revoke it
    if (token.value?.token_type) {
      try {
        const provider = getAuthProvider(token.value?.token_type)
        await provider.logout()
      } catch (error) {
        console.error('Error revoking token:', error)
      }
    }

    token.value = null
    user.value = null

    // Reset refresh failure state on logout
    isRefreshFailed.value = false
    refreshPromise.value = null
  }

  const handleCallBack = async (providerType: AuthProviderType, callbackUrl: string) => {
    try {
      const provider = getAuthProvider(providerType)
      const newToken = await provider.onCallback(callbackUrl)
      token.value = newToken

      // Fetch user info from backend using the Kiwix token
      await fetchUserInfo(newToken.access_token)

      errors.value = []
      provider.saveToken(newToken)

      // Reset refresh failure state on successful login
      isRefreshFailed.value = false

      return true
    } catch (err: unknown) {
      token.value = null
      user.value = null
      errors.value = translateErrors(err as ErrorResponse)
      return false
    }
  }

  return {
    // State
    errors,
    token,
    user,
    isRefreshFailed,
    refreshPromise,
    permissions,

    // Computed
    isLoggedIn,
    username,
    accessToken,
    refreshToken,
    tokenExpiryDate,
    isTokenExpired,

    // Methods
    loadToken,
    fetchUserInfo,
    renewToken,
    authenticate,
    logout,
    getApiService,
    handleCallBack,
    hasPermission,
  }
})
