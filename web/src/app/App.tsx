import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useCallback, useMemo, useRef, useState, type CSSProperties } from 'react'
import {
  BookOpen,
  House,
  Inbox,
  MessageSquare,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Sparkles,
} from 'lucide-react'
import { Brand } from '../components/Brand'
import { AssistantPage } from '../features/assistant/AssistantPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { ChatProvider } from '../features/assistant/ChatProvider'
import { ContentPage } from '../features/content/ContentPage'
import { KnowledgePage } from '../features/knowledge/KnowledgePage'
import { FeedPage } from '../features/feed/FeedPage'
import { TodayPage } from '../features/today/TodayPage'
import { Modal } from '../components/Modal'
import { useApplyPreferences } from '../lib/preferences'
import { persistDesktopSidebar } from '../desktop/bridge'
import '../styles/preferences.css'
import { LaunchPage } from '../features/launch/LaunchPage'
import '../styles/workspace.css'
import '../styles/compact-workspace.css'
import { useReducedMotion } from '../lib/useReducedMotion'
import { usePageTransition } from './usePageTransition'
import './page-transition.css'
import { ResizeHandle } from '../components/ResizeHandle'
import { usePanelSize } from '../lib/usePanelSize'
import '../styles/resizable-panels.css'

const navigation = [
  { path: '/today', label: 'Today', icon: House },
  { path: '/assistant', label: 'Assistant', icon: MessageSquare },
  { path: '/feed', label: 'Feed', icon: Newspaper },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/knowledge', label: 'Knowledge', icon: BookOpen },
]
export function App() {
  useApplyPreferences()
  return (
    <ChatProvider>
      <AppLayout />
    </ChatProvider>
  )
}
function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const isSettings = location.pathname === '/settings'
  const background = location.state?.backgroundLocation
  const backgroundUrl =
    background && background.pathname !== '/settings' && background.pathname !== '/'
      ? background
      : '/today'
  const target = useMemo(
    () =>
      isSettings
        ? typeof backgroundUrl === 'string'
          ? { ...location, pathname: backgroundUrl, search: '', hash: '' }
          : backgroundUrl
        : location,
    [isSettings, backgroundUrl, location]
  )
  const transitionRoot = useRef<HTMLDivElement>(null)
  const displayed = usePageTransition(target, transitionRoot, useReducedMotion())
  const closeTarget =
    typeof backgroundUrl === 'string'
      ? backgroundUrl
      : backgroundUrl.pathname + backgroundUrl.search + backgroundUrl.hash
  const closeSettings = useCallback(
    () => navigate(closeTarget, { replace: true }),
    [navigate, closeTarget]
  )
  const [collapsed, setCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('xiliu-sidebar-collapsed')
      return saved === null ? window.innerWidth <= 900 : saved === 'true'
    } catch {
      return window.innerWidth <= 900
    }
  })
  const sidebarMax = window.innerWidth >= 1700 ? 250 : window.innerWidth <= 1200 ? 190 : 224
  const [sidebarWidth, setSidebarWidth] = usePanelSize('xiliu-sidebar-width', 144, sidebarMax)
  return (
    <div className="route-surface" ref={transitionRoot} data-route-path={displayed.pathname}>
      {displayed.pathname === '/' ? (
        <LaunchPage />
      ) : (
        <div className="app-shell">
          <aside
            inert={isSettings || undefined}
            className={`global-sidebar ${collapsed ? 'collapsed' : ''}`}
            style={{ '--panel-width': `${sidebarWidth}px` } as CSSProperties}
            data-compact={sidebarWidth < 190}
          >
            {!collapsed && (
              <ResizeHandle
                label="调整主侧栏宽度"
                value={sidebarWidth}
                min={144}
                max={sidebarMax}
                onChange={setSidebarWidth}
              />
            )}
            <NavLink className="brand" to="/assistant" aria-label="xiliu Assistant">
              <Brand />
              <span>
                xiliu<small>息流 · 百川归海</small>
              </span>
            </NavLink>
            <button
              className="icon-button sidebar-toggle"
              aria-label={collapsed ? '展开侧栏' : '折叠侧栏'}
              aria-expanded={!collapsed}
              aria-controls="main-navigation"
              onClick={() => {
                setCollapsed(!collapsed)
                try {
                  localStorage.setItem('xiliu-sidebar-collapsed', String(!collapsed))
                  void persistDesktopSidebar(!collapsed).catch(() => {
                    /* Browser storage still preserves this window's selection. */
                  })
                } catch {
                  /* Storage may be unavailable. */
                }
              }}
            >
              {collapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
            </button>
            <nav aria-label="主导航" id="main-navigation">
              {navigation.map(({ path, label, icon: Icon }) => (
                <NavLink
                  key={path}
                  to={path}
                  aria-label={label}
                  title={collapsed ? label : undefined}
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                  <Icon size={21} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <NavLink
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                to="/settings"
                state={{ backgroundLocation: isSettings ? backgroundUrl : location }}
                aria-label="Settings"
                title={collapsed ? 'Settings' : undefined}
              >
                <Settings size={20} />
                <span>Settings</span>
              </NavLink>
              <div className="local-label">
                <Sparkles size={13} />
                <span>属于你的信息空间</span>
                <span className="version">v0.3</span>
              </div>
            </div>
          </aside>
          <main className="main-stage" inert={isSettings || undefined}>
            <Routes location={displayed}>
              <Route path="/assistant" element={<AssistantPage />} />
              <Route path="/today" element={<TodayPage />} />
              <Route path="/feed" element={<FeedPage />} />
              <Route path="/inbox" element={<ContentPage key="inbox" status="inbox" />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="*" element={<Navigate to="/assistant" replace />} />
            </Routes>
          </main>
          {isSettings && (
            <Modal title="设置" onClose={closeSettings} className="settings-dialog">
              <SettingsPage embedded />
            </Modal>
          )}
        </div>
      )}
    </div>
  )
}
