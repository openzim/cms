export interface Paginator {
  count: number
  skip: number
  limit: number
  page_size: number
  page: number
}

export interface ListResponse<T> {
  meta: Paginator
  items: T[]
}
