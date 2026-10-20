import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Search, Sun } from 'lucide-react'
import { workspaceApi } from '../../lib/workspace-api'
import { useAskAI } from '../content/useAskAI'
import { ContentDialog } from '../content/ContentDialog'
import { isDemo } from '../../lib/runtime-mode'
import { DemoBar } from '../demo/DemoBar'
import { resetDemoExperience } from '../demo/reset'
import { PageToolbar, WorkspaceSidebar } from '../../components/WorkspaceChrome'
export function WorkbenchShell({ children, inert }: { children: ReactNode; inert: boolean }) {
  const location = useLocation(),
    navigate = useNavigate(),
    cache = useQueryClient(),
    ask = useAskAI()
  const [search, setSearch] = useState(''),
    [searchOpen, setSearchOpen] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const data = useQuery({ queryKey: ['today'], queryFn: workspaceApi.today })
  const contents = useQuery({
    queryKey: ['home-content', 'knowledge'],
    queryFn: () => workspaceApi.content('knowledge'),
    enabled: searchOpen,
  })
  const inbox = useQuery({
    queryKey: ['home-content', 'inbox'],
    queryFn: () => workspaceApi.content('inbox'),
    enabled: searchOpen,
  })
  const settingsState = {
    backgroundLocation: location.pathname === '/settings' ? { pathname: '/today' } : location,
  }
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        if (inert || document.querySelector('[role="dialog"][aria-modal="true"]')) return
        event.preventDefault()
        input.current?.focus()
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [inert])
  const query = search.trim().toLowerCase()
  const matches = [
    ...(data.data?.tasks ?? []).map((t) => ({
      id: 't' + t.id,
      title: t.title,
      kind: '任务',
      to: '/plans',
    })),
    ...(data.data?.feed ?? []).map((t) => ({
      id: 'f' + t.id,
      title: t.title,
      kind: '资讯',
      to: '/feed',
    })),
    ...[...(contents.data ?? []), ...(inbox.data ?? [])].map((t) => ({
      id: 'c' + t.id,
      title: t.title,
      kind: t.status === 'inbox' ? '收集' : '知识',
      to:
        t.status === 'inbox'
          ? `/inbox?item=${encodeURIComponent(t.id)}`
          : `/knowledge?folder=all&document=${encodeURIComponent(t.id)}`,
    })),
  ]
    .filter((t) => query && t.title.toLowerCase().includes(query))
    .slice(0, 12)
  return (
    <div className="app-shell workbench-shell">
      <WorkspaceSidebar inert={inert} />
      <main className="main-stage" inert={inert || undefined}>
        {isDemo && (
          <DemoBar
            onReset={async () => {
              await resetDemoExperience(cache)
              navigate('/today', { replace: true })
            }}
          />
        )}
        <header className="workbench-topbar">
          <form
            className="wb-global-search"
            onSubmit={(event) => {
              event.preventDefault()
              setSearchOpen(true)
            }}
          >
            <Search size={19} />
            <input
              ref={input}
              aria-label="搜索息流"
              placeholder="搜索笔记、资讯、任务，或向 AI 提问…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <kbd>⌘ K</kbd>
          </form>
          <div className="wb-top-actions">
            <PageToolbar />
            <Link
              to="/settings?section=automations"
              state={settingsState}
              className="wb-icon-button"
              aria-label="提醒与自动任务"
            >
              <Bell size={21} />
            </Link>
            <Link
              to="/settings?section=appearance"
              state={settingsState}
              className="wb-icon-button"
              aria-label="外观设置"
            >
              <Sun size={22} />
            </Link>
          </div>
        </header>
        {children}
      </main>
      {searchOpen && (
        <ContentDialog title="搜索息流" onClose={() => setSearchOpen(false)}>
          <form
            className="wb-search-dialog"
            onSubmit={(event) => {
              event.preventDefault()
              if (search.trim()) ask.mutate({ draft: search.trim() })
            }}
          >
            <label>
              搜索内容
              <input autoFocus value={search} onChange={(event) => setSearch(event.target.value)} />
            </label>
            <div className="wb-search-results">
              {matches.map((item) => (
                <Link key={item.id} to={item.to} onClick={() => setSearchOpen(false)}>
                  <span>{item.kind}</span>
                  {item.title}
                </Link>
              ))}
              {query && !matches.length && <p>没有匹配的内容，也可以交给助手一起想想。</p>}
            </div>
            {(contents.error || inbox.error) && (
              <p role="alert">部分资料暂时未能加载，已展示可用结果。</p>
            )}
            <button className="wb-button" disabled={!search.trim() || ask.isPending}>
              向 AI 提问
            </button>
            {ask.error && <p role="alert">{ask.error.message}</p>}
          </form>
        </ContentDialog>
      )}
    </div>
  )
}
