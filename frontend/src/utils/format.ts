import { DateTime } from 'luxon'

export function fromNow(value: string) {
  if (!value) return ''
  const start = DateTime.fromISO(value)
  if (!start.isValid) return value
  return start.toRelative()
}

export function formatDt(value?: string, format: string = 'fff') {
  // display a datetime in the provided format (defaults to 'fff')
  if (!value) return ''
  const dt = DateTime.fromISO(value)
  if (!dt.isValid) return value
  return dt.toFormat(format)
}
