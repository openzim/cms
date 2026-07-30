export interface OfflinerFlagSchema {
  data_key: string
  secret?: boolean
  description: string | null
  choices:
    | {
        title: string
        value: string
      }[]
    | null
  label: string
  key: string
  required: boolean
  type: string
  min: number | null
  max: number | null
  min_graphemes: number | null
  max_graphemes: number | null
  pattern: string | null
  kind: 'image' | 'illustration' | 'css' | 'html' | 'txt' | null
  allow_remote_url: boolean
}

export interface OfflinerDefinitionFlag {
  flags: OfflinerFlagSchema[]
  help: string
}

export interface ZimMetadata {
  metadata: string
  flag: string
}

export interface OfflinerDefinitionSchema {
  // not all fields of an offliner definition are included
  zimMetadata: ZimMetadata[]
}

export interface OfflinerDefinitionSpec {
  offliner: string
  version: string
  created_at: string
  schema: OfflinerDefinitionSchema
}
