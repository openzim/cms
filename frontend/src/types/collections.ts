import type { MultipartCompleteRequest } from '@/types/s3'

export interface CollectionLight {
  id: string
  name: string
  paths: string[]
  is_private: boolean
}

export interface Collection extends CollectionLight {
  warehouse: string
  download_base_url?: string
  view_base_url?: string
  article_count_increase_threshold?: number | null
  article_count_decrease_threshold?: number | null
  media_count_increase_threshold?: number | null
  media_count_decrease_threshold?: number | null
}

export interface CollectionUpdate {
  name?: string
  download_base_url?: string | null
  view_base_url?: string | null
  comment?: string | null
  article_count_increase_threshold?: number | null
  article_count_decrease_threshold?: number | null
  media_count_increase_threshold?: number | null
  media_count_decrease_threshold?: number | null
  is_private?: boolean
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

export interface TaskCreateRequest {
  file: MultipartCompleteRequest
}
