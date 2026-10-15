import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Inbox, MessageSquare, Sparkles } from 'lucide-react'
import { CaptureDialog } from '../content/CaptureDialog'
import { useQueryClient } from '@tanstack/react-query'
import { companionCall } from '../../desktop/companion'
import { isDesktop } from '../../desktop/bridge'
import './companion.css'

export function TodayCompanion() {
  const cache = useQueryClient()
  const [capture, setCapture] = useState(false)
  const [error, setError] = useState('')
  return (
    <>
      <section className="today-companion" aria-label="息流伴侣">
        <div className="today-companion-copy">
          <span className="eyebrow">
            <Sparkles size={14} /> 息流，陪你把想法向前推进
          </span>
          <h2>让灵感，有处安放。</h2>
          <p>聊聊正在想的事，或先收下值得留住的内容。</p>
          <div className="today-companion-actions">
            <Link className="primary-button" to="/assistant">
              <MessageSquare size={16} />
              开始对话
            </Link>
            <button
              className="secondary-button"
              onClick={() => {
                if (isDesktop())
                  void companionCall('open_capture').catch((error: Error) =>
                    setError(error.message)
                  )
                else setCapture(true)
              }}
            >
              <Inbox size={16} />
              收进 Inbox
            </button>
            {isDesktop() && (
              <button
                className="companion-text-button"
                onClick={() =>
                  void companionCall('show').catch((error: Error) => setError(error.message))
                }
              >
                唤出桌宠
              </button>
            )}
          </div>
          {error && (
            <p role="alert" className="workspace-error">
              {error}
            </p>
          )}
        </div>
        <div className="today-companion-portrait" aria-hidden="true">
          <img src="/companion/standing.png" alt="" width="1024" height="1536" />
        </div>
      </section>
      {capture && (
        <CaptureDialog
          onClose={() => setCapture(false)}
          onSaved={() => {
            setCapture(false)
            void cache.invalidateQueries({ queryKey: ['today'] })
            void cache.invalidateQueries({ queryKey: ['content'] })
          }}
        />
      )}
    </>
  )
}
