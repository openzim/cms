export type LocationKind = 'quarantine' | 'staging' | 'prod' | 'to_delete' | 'deleted'

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

export interface BookLight {
  id: string
  title_id?: string
  needs_processing: boolean
  has_error: boolean
  needs_file_operation: boolean
  location_kind: LocationKind
  created_at: string
  deletion_date?: string
  name?: string
  date?: string
  flavour?: string
}

export interface Book extends BookLight {
  article_count: number
  media_count: number
  size: number
  zimcheck_result: Record<string, unknown>
  zim_metadata: Record<string, unknown>
  events: string[]
  current_locations: BookLocation[]
  target_locations: BookLocation[]
}

export interface ZimUrl {
  kind: 'view' | 'download'
  url: string
  collection: string
}

export interface ZimUrls {
  urls: Record<string, ZimUrl[]>
}
