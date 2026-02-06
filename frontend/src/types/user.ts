export interface User {
  username: string
  scope: Record<string, Record<string, boolean>>
}
