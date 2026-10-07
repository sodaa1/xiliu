import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Brand } from '../../components/Brand'
import type { Message } from '../../lib/types'

export function MessageList({messages,status,loading,onPrompt}: {messages:Message[];status?:string;loading:boolean;onPrompt:(text:string)=>void}) {
  const bottom = useRef<HTMLDivElement>(null)
  useEffect(() => {bottom.current?.scrollIntoView({behavior:'smooth',block:'end'})}, [messages,status])
  return <div className="messages-scroll" aria-label="对话内容">
    {loading ? <div className="loading-copy">正在加载对话…</div> : !messages.length ? <div className="assistant-welcome"><Brand large/><span className="eyebrow">ASK XILIU</span><h2>让信息流动，让思路清晰。</h2><p>一个问题、一段想法，或一件想一起完成的事。</p><div className="prompt-suggestions">{['帮我整理一个思路','解释一个概念','制定今日计划'].map((text) => <button key={text} onClick={() => onPrompt(text)}>{text}</button>)}</div></div> : <div className="messages-inner">{messages.map((message) => message.role === 'event' ? <div className="context-event" key={message.id}><span>{message.content === 'Context cleared' ? '已清除上下文' : message.content === 'Context compressed' ? '已压缩上下文' : message.content}</span></div> : <article className={`message message-${message.role}`} key={message.id}>
      {message.role === 'assistant' && <div className="message-avatar"><Brand/></div>}<div className="message-content"><ReactMarkdown remarkPlugins={[remarkGfm]} components={{a:({children,...props}) => <a {...props} target="_blank" rel="noopener noreferrer">{children}</a>}}>{message.content}</ReactMarkdown></div>
    </article>)}</div>}
    {status && <div className="run-status" role="status"><span className="status-pulse"/>{status}</div>}<div ref={bottom}/>
  </div>
}
