export type PublicationStore = 'android' | 'apple'

export type PublicationStatus = 'pending' | 'running' | 'success' | 'failure' | 'cancelled'

export type PublicationPhase = 'requested' | 'checks' | 'merge' | 'release' | 'building' | 'store'

export interface ApplicationPublication {
  id: string
  title_id: string
  flavour: string
  store: PublicationStore
  repository: string
  app_name: string
  status: PublicationStatus
  phase: PublicationPhase | null
  phase_started_at: string | null
  content_version: string
  tag: string | null
  branch: string
  pr_number: number | null
  pr_url: string | null
  merge_commit_sha: string | null
  release_url: string | null
  run_url: string | null
  error: string | null
  events: string[]
  requested_by: string | null
  cancelled_by: string | null
  created_at: string
  updated_at: string
}

export interface PublicationCreate {
  flavour: string
  store: PublicationStore
}

export interface PublicationCheck {
  content_version: string
  published: boolean
  publication: ApplicationPublication | null
}
