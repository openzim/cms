import type { ApplicationStore } from '@/types/appBuild'

export interface Application {
  id: string
  title_id: string
  title_name: string
  flavour: string
  store: ApplicationStore
  enabled: boolean
  name: string
}

export interface ApplicationCreate {
  title_id: string
  flavour: string
  store: ApplicationStore
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
  store: ApplicationStore
  name: string
  enabled: boolean
  author: string
  comment: string | null
  created_at: string
}
