import { describe, expect, it } from 'vitest'
import { translateErrors } from './errors'

describe('translateErrors', () => {
  it('returns the message and per-field errors from a structured ErrorResponse', () => {
    const result = translateErrors({
      success: false,
      message: 'Validation failed',
      errors: { title: 'is required', author: 'too long' },
    })
    expect(result).toEqual([
      'Validation failed',
      'title: is required',
      'author: too long',
    ])
  })

  it('returns just the message when ErrorResponse has no per-field errors', () => {
    expect(
      translateErrors({ success: false, message: 'Forbidden' }),
    ).toEqual(['Forbidden'])
  })

  // Regression for #251: HTTP error from the server (an AxiosResponse came
  // through the interceptor when the body was empty / not an ErrorResponse).
  // The previous code returned the generic "An unknown error occurred"
  // banner; now we surface the status code so the user knows the server
  // responded.
  it('treats an AxiosResponse fallthrough as an unexpected HTTP error, not a network error', () => {
    const fakeAxiosResponse = {
      status: 502,
      statusText: 'Bad Gateway',
      headers: {},
      data: '',
    }
    expect(translateErrors(fakeAxiosResponse)).toEqual([
      'Unexpected error (HTTP 502 Bad Gateway)',
    ])
  })

  it('expands the "Network Error" axios message on real transport failures', () => {
    expect(translateErrors({ message: 'Network Error' })).toEqual([
      'Network error: could not reach the server',
    ])
  })

  it('falls back to "An unknown error occurred" for shapes it cannot read', () => {
    expect(translateErrors(undefined)).toEqual(['An unknown error occurred'])
    expect(translateErrors({})).toEqual(['An unknown error occurred'])
    expect(translateErrors('string error')).toEqual([
      'An unknown error occurred',
    ])
  })
})
