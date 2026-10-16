import { useState, type CSSProperties } from 'react'
import { ResizeHandle } from '../../components/ResizeHandle'
import { usePanelSize } from '../../lib/usePanelSize'
import '../../styles/resizable-panels.css'
import { MessageSquare, MoreHorizontal, Plus, Trash2 } from 'lucide-react'
import type { Conversation } from '../../lib/types'

function group(created: string) {
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  const date = new Date(created).toDateString()
  return date === today.toDateString()
    ? '今日'
    : date === yesterday.toDateString()
      ? '昨日'
      : '更早'
}
export function ConversationList({
  items,
  selected,
  creating,
  busyIds,
  onCreate,
  onSelect,
  onDelete,
}: {
  items: Conversation[]
  selected?: string
  creating: boolean
  busyIds: string[]
  onCreate: () => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}) {
  const [menu, setMenu] = useState<string | null>(null)
  const maximum =
    window.innerWidth >= 1700
      ? 290
      : window.innerWidth <= 900
        ? 205
        : window.innerWidth <= 1200
          ? 225
          : 266
  const [width, setWidth] = usePanelSize('xiliu-conversation-width', 160, maximum)
  return (
    <aside
      className="conversation-sidebar"
      aria-label="对话列表"
      style={{ '--panel-width': `${width}px` } as CSSProperties}
    >
      <ResizeHandle
        label="调整对话侧栏宽度"
        value={width}
        min={160}
        max={maximum}
        onChange={setWidth}
      />
      <button className="new-chat" aria-label="创建新对话" onClick={onCreate} disabled={creating}>
        <Plus size={20} />
        <span>新建对话</span>
      </button>
      <div className="conversation-scroll">
        {['今日', '昨日', '更早'].map((label) => {
          const rows = items.filter((conversation) => group(conversation.created_at) === label)
          if (!rows.length) return null
          return (
            <section className="conversation-group" key={label}>
              <h2>{label}</h2>
              {rows.map((conversation) => (
                <div
                  className={`conversation-row ${selected === conversation.id ? 'selected' : ''}`}
                  key={conversation.id}
                >
                  <button
                    className="conversation-select"
                    onClick={() => {
                      setMenu(null)
                      onSelect(conversation.id)
                    }}
                  >
                    <MessageSquare size={17} />
                    <span>{conversation.title}</span>
                  </button>
                  <button
                    className="icon-button conversation-more"
                    aria-label={`对话操作：${conversation.title}`}
                    aria-expanded={menu === conversation.id}
                    onClick={() => setMenu(menu === conversation.id ? null : conversation.id)}
                  >
                    <MoreHorizontal size={16} />
                  </button>
                  {menu === conversation.id && (
                    <div className="conversation-menu">
                      <button
                        disabled={busyIds.includes(conversation.id)}
                        onClick={() => {
                          setMenu(null)
                          onDelete(conversation.id)
                        }}
                      >
                        <Trash2 size={15} />
                        删除对话
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </section>
          )
        })}
        {!items.length && (
          <p className="list-empty">
            思路从一段对话开始。
            <br />
            新建你的第一段对话。
          </p>
        )}
      </div>
      <div className="conversation-footnote">每一段思路，都有自己的位置。</div>
    </aside>
  )
}
