export interface RequestedTaskLight {
  id: string
  status: string
  requested_by: string | null
  created_at: string
  zimfarm_link?: string | null
}
