export interface DailyDownload {
  date: string
  downloads: number
}

export interface TitleFlavourDownloads {
  flavour: string
  recipe_id: string | null
  downloads: DailyDownload[]
}
