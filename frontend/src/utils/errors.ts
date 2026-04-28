import { type ErrorResponse } from '@/types/errors'

// Loose shape of what httpRequest's response interceptor passes to
// `Promise.reject` — `error.response.data` if present, otherwise the
// AxiosResponse, otherwise the Axios Error itself. Each of those has a
// different shape, so translateErrors has to check structurally.
interface MaybeAxiosResponse {
  status?: number
  statusText?: string
}

export function translateErrors(error: ErrorResponse | unknown): string[] {
  // The standard ErrorResponse path (API returned a JSON body matching
  // the ErrorResponse interface).
  if (error && typeof error === 'object') {
    const e = error as Partial<ErrorResponse>
    if (e.errors) {
      const errors: string[] = []
      if (e.message) {
        errors.push(e.message)
      }
      for (const [key, value] of Object.entries(e.errors)) {
        errors.push(`${key}: ${value}`)
      }
      return errors
    }
    if (e.message) {
      // Axios's "Network Error" case — true transport failure (DNS,
      // timeout, no connectivity). The previous code surfaced this
      // verbatim; expand it slightly so the user knows what kind of
      // failure this was.
      if (e.message === 'Network Error') {
        return ['Network error: could not reach the server']
      }
      return [e.message]
    }

    // The AxiosResponse fallthrough from httpRequest's interceptor:
    // the API returned a non-success status whose body wasn't a
    // structured ErrorResponse (empty body, HTML error page, etc.).
    // Don't say "Network error" here — there *was* a response, the
    // server just sent us something we don't understand. (#251)
    const r = error as MaybeAxiosResponse
    if (typeof r.status === 'number') {
      const detail = r.statusText ? ` ${r.statusText}` : ''
      return [`Unexpected error (HTTP ${r.status}${detail})`]
    }
  }

  return ['An unknown error occurred']
}
