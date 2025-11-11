import type { BookLight } from './book'

export interface WarehousePathInfo {
  path_id: string
  folder_name: string
  warehouse_name: string
}

export interface Title {
  id: string
  name: string
  producer_unique_id: string
  producer_display_name: string | null
  producer_display_url: string | null
  dev_warehouse_paths: WarehousePathInfo[]
  prod_warehouse_paths: WarehousePathInfo[]
  in_prod: boolean
  events: string[]
  books: BookLight[]
}

export interface TitleLight {
  id: string
  name: string
  producer_unique_id: string
  producer_display_name: string | null
  producer_display_url: string | null
}

export interface TitleCreate {
  name: string
  producer_unique_id: string
  producer_display_name?: string
  producer_display_url?: string
  dev_warehouse_path_ids: string[]
  prod_warehouse_path_ids: string[]
  in_prod?: boolean
}
