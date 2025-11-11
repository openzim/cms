export interface Producer {
  display_name: string
  display_url: string
  unique_id: string
}

export interface BookLocation {
  warehouse_path_id: string
  warehouse_name: string
  folder_name: string
  filename: string
  status: string
}

export interface Book {
  id: string
  title_id?: string
  status: string
  created_at: string
  name?: string
  date?: string
  flavour?: string
  article_count: number
  media_count: number
  size: number
  zimcheck_result: Record<string, unknown>
  zim_metadata: Record<string, unknown>
  events: string[]
  producer: Producer
  current_locations: BookLocation[]
  target_locations: BookLocation[]
}

export interface BookLight {
  id: string
  title_id?: string
  status: string
  created_at: string
  name?: string
  date?: string
  flavour?: string
}
