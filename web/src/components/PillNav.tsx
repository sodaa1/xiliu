import { useLocation, useNavigate } from 'react-router-dom'
import ReactBitsPillNav from './react-bits/PillNav'
import { usePreferences } from '../lib/preferences'
import './pill-nav-adapter.css'
const items = [
  { href: '/assistant', label: '助手' },
  { href: '/feed', label: '资讯' },
  { href: '/inbox', label: '收件箱' },
  { href: '/knowledge', label: '知识库' },
  { href: '/plans', label: '个人计划' },
  { href: '/settings', label: '设置' },
]
const logo =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"%3E%3Cpath fill="%237773e9" d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/%3E%3C/svg%3E'
export function PillNav() {
  const location = useLocation(),
    navigate = useNavigate(),
    preferences = usePreferences()
  return (
    <div
      className="today-shortcuts"
      onClickCapture={(event) => {
        const anchor = (event.target as HTMLElement).closest('a')
        if (anchor?.getAttribute('href') === '/settings') {
          event.preventDefault()
          navigate('/settings', {
            state: {
              backgroundLocation:
                location.pathname === '/settings'
                  ? (location.state?.backgroundLocation ?? { pathname: '/today' })
                  : location,
            },
          })
        }
      }}
    >
      <ReactBitsPillNav
        logo={logo}
        logoAlt="xiliu"
        items={items}
        activeHref={location.pathname}
        className="xiliu-pill-nav"
        ease="power2.easeOut"
        baseColor="var(--accent)"
        pillColor="var(--surface)"
        hoveredPillTextColor="#ffffff"
        pillTextColor="var(--text)"
        initialLoadAnimation={!preferences.reducedMotion}
      />
    </div>
  )
}
