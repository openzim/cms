import { byGrapheme } from 'split-by-grapheme'

export const TITLE_NAME_PATTERN = '^[a-z0-9\\-\\.]+?_[a-z]{2,3}(?:-[a-z]{2,10})?_[a-z0-9\\-\\.]+?$'

/** Result returned by a Vuetify rule: `true` when valid, otherwise an error message. */
export type ValidationResult = string | true

export function titleNameRule(value: unknown): ValidationResult {
  if (!value) return 'This field is required'
  if (!new RegExp(TITLE_NAME_PATTERN).test(String(value))) {
    return `Value does not meet pattern: ${TITLE_NAME_PATTERN}`
  }
  return true
}

export function graphemeLengthRule(max: number): (value: unknown) => ValidationResult {
  return (value: unknown) => {
    if (!value) return true
    if (String(value).split(byGrapheme).length > max) {
      return `Maximum length is ${max} characters.`
    }
    return true
  }
}

export function languageRule(value: unknown): ValidationResult {
  if (!value) return true
  const parts = String(value).split(',')
  return parts.every((part) => part.trim().length === 3)
    ? true
    : 'Language code(s) must be 3 characters long'
}

export function isTitleNameValid(value: unknown): boolean {
  return titleNameRule(value) === true
}

export function isWithinGraphemeLimit(value: unknown, max: number | undefined): boolean {
  if (!max) return true
  return graphemeLengthRule(max)(value) === true
}

export function isLanguageValid(value: unknown): boolean {
  return languageRule(value) === true
}
