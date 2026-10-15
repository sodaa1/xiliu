import { useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { ArrowUp, Square, Command as CommandIcon } from 'lucide-react'
import type { Capability, Command } from '../../lib/types'
import { ResizeHandle } from '../../components/ResizeHandle'
import { usePanelSize } from '../../lib/usePanelSize'
import '../../styles/resizable-panels.css'

const fallback: Command[] = [
  { name: 'clear', description: '清除对话内容' },
  { name: 'compress', description: '压缩当前上下文' },
  { name: 'skill', description: '使用一个已安装技能' },
  { name: 'mcp', description: '使用一个已连接服务' },
]

// Older builds persisted the composer height under these keys, defaulting to the
// tallest size. Drop them once so the compact default applies for everyone.
try {
  localStorage.removeItem('xiliu-composer-height')
  localStorage.removeItem('xiliu-composer-height-v2')
} catch {
  /* Storage may be unavailable. */
}
export function Composer({
  text,
  onText,
  onSend,
  disabled,
  onStop,
  stopping,
  commands,
  skills,
  mcp,
  modelPicker,
}: {
  text: string
  onText: (text: string) => void
  onSend: () => void
  disabled: boolean
  onStop?: () => void
  stopping?: boolean
  commands?: Command[]
  skills?: Capability[]
  mcp?: Capability[]
  modelPicker?: ReactNode
}) {
  const [highlight, setHighlight] = useState(0),
    [dismissed, setDismissed] = useState(false)
  const [height, setHeight] = usePanelSize('xiliu-composer-height-v3', 40, 98, 40)
  const trimmed = text.trimStart(),
    match = /^\/(skill|mcp)\s+(\S*)$/.exec(trimmed)
  const entries = match
    ? (match[1] === 'skill' ? (skills ?? []) : (mcp ?? []))
        .filter((entry) => entry.name.startsWith(match[2]))
        .map((entry) => ({
          name: entry.name,
          description: entry.description,
          value: `/${match[1]} ${entry.name} `,
        }))
    : (commands ?? fallback)
        .filter((entry) => !trimmed.includes(' ') && `/${entry.name}`.startsWith(trimmed))
        .map((entry) => ({ ...entry, value: `/${entry.name} ` }))
  const open = trimmed.startsWith('/') && entries.length > 0 && !dismissed
  const chosen = highlight % Math.max(entries.length, 1)
  function complete(index: number) {
    onText(entries[index].value)
    setDismissed(!/^\/(skill|mcp)\s+$/.test(entries[index].value))
    setHighlight(0)
  }
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return
    if (open && ['ArrowDown', 'ArrowUp', 'Enter', 'Tab'].includes(event.key)) {
      event.preventDefault()
      if (event.key === 'ArrowDown') setHighlight((chosen + 1) % entries.length)
      else if (event.key === 'ArrowUp') setHighlight((chosen + entries.length - 1) % entries.length)
      else complete(chosen)
    } else if (event.key === 'Escape') setDismissed(true)
    else if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (!disabled && text.trim()) onSend()
    }
  }
  return (
    <div className="composer-area">
      <div className="composer-box">
        <ResizeHandle
          label="调整输入框高度"
          vertical
          value={height}
          min={40}
          max={98}
          onChange={setHeight}
        />
        {open && (
          <div id="slash-options" className="command-palette" role="listbox" aria-label="命令建议">
            {entries.map((entry, index) => (
              <button
                key={entry.name}
                role="option"
                id={`suggestion-${index}`}
                aria-selected={chosen === index}
                className={chosen === index ? 'highlighted' : ''}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => complete(index)}
              >
                <span>{match ? entry.name : `/${entry.name}`}</span>
                <small>{entry.description}</small>
              </button>
            ))}
          </div>
        )}
        <textarea
          aria-label="消息"
          placeholder="Ask anything…"
          value={text}
          disabled={disabled}
          onChange={(event) => {
            onText(event.target.value)
            setDismissed(false)
            setHighlight(0)
          }}
          onKeyDown={keyDown}
          rows={3}
          style={{ height }}
          aria-controls={open ? 'slash-options' : undefined}
          aria-activedescendant={open ? `suggestion-${chosen}` : undefined}
        />
        <div className="composer-toolbar">
          {modelPicker}
          <span className="composer-hint">
            <CommandIcon size={15} />
            <span>输入 / 查看快捷命令</span>
          </span>
          <button
            className="send-button"
            aria-label={onStop ? (stopping ? '正在停止回复' : '停止回复') : '发送消息'}
            title={onStop ? '停止回复' : '发送消息'}
            onClick={onStop ?? onSend}
            disabled={onStop ? stopping : disabled || !text.trim()}
          >
            {onStop ? <Square size={17} fill="currentColor" /> : <ArrowUp size={23} />}
          </button>
        </div>
      </div>
      <p className="composer-disclaimer">
        息流可能会出错，请核对重要信息。<span>Enter 发送 · Shift + Enter 换行</span>
      </p>
    </div>
  )
}
