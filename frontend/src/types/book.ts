export interface Book {
  id: string
  title_id?: string
  status: string
  article_count: number
  media_count: number
  size: number
  zimcheck_result: Record<string, unknown>
  zim_metadata: Record<string, unknown>
  events: string[]
}

export interface BookLight {
  id: string
  title_id?: string
  status: string
}
