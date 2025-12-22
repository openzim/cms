export interface Producer {
  display_name: string
  display_url: string
  unique_id: string
}

export interface BookLocation {
  warehouse_name: string
  path: string
  filename: string
  status: string
}

export interface Book {
  id: string
  title_id?: string
  needs_processing: boolean
  has_error: boolean
  needs_file_operation: boolean
  location_kind: 'jail' | 'staging' | 'prod'
  created_at: string
  name?: string
  date?: string
  flavour?: string
  article_count: number
  media_count: number
  size: number
  zimcheck_result: Record<string, unknown>
  zim_metadata: Record<string, unknown>
  events: string[]
  current_locations: BookLocation[]
  target_locations: BookLocation[]
}

export interface BookLight {
  id: string
  title_id?: string
  needs_processing: boolean
  has_error: boolean
  needs_file_operation: boolean
  location_kind: 'jail' | 'staging' | 'prod'
  created_at: string
  name?: string
  date?: string
  flavour?: string
}
