export function generatePassword(
  length = 12,
  chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
) {
  const array = new Uint8Array(length)
  crypto.getRandomValues(array)
  return Array.from(array, (x) => chars[x % chars.length]).join('')
}
