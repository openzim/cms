export interface OfflinerFlags {
  offliner_id: string
  [key: string]: unknown
}

export interface RecipeConfig {
  platform?: string
  warehouse_path: string
  artifacts_globs?: string[]
  artifacts_globs_str?: string // generated field
  monitor: boolean
  offliner: OfflinerFlags
}

export interface ExpandedRecipeConfig extends RecipeConfig {
  mount_point: string
  command: string[]
  str_command: string
}

export interface Recipe {
  // not all fields of a recipe are included in this interface
  id: string
  name: string
  config: ExpandedRecipeConfig
  version: string
  offliner: string
}

export interface Blob {
  id: string
  flag_name: string
  kind: string
  url: string
  checksum: string
  comments: string
  created_at: string
}

export interface CreateBlob {
  flag_name: string
  kind: string
  data: string
  comments: string
}
