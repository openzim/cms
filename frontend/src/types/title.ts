import type { BookLight } from './book'

export interface WarehousePathInfo {
  path_id: string
  folder_name: string
  warehouse_name: string
}

export interface BaseTitleCollection {
  collection_name: string
  path: string
}

export interface TitleCollection extends BaseTitleCollection {
  collection_id: string
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
  collection_titles: BaseTitleCollection[]
}

export interface TitleUpdate {
  maturity: string
  collection_titles: BaseTitleCollection[]
}
