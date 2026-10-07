import { useState } from 'react'
import { MessageSquare, MoreHorizontal, Plus, Trash2 } from 'lucide-react'
import type { Conversation } from '../../lib/types'

function group(created: string) {
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  const date = new Date(created).toDateString()
  return date === today.toDateString()
    ? 'Today'
    : date === yesterday.toDateString()
      ? 'Yesterday'
      : 'Earlier'
}
export function ConversationList({
  items,
  selected,
  creating,
  busy,
  onCreate,
  onSelect,
  onDelete,
}: {
  items: Conversation[]
  selected?: string
  creating: boolean
  busy: boolean
  onCreate: () => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}) {
  const [menu, setMenu] = useState<string | null>(null)
  return (
    <aside className="conversation-sidebar" aria-label="对话列表">
      <button
        className="new-chat"
        aria-label="新建 New Chat"
        onClick={onCreate}
        disabled={creating}
      >
        <Plus size={20} />
        <span>New Chat</span>
      </button>
      <div className="conversation-scroll">
        {['Today', 'Yesterday', 'Earlier'].map((label) => {
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
                        disabled={busy}
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
