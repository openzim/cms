export type LocationKind = 'quarantine' | 'staging' | 'prod' | 'to_delete' | 'deleted'

export type BookStatus = 'active' | 'deleted' | 'to_delete' | 'all'

export const ACTIVE_LOCATION_KINDS: LocationKind[] = ['quarantine', 'staging', 'prod']

export type BookPromotionActionKind =
  | 'unknown_languages'
  | 'zimcheck_issues'
  | 'create_title'
  | 'restore_title'
  | 'update_title_metadata'
  | 'update_title_maturity'
  | 'set_title_collections'
  | 'update_title_flavours'
  | 'create_title_flavour'
  | 'update_flavour_recipe'

export type BookPromotionRequirement = 'mandatory' | 'optional' | 'information'

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

export interface ZimcheckSummary {
  zimcheck_version: string | null
  status: boolean | null
  checks: string[] | null
  error_count: number | null
  warning_count: number | null
  retcode: number | null
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
  offliner: string | null
  deletion_date?: string
  name?: string
  date?: string
  flavour: string
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
  zimcheck_result_url: string | null
  zimcheck_s3_deleted: boolean
  zimcheck_summary: ZimcheckSummary | null
  recipe_id: string | null
  recipe_link: string | null
  recipe_api_link?: string
  task_link?: string | null
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

export interface BaseBookPromotion {
  kind: BookPromotionActionKind
  data: Record<string, unknown>
  requirement: BookPromotionRequirement
}

export interface BookPromotionAction extends BaseBookPromotion {
  message: string
}

export interface BasePromoteBook {
  actions: BaseBookPromotion[]
}

export interface PromoteBook {
  actions: BookPromotionAction[]
}
