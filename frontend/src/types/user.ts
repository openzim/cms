export interface User {
  id: string
  role: string
  display_name: string
  has_password: boolean
  idp_sub: string | null
  username: string | null
  scope: Record<string, Record<string, boolean>>
}
