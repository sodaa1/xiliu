import { PageToolbar } from '../../components/WorkspaceChrome'
import { useHomeTheme } from './home-theme'
import { WorkbenchHome } from './WorkbenchHome'
import { useHomeDraft } from './useHomeDraft'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowUp, Inbox, Plus } from 'lucide-react'
import { Avatar } from '../../components/Avatar'
import { usePreferences } from '../../lib/preferences'
import { useAskAI } from '../content/useAskAI'
import { CaptureDialog } from '../content/CaptureDialog'
import { useHomeBackground } from './useHomeBackground'
import { publicAsset } from '../../lib/deployment'
import './home.css'
export function TodayPage() {
  const theme = useHomeTheme()
  return theme === 'workbench' ? <WorkbenchHome /> : <OriginalHome />
}
function OriginalHome() {
  const location = useLocation(),
    preferences = usePreferences(),
    ask = useAskAI(),
    cache = useQueryClient()
  const [draft, setDraft] = useHomeDraft()
  const [capture, setCapture] = useState(false)
  const { url } = useHomeBackground()
  const hour = new Date().getHours()
  const greeting = hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'
  return (
    <section className="home-page" aria-label="主页" data-wallpaper={url ? 'true' : undefined}>
      {url && (
        <img
          key={url}
          className="home-wallpaper"
          src={url}
          alt=""
          onError={(event) => {
            event.currentTarget.hidden = true
          }}
        />
      )}
      <div className="original-home-toolbar">
        <PageToolbar />
      </div>
      <Link
        className="home-profile"
        to="/settings?section=profile"
        state={{ backgroundLocation: location }}
        aria-label={`${preferences.displayName || '你'}的个人设置`}
      >
        <Avatar />
      </Link>
      <div className="home-composition">
        <div className="home-copy">
          <header className="home-heading">
            <time className="home-date" dateTime={new Date().toISOString()}>
              {new Date().toLocaleDateString('zh-CN', {
                month: 'long',
                day: 'numeric',
                weekday: 'long',
              })}
            </time>
            <h1>
              {greeting}
              {preferences.displayName ? `，${preferences.displayName}` : ''}，<br />
              今天从容开始<span>。</span>
            </h1>
            <p className="home-subtitle">有什么想法，随时告诉我。</p>
          </header>
          <div className="home-composer-halo">
            <form
              className="home-composer"
              onSubmit={(event) => {
                event.preventDefault()
                if (draft.trim() && !ask.isPending) ask.mutate({ draft: draft.trim() })
              }}
            >
              <button
                type="button"
                className="home-attach"
                aria-label="导入文件或链接"
                title="导入文件或链接"
                onClick={() => setCapture(true)}
              >
                <Plus size={24} />
              </button>
              <input
                aria-label="问问息流"
                placeholder="聊点什么，或随手记下…"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                maxLength={20000}
                disabled={ask.isPending}
              />
              <button
                type="button"
                className="home-capture"
                aria-label="快速收录"
                title="快速收录到收件箱"
                onClick={() => setCapture(true)}
              >
                <Inbox size={23} />
              </button>
              <button
                className="home-send"
                aria-label="在助手中继续"
                title="开始对话"
                disabled={ask.isPending || !draft.trim()}
              >
                <ArrowUp size={25} />
              </button>
            </form>
          </div>
          {ask.error && (
            <p className="workspace-error" role="alert">
              {ask.error.message}
            </p>
          )}
        </div>
        <div className="home-character" aria-hidden="true">
          <img
            src={publicAsset('companion/standing.png')}
            alt=""
            draggable={false}
            width="1024"
            height="1536"
          />
        </div>
      </div>
      {capture && (
        <CaptureDialog
          initialText={draft}
          onClose={() => setCapture(false)}
          onSaved={() => {
            setCapture(false)
            void cache.invalidateQueries({ queryKey: ['content'] })
            void cache.invalidateQueries({ queryKey: ['inbox'] })
          }}
        />
      )}
    </section>
  )
}
