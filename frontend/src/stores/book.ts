import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { Book, BookLight, ZimUrls } from '@/types/book'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useBookStore = defineStore('book', () => {
  const book = ref<Book | null>(null)
  const errors = ref<string[]>([])
  const books = ref<BookLight[]>([])
  const defaultLimit = ref<number>(Number(localStorage.getItem('books-table-limit') || 20))
  const paginator = ref<Paginator>({
    page: 1,
    page_size: defaultLimit.value,
    skip: 0,
    limit: defaultLimit.value,
    count: 0,
  })
  const authStore = useAuthStore()

  const fetchBook = async (bookId: string, forceReload: boolean = false) => {
    const service = await authStore.getApiService('books')
    // Check if we already have the book and don't need to force reload
    if (!forceReload && book.value && book.value.id === bookId) {
      return book.value
    }

    try {
      errors.value = []
      // Clear current book until we receive the right one
      book.value = null

      const response = await service.get<null, Book>(`/${bookId}`)
      book.value = response
    } catch (_error) {
      console.error('Failed to load book', _error)
      errors.value = translateErrors(_error as ErrorResponse)
    }
    return book.value
  }

  const fetchBooks = async (
    limit: number,
    skip: number,
    needs_attention: boolean | undefined = undefined,
    id: string | undefined = undefined,
    location_kinds: string[] | undefined = undefined,
    flag: string | undefined = undefined,
  ) => {
    const service = await authStore.getApiService('books')

    const needs_file_operation = flag === 'needs_file_operation' ? true : undefined
    const needs_processing = flag === 'needs_processing' ? true : undefined
    const has_error = flag === 'has_error' ? true : undefined
    const has_title = flag == 'no_title' ? false : undefined

    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        needs_attention,
        id,
        location_kinds,
        needs_file_operation,
        needs_processing,
        has_error,
        has_title,
      }).filter(
        ([name, value]) => !!value || (!['limit', 'skip'].includes(name) && value !== undefined),
      ),
    )
    try {
      const response = await service.get<null, ListResponse<Book>>('', {
        params: cleanedParams,
      })
      books.value = response.items
      paginator.value = response.meta
      errors.value = []
      return books.value
    } catch (_error) {
      console.error('Failed to fetch books', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const savePaginatorLimit = (limit: number) => {
    localStorage.setItem('books-table-limit', limit.toString())
  }

  const fetchZimUrls = async (zim_ids: string[]) => {
    const service = await authStore.getApiService('books')
    try {
      const response = await service.get<null, ZimUrls>('/zims', {
        params: { zim_ids },
      })
      return response
    } catch (_error) {
      console.error('Failed to fetch zim URLs', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const deleteBook = async (bookId: string, force_delete: boolean = false) => {
    const service = await authStore.getApiService('books')
    try {
      const response = await service.delete<{ force_delete: boolean }, Book>(`/${bookId}`, {
        params: { force_delete },
      })
      errors.value = []
      book.value = response
      return response
    } catch (_error) {
      console.error('Failed to delete book', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const recoverBook = async (bookId: string) => {
    const service = await authStore.getApiService('books')
    try {
      const response = await service.post<null, Book>(`/${bookId}/recover`)
      errors.value = []
      book.value = response
      return response
    } catch (_error) {
      console.error('Failed to recover book', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  const moveBook = async (bookId: string, destination: 'staging' | 'prod') => {
    const service = await authStore.getApiService('books')
    try {
      const response = await service.post<{ destination: string }, Book>(`/${bookId}/move`, {
        destination,
      })
      errors.value = []
      book.value = response
      return response
    } catch (_error) {
      console.error('Failed to move book', _error)
      errors.value = translateErrors(_error as ErrorResponse)
      return null
    }
  }

  return {
    // State
    defaultLimit,
    book,
    books,
    paginator,
    errors,
    // Actions
    fetchBook,
    fetchBooks,
    savePaginatorLimit,
    fetchZimUrls,
    deleteBook,
    recoverBook,
    moveBook,
  }
})
