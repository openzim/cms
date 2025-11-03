export interface ZimfarmNotification {
  id: string
  book_id?: string
  status: string
  received_at: string
  content: Record<string, unknown>
  events: string[]
}

export interface ZimfarmNotificationLight {
  id: string
  book_id?: string
  status: string
  received_at: string
}
