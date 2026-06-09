export interface CollectionLight {
  id: string
  name: string
  paths: string[]
}

export interface Collection {
  id: string
  name: string
  warehouse: string
  download_base_url?: string
  view_base_url?: string
  article_count_change_threshold?: number | null
  media_count_change_threshold?: number | null
}

export interface CollectionUpdate {
  name?: string
  download_base_url?: string | null
  view_base_url?: string | null
  comment?: string | null
  article_count_change_threshold?: number | null
  media_count_change_threshold?: number | null
}

export interface CollectionHistory {
  id: string
  comment: string | null
  author: string
  created_at: string
  name: string
  download_base_url?: string
  view_base_url?: string
}
