import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Link } from 'react-router-dom'
import { Brand } from '../../components/Brand'
import type { ChatRun, Message, Thinking } from '../../lib/types'
import { ThinkingPanel } from './ThinkingPanel'
import { AppReceipts } from './AppReceipts'

function thinkingFor(message: Message): Thinking | undefined {
  try {
    const value = JSON.parse(message.metadata_json).thinking
    if (
      typeof value?.elapsed_ms === 'number' &&
      Array.isArray(value.steps) &&
      typeof value.reasoning === 'string'
    )
      return value
  } catch {
    /* Older messages may not have thinking metadata. */
  }
}

export function MessageList({
  messages,
  run,
  loading,
  onPrompt,
}: {
  messages: Message[]
  run?: ChatRun
  loading: boolean
  onPrompt: (text: string) => void
}) {
  const resolved = messages.flatMap((message) => {
    try {
      const receipts = JSON.parse(message.metadata_json).app_receipts
      return Array.isArray(receipts)
        ? receipts.filter((r) => r.confirmation_resolved).map((r) => String(r.confirmation_id))
        : []
    } catch {
      return []
    }
  })
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, run?.status])
  return (
    <div className="messages-scroll" aria-label="对话内容">
      {loading ? (
        <div className="loading-copy">正在加载对话…</div>
      ) : !messages.length ? (
        <div className="assistant-welcome">
          <Brand large />
          <span className="eyebrow">向息流提问</span>
          <h2>让信息流动，让思路清晰。</h2>
          <p>一个问题、一段想法，或一件想一起完成的事。</p>
          <div className="prompt-suggestions">
            {['帮我整理一个思路', '解释一个概念', '制定今日计划'].map((text) => (
              <button key={text} onClick={() => onPrompt(text)}>
                {text}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="messages-inner">
          {messages.map((message) =>
            message.role === 'event' ? (
              <div className="context-event" key={message.id}>
                <span>
                  {message.content === 'Context cleared'
                    ? '已清除上下文'
                    : message.content === 'Context compressed'
                      ? '已压缩上下文'
                      : message.content}
                </span>
              </div>
            ) : (
              <article className={`message message-${message.role}`} key={message.id}>
                {message.role === 'assistant' && (
                  <div className="message-avatar">
                    <Brand />
                  </div>
                )}
                <div className="message-content">
                  {message.role === 'assistant' && thinkingFor(message) && (
                    <ThinkingPanel thinking={thinkingFor(message)!} />
                  )}
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      a: ({ children, href, title }) =>
                        href?.startsWith('/knowledge?') ? (
                          <Link to={href} title={title}>
                            {children}
                          </Link>
                        ) : (
                          <a href={href} title={title} target="_blank" rel="noopener noreferrer">
                            {children}
                          </a>
                        ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  {message.role === 'assistant' && (
                    <AppReceipts
                      metadata={message.metadata_json}
                      sessionId={message.conversation_id}
                      resolved={resolved}
                    />
                  )}
                </div>
              </article>
            )
          )}
        </div>
      )}
      {run && (
        <div className="active-thinking">
          <ThinkingPanel
            startedAt={run.startedAt}
            thinking={{ elapsed_ms: 0, steps: run.steps, reasoning: run.reasoning }}
          />
          <div className="run-status" role="status">
            <span className="status-pulse" />
            {run.status}
          </div>
        </div>
      )}
      <div ref={bottom} />
    </div>
  )
}
