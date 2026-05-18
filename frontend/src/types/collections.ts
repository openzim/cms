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
}

export interface CollectionUpdate {
  name?: string
  download_base_url?: string | null
  view_base_url?: string | null
}
