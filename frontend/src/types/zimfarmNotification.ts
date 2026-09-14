export interface ZimfarmNotificationLight {
  id: string
  task_id: string
  book_id?: string
  status: string
  received_at: string
}

export interface ZimfarmNotification extends ZimfarmNotificationLight {
  content: Record<string, unknown>
  events: string[]
}
