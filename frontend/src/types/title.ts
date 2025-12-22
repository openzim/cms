import type { BookLight } from './book'

export interface WarehousePathInfo {
  path_id: string
  folder_name: string
  warehouse_name: string
}

export interface TitleCollection {
  collection_id: string
  collection_name: string
  path: string
}

export interface Title {
  id: string
  name: string
  maturity: string
  events: string[]
  books: BookLight[]
  collections: TitleCollection[]
}

export interface TitleLight {
  id: string
  name: string
  maturity: string
}

export interface TitleCreate {
  name: string
  maturity: string
}
