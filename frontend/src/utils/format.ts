import { filesize } from 'filesize'

import { DateTime, Duration } from 'luxon'

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

/**
 * Format a duration in seconds as a human-readable estimate
 */
export function formatEta(totalSeconds: number): string {
  const seconds = Math.round(totalSeconds)
  if (seconds < 1) return 'less than a minute'

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  const duration = Duration.fromObject({
    ...(days ? { days } : {}),
    ...(hours ? { hours } : {}),
    ...(minutes ? { minutes } : {}),
    ...(secs ? { seconds: secs } : {}),
  })

  return `~${duration.toHuman({ unitDisplay: 'long', listStyle: 'long' })}`
}

export function formattedBytesSize(value: number) {
  return filesize(value, { base: 2, standard: 'iec', precision: 3 }) // display in KiB, MiB,... instead of KB, MB,...
}

/**
 * Calculate the byte size of base64-encoded data.
 */
export function base64ByteSize(base64String: string): number {
  const base64 = base64String.includes(',') ? base64String.split(',')[1] : base64String
  if (!base64) return 0
  // Each base64 character represents 6 bits; 4 chars = 3 bytes
  const padding = base64.endsWith('==') ? 2 : base64.endsWith('=') ? 1 : 0
  return (base64.length * 3) / 4 - padding
}

/**
 * Return a human-readable file size for base64-encoded data.
 */
export function base64FormattedSize(base64String: string): string {
  const bytes = base64ByteSize(base64String)
  if (bytes === 0) return ''
  return formattedBytesSize(bytes)
}

export function matchOffliner(rawOffliner: string | null, offlinerNames: string[]): string {
  if (!rawOffliner) return 'Unknown'
  const lower = rawOffliner.toLowerCase()
  for (const name of offlinerNames) {
    if (lower.includes(name.toLowerCase())) return name
  }
  return 'Unknown'
}
