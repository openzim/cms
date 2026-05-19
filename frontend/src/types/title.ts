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

export interface TitleLight {
  id: string
  name: string
  maturity: string
  archived: boolean
}

export interface Title extends TitleLight {
  events: string[]
  books: BookLight[]
  collections: TitleCollection[]
}

export interface TitleCreate {
  name: string
  maturity: string
  collection_titles: BaseTitleCollection[]
}

export interface TitleUpdate {
  name?: string
  maturity: string
  collection_titles: BaseTitleCollection[]
}
