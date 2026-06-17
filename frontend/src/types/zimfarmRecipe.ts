import type { TitleFlavour } from '@/types/title'

export interface ZimfarmRecipeLight {
  id: string
  name: string
}

export interface ZimfarmRecipe extends ZimfarmRecipeLight {
  title_id: string | null
  title_name: string | null
  flavours: TitleFlavour[]
  link: string
}

export interface ZimfarmRecipeUpdate {
  title_name: string
  flavours: string[]
  current_recipes: string[]
}
