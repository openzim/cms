export type ApplicationStore = 'android' | 'apple'

export type AppBuildStatus = 'pending' | 'running' | 'success' | 'failure' | 'cancelled'

export type AppBuildPhase = 'requested' | 'checks' | 'merge' | 'release' | 'building' | 'uploaded'

export interface ApplicationBuild {
  id: string
  title_id: string
  flavour: string
  store: ApplicationStore
  repository: string
  app_name: string
  status: AppBuildStatus
  phase: AppBuildPhase | null
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

export interface AppBuildCreate {
  flavour: string
  store: ApplicationStore
}

export interface AppBuildCheck {
  content_version: string
  built: boolean
  app_build: ApplicationBuild | null
}
