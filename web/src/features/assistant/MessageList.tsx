import { FileText, BookOpen, CalendarCheck2, Blocks } from 'lucide-react'
import { useReducedMotion } from '../../lib/useReducedMotion'
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
  const reduced = useReducedMotion()
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'end' })
  }, [messages, run?.status, reduced])
  return (
    <div className="messages-scroll" aria-label="对话内容">
      {loading ? (
        <div className="loading-copy">正在加载对话…</div>
      ) : !messages.length ? (
        <div className="assistant-welcome">
          <div className="assistant-welcome-heading">
            <Brand large />
            <div>
              <h2>息流 AI 助手</h2>
              <p>让信息流动，让思路清晰。</p>
            </div>
          </div>
          <div className="assistant-introduction">
            <div className="message-avatar">
              <Brand />
            </div>
            <div>
              <strong>你好，我是息流，很高兴和你一起思考。</strong>
              <p>梳理零散想法，理解手边的资料，把目标拆成可执行的下一步。</p>
              <p>从一个问题、一段想法，或一件想一起完成的事开始。</p>
            </div>
          </div>
          <div className="prompt-suggestions">
            {[
              {
                title: '梳理材料',
                detail: '提取要点，找到内容之间的联系',
                icon: FileText,
                draft: '请帮我整理以下材料，提取要点、结论和待确认的问题：\n\n',
              },
              {
                title: '知识问答',
                detail: '把问题说清楚，让理解更进一步',
                icon: BookOpen,
                draft: '请帮我解释一个概念，并结合具体例子说明：',
              },
              {
                title: '拆解计划',
                detail: '从一个目标，走到具体的行动',
                icon: CalendarCheck2,
                draft: '请帮我把以下目标拆成可以执行的计划：',
              },
              {
                title: '工具与连接',
                detail: '查看已经接入的工具与能力',
                icon: Blocks,
                draft: '/mcp ',
              },
            ].map(({ title, detail, icon: Icon, draft }) => (
              <button key={title} onClick={() => onPrompt(draft)}>
                <span className="suggestion-icon">
                  <Icon size={22} />
                </span>
                <strong>{title}</strong>
                <small>{detail}</small>
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
