import type { OfflinerDefinitionFlag, OfflinerDefinitionSpec } from '@/types/zimfarm/offliner'

/**
 * Maps ZIM metadata names (as they appear in the offliner definition spec's
 * `zimMetadata[].metadata` field) to CMS title field keys.
 */
export const ZIM_METADATA_TO_CMS_FIELD: Record<string, string> = {
  Title: 'title',
  Creator: 'creator',
  Publisher: 'publisher',
  License: 'license',
  Language: 'language',
  Illustration: 'illustration_48x48_at_1',
  Description: 'description',
  LongDescription: 'long_description',
  Relation: 'relation',
  Source: 'source',
}

/**
 * Extract CMS title metadata values from the recipe's offliner config.
 *
 * Given the offliner's definition flag, definition spec, and the recipe's
 * `config.offliner` flags object, resolves each ZIM metadata field to a CMS
 * field key and extracts the corresponding value.
 */
export function extractRecipeMetadataValues(
  defFlag: OfflinerDefinitionFlag,
  defSpec: OfflinerDefinitionSpec,
  offlinerConfig: Record<string, unknown>,
): Record<string, string | null> {
  const result: Record<string, string | null> = {}

  for (const zimMeta of defSpec.schema.zimMetadata) {
    const cmsField = ZIM_METADATA_TO_CMS_FIELD[zimMeta.metadata]
    if (!cmsField) continue

    const flag = defFlag.flags.find((f) => f.key === zimMeta.flag)
    if (!flag) continue

    const rawValue = offlinerConfig[flag.data_key]
    result[cmsField] = rawValue !== undefined && rawValue !== null ? String(rawValue) : null
  }

  return result
}
