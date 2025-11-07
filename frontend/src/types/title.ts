export interface Title {
  id: string
  name: string
}

export interface TitleLight {
  id: string
  name: string
}

export interface TitleCreate {
  name: string
  producer_unique_id: string
  producer_display_name?: string
  producer_display_url?: string
  dev_warehouse_path_id: string
  prod_warehouse_path_id: string
  in_prod?: boolean
}
