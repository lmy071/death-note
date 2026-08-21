export interface ActionMenuSvgIcon {
  paths: readonly string[]
  viewBox?: string
}

export type ActionMenuIcon = string | ActionMenuSvgIcon

export interface ActionMenuItem {
  icon: ActionMenuIcon
  name: string
  url: string
}
