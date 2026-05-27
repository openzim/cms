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
  title: string | null
  creator: string | null
  publisher: string | null
  description: string | null
  language: string | null
  illustration_48x48_at_1: string | null
  long_description: string | null
  license: string | null
  relation: string | null
  source: string | null
  flavours: string[]
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
  title?: string | null
  creator?: string | null
  publisher?: string | null
  description?: string | null
  language?: string | null
  illustration_48x48_at_1?: string | null
  long_description?: string | null
  license?: string | null
  relation?: string | null
  source?: string | null
  flavours?: string[] | null
}

export interface TitleUpdate {
  name?: string
  maturity: string
  collection_titles: BaseTitleCollection[]
  title?: string | null
  creator?: string | null
  publisher?: string | null
  description?: string | null
  language?: string | null
  illustration_48x48_at_1?: string | null
  long_description?: string | null
  license?: string | null
  relation?: string | null
  source?: string | null
  flavours?: string[] | null
}
