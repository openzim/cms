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
  is_backup: boolean
}

export interface BookLight {
  id: string
  title_id?: string
  title_name?: string
  needs_processing: boolean
  has_error: boolean
  needs_file_operation: boolean
  location_kind: LocationKind
  created_at: string
  issues: string[]
  deletion_date?: string
  name?: string
  date?: string
  flavour?: string
  has_flavour_mismatch: boolean
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
  title_archived: boolean
  has_backup: boolean
  illustration_48x48_at_1: string | null
  illustration_48x48_at_1_hash: string | null
}

export interface ZimUrl {
  kind: 'view' | 'download'
  url: string
  collection: string
}

export interface ZimUrls {
  urls: Record<string, ZimUrl[]>
}

export interface BookHistory {
  id: string
  comment: string | null
  author: string
  created_at: string
  flavour: string | null
  name: string | null
}
