import constants from '@/constants'

export type Role = (typeof constants.ROLES)[number]

export const COLLECTION_SCOPED_ROLES = constants.COLLECTION_SCOPED_ROLES

export const isCollectionScopedRole = (role: string | null | undefined): boolean =>
  role != null && (COLLECTION_SCOPED_ROLES as readonly string[]).includes(role)
