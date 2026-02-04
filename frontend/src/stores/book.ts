import constants from '@/constants'
import { useAuthStore } from '@/stores/auth'
import type { ListResponse, Paginator } from '@/types/base'
import type { Book, BookLight } from '@/types/book'
import type { ErrorResponse } from '@/types/errors'
import { translateErrors } from '@/utils/errors'
import { defineStore } from 'pinia'
import { inject, ref } from 'vue'
import type { VueCookies } from 'vue-cookies'

export const useBookStore = defineStore('book', () => {
  const $cookies = inject<VueCookies>('$cookies')
  const book = ref<Book | null>(null)
  const errors = ref<string[]>([])
  const books = ref<BookLight[]>([])
  const defaultLimit = ref<number>(Number($cookies?.get('books-table-limit') || 20))
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
    has_title: boolean | undefined = undefined,
    id: string | undefined = undefined,
    location_kind: string | undefined = undefined,
  ) => {
    const service = await authStore.getApiService('books')
    // filter out undefined values from params
    const cleanedParams = Object.fromEntries(
      Object.entries({
        limit,
        skip,
        has_title,
        id,
        location_kind,
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
    $cookies?.set('books-table-limit', limit, constants.COOKIE_LIFETIME_EXPIRY)
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
  }
})
