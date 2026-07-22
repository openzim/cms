export function getImageDataUrl(base64String: string | null | undefined): string | undefined {
  if (!base64String) return undefined
  if (base64String.startsWith('data:') || base64String.startsWith('http')) return base64String
  return `data:image/png;base64,${base64String}`
}
