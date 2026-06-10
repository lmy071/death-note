// Type definitions for the World Tree component

export interface PageInfo {
  label: string
  route: string
  desc: string
  /** Direct URL to open in new tab (e.g. PDF). Overrides route when present. */
  url?: string
}

export interface BranchNode {
  depth: number
  index: number
  children: BranchNode[]
  page: PageInfo | null
  lenRatio: number
  angleOffset: number
  curveWobble: number
  curveJitter: number
  thicknessBase: number
  leafSize: number
  branchId: number
  _maxLen: number
}

export interface HitArea {
  x: number
  y: number
  radius: number
  label: string
  desc: string
  route: string
  /** Direct URL to open in new tab (e.g. PDF). Overrides route when present. */
  url?: string
}
