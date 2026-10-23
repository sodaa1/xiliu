import { NavLink, useLocation } from 'react-router-dom'
import {
  BookOpen,
  House,
  Inbox,
  MessageSquare,
  Newspaper,
  Settings,
  CalendarCheck2,
  CircleHelp,
} from 'lucide-react'
import { Brand } from './Brand'

import { HomeThemeSwitch } from '../features/today/HomeThemeSwitch'
import { startGuide } from '../features/onboarding/progress'
import { AccountControl } from '../features/auth/AccountControl'
import { isCloud } from '../lib/runtime-mode'

export function WorkspaceControls() {
  const location = useLocation()
  if (location.pathname !== '/today' && !isCloud) return null
  return (
    <div className="workspace-controls">
      <div className="workspace-controls-inner">
        {location.pathname === '/today' && <HomeThemeSwitch />}
        {isCloud && <AccountControl />}
      </div>
    </div>
  )
}
const navigation = [
  { path: '/today', label: '今日', icon: House },
  { path: '/assistant', label: '助手', icon: MessageSquare },
  { path: '/feed', label: '资讯', icon: Newspaper },
  { path: '/inbox', label: '收件箱', icon: Inbox },
  { path: '/knowledge', label: '知识库', icon: BookOpen },
  { path: '/plans', label: '个人计划', icon: CalendarCheck2 },
]
export function WorkspaceSidebar({ inert = false }: { inert?: boolean }) {
  const location = useLocation()
  const background =
    location.pathname === '/settings'
      ? (location.state?.backgroundLocation ?? { pathname: '/today' })
      : location
  return (
    <aside
      inert={inert || undefined}
      className="global-sidebar workspace-sidebar icon-only-sidebar"
    >
      <NavLink className="brand" to="/assistant" aria-label="xiliu 助手" title="xiliu">
        <Brand />
      </NavLink>
      <nav aria-label="主导航" id="main-navigation">
        {navigation.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            aria-label={label}
            title={label}
            data-onboarding={`nav-${path.slice(1)}`}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={21} />
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <button
          type="button"
          className="nav-item"
          aria-label="重新查看新手引导"
          title="新手引导"
          data-onboarding="help-entry"
          onClick={startGuide}
        >
          <CircleHelp size={20} />
        </button>
        <NavLink
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          to="/settings"
          state={{ backgroundLocation: background }}
          aria-label="设置"
          title="设置"
        >
          <Settings size={20} />
        </NavLink>
      </div>
    </aside>
  )
}
