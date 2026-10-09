import { useEffect, useState } from 'react'
import type { Thinking } from '../../lib/types'

export function ThinkingPanel({ thinking, startedAt }: { thinking: Thinking; startedAt?: number }) {
  const [now, setNow] = useState(Date.now)
  useEffect(() => {
    if (startedAt === undefined) return
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [startedAt])
  const seconds = Math.floor(
    Math.max(0, startedAt === undefined ? thinking.elapsed_ms : now - startedAt) / 1000
  )
  return (
    <details className="thinking-panel">
      <summary>
        {startedAt === undefined ? '思考过程' : '思考中'} · {Math.floor(seconds / 60)}分
        {seconds % 60}秒
      </summary>
      <div className="thinking-content">
        {!!thinking.steps.length && (
          <ol>
            {thinking.steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>
        )}
        {thinking.reasoning && <pre>{thinking.reasoning}</pre>}
        {!thinking.reasoning && <p>这里显示处理步骤；模型返回思考内容时会同步显示。</p>}
      </div>
    </details>
  )
}
