import type { ComponentType } from 'react'
declare const PillNav: ComponentType<{
  logo: string
  logoAlt?: string
  items: { label: string; href: string; ariaLabel?: string }[]
  activeHref?: string
  className?: string
  ease?: string
  baseColor?: string
  pillColor?: string
  hoveredPillTextColor?: string
  pillTextColor?: string
  initialLoadAnimation?: boolean
}>
export default PillNav
