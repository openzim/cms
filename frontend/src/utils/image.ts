import httpRequest from '@/utils/httpRequest'

export const ILLUSTRATION_HEX_DIGEST_REGEX = /^[0-9a-f]{16}$/

export function isIllustrationHexDigest(value: string | null | undefined): boolean {
  return !!value && ILLUSTRATION_HEX_DIGEST_REGEX.test(value)
}

export function getIllustrationUrl(cmsApi: string, hexDigest: string): string {
  return `${cmsApi.replace(/\/+$/, '')}/illustrations/${hexDigest}`
}

export function getImageDataUrl(base64String: string | null | undefined): string | undefined {
  if (!base64String) return undefined
  if (base64String.startsWith('data:') || base64String.startsWith('http')) return base64String
  return `data:image/png;base64,${base64String}`
}

const fetchBlobByUrl = async (url: string): Promise<Blob | null> => {
  const service = httpRequest({})
  return await service.get<unknown, Blob>(url, { responseType: 'blob' })
}

export async function fetchImageAsDataUrl(url: string): Promise<string | undefined> {
  try {
    const blob = await fetchBlobByUrl(url)
    if (!blob) return undefined
    return await new Promise<string | undefined>((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => resolve(reader.result as string | undefined)
      reader.onerror = () => reject(reader.error)
      reader.readAsDataURL(blob)
    })
  } catch {
    return undefined
  }
}
