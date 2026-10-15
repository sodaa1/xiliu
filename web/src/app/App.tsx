import { PlansPage } from '../features/plans/PlansPage'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useCallback, useMemo, useRef } from 'react'
import {
  BookOpen,
  House,
  Inbox,
  MessageSquare,
  Newspaper,
  Settings,
  CalendarCheck2,
} from 'lucide-react'
import { Brand } from '../components/Brand'
import { PillNav } from '../components/PillNav'
import { AssistantPage } from '../features/assistant/AssistantPage'
import { SettingsPage } from '../features/settings/SettingsPage'
import { ChatProvider } from '../features/assistant/ChatProvider'
import { ContentPage } from '../features/content/ContentPage'
import { KnowledgePage } from '../features/knowledge/KnowledgePage'
import { FeedPage } from '../features/feed/FeedPage'
import { TodayPage } from '../features/today/TodayPage'
import { Modal } from '../components/Modal'
import { useApplyPreferences } from '../lib/preferences'
import '../styles/preferences.css'
import { LaunchPage } from '../features/launch/LaunchPage'
import '../styles/workspace.css'
import '../styles/compact-workspace.css'
import '../styles/editorial-workspace.css'
import { useReducedMotion } from '../lib/useReducedMotion'
import { usePageTransition } from './usePageTransition'
import './page-transition.css'
import { CompanionController } from '../features/companion/CompanionController'
import { CompanionPage } from '../features/companion/CompanionPage'
import { CapturePage } from '../features/companion/CapturePage'

const navigation = [
  { path: '/today', label: 'Today', icon: House },
  { path: '/assistant', label: 'Assistant', icon: MessageSquare },
  { path: '/feed', label: 'Feed', icon: Newspaper },
  { path: '/inbox', label: 'Inbox', icon: Inbox },
  { path: '/knowledge', label: 'Knowledge', icon: BookOpen },
  { path: '/plans', label: '个人计划', icon: CalendarCheck2 },
]
export function App() {
  useApplyPreferences()
  const location = useLocation()
  if (location.pathname.startsWith('/desktop/'))
    return (
      <Routes>
        <Route path="/desktop/companion" element={<CompanionPage />} />
        <Route path="/desktop/capture" element={<CapturePage />} />
        <Route path="*" element={<Navigate to="/today" replace />} />
      </Routes>
    )
  return (
    <ChatProvider>
      <CompanionController />
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
  const capturedItem = new URLSearchParams(displayed.search).get('item')
  const closeTarget =
    typeof backgroundUrl === 'string'
      ? backgroundUrl
      : backgroundUrl.pathname + backgroundUrl.search + backgroundUrl.hash
  const closeSettings = useCallback(
    () => navigate(closeTarget, { replace: true }),
    [navigate, closeTarget]
  )
  return (
    <div className="route-surface" ref={transitionRoot} data-route-path={displayed.pathname}>
      {displayed.pathname === '/' ? (
        <LaunchPage />
      ) : (
        <div className="app-shell">
          <aside inert={isSettings || undefined} className="global-sidebar icon-rail">
            <NavLink className="brand" to="/assistant" aria-label="xiliu Assistant" title="xiliu">
              <Brand />
            </NavLink>
            <nav aria-label="主导航" id="main-navigation">
              {navigation.map(({ path, label, icon: Icon }) => (
                <NavLink
                  key={path}
                  to={path}
                  aria-label={label}
                  title={label}
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                >
                  <Icon size={21} />
                </NavLink>
              ))}
            </nav>
            <div className="sidebar-bottom">
              <NavLink
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                to="/settings"
                state={{ backgroundLocation: isSettings ? backgroundUrl : location }}
                aria-label="Settings"
                title="Settings"
              >
                <Settings size={20} />
              </NavLink>
            </div>
          </aside>
          <main className="main-stage" inert={isSettings || undefined}>
            <div className="global-topbar">
              <PillNav />
            </div>
            <Routes location={displayed}>
              <Route path="/assistant" element={<AssistantPage />} />
              <Route path="/today" element={<TodayPage />} />
              <Route path="/plans" element={<PlansPage />} />
              <Route path="/feed" element={<FeedPage />} />
              <Route
                path="/inbox"
                element={
                  <ContentPage
                    key={`inbox:${capturedItem ?? ''}`}
                    status="inbox"
                    documentId={capturedItem ?? undefined}
                  />
                }
              />
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
