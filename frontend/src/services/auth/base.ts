import type { Config } from '@/config'
import type { StoredToken } from '@/types/auth'
import type { User } from '@/types/user'
import httpRequest from '@/utils/httpRequest'

export interface OAuthConfig {
  basePath: string
}

export function getOAuthConfig(config: Config): OAuthConfig {
  return {
    basePath: config.OAUTH_BASE_URL,
  }
}

/**
 * Abstract base class for authentication providers
 * Defines the common interface that all auth providers must implement
 */
export abstract class AuthProvider {
  protected readonly apiBaseUrl: string
  protected _user: User | null = null

  constructor(apiBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl
  }

  /**
   * Returns the currently authenticated user, if any
   */
  get user(): User | null {
    return this._user
  }

  /**
   * Clear the stored user
   */
  clearUser(): void {
    this._user = null
  }

  /**
   * Fetches user information from the provider's backend
   */
  async fetchUserInfo(accessToken: string): Promise<User> {
    const service = httpRequest({
      baseURL: `${this.apiBaseUrl}/auth`,
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    const response = (await service.get('/me')) as User
    this._user = response
    return response
  }

  /**
   * Initiates the login flow
   */
  abstract initiateLogin(username?: string, password?: string): Promise<void>

  /**
   * Handles the logout process
   */
  abstract logout(accessToken?: string): Promise<void>

  /**
   * Refreshes the authentication credentials
   */
  abstract refreshAuth(refreshToken: string): Promise<StoredToken>

  /**
   * Handles the authentication callback from the auth provider
   */
  abstract onCallback(callbackUrl: string): Promise<StoredToken>

  /**
   * Save the token from the auth provider
   */
  abstract saveToken(token: StoredToken): null

  /**
   * Load auth token
   */
  abstract loadToken(): Promise<StoredToken | null>

  abstract removeToken(): void
}
