export type PublicationStore = 'android' | 'apple'

export type PublicationStatus = 'pending' | 'running' | 'success' | 'failure' | 'cancelled'

export interface ApplicationPublication {
  id: string
  title_id: string
  flavour: string
  store: PublicationStore
  repository: string
  status: PublicationStatus
  content_version: string
  tag: string
  release_url: string | null
  run_url: string | null
  error: string | null
  requested_by: string | null
  created_at: string
  updated_at: string
}

export interface PublicationCreate {
  flavour: string
  store: PublicationStore
}
