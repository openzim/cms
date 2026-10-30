import type { PublicationStore } from '@/types/publication'

export interface Application {
  id: string
  title_id: string
  title_name: string
  flavour: string
  store: PublicationStore
  enabled: boolean
  name: string
}

export interface ApplicationCreate {
  title_id: string
  flavour: string
  store: PublicationStore
  enabled: boolean
  name: string
}

export interface ApplicationUpdate {
  enabled?: boolean
  name?: string
  comment?: string
}

export interface ApplicationHistory {
  id: string
  title_id: string
  title_name: string
  flavour: string
  store: PublicationStore
  name: string
  enabled: boolean
  author: string
  comment: string | null
  created_at: string
}
