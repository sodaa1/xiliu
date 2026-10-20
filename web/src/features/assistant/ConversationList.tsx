import { useState, type CSSProperties } from 'react'
import { ResizeHandle } from '../../components/ResizeHandle'
import { usePanelSize } from '../../lib/usePanelSize'
import '../../styles/resizable-panels.css'
import { MessageSquare, MoreHorizontal, Plus, Trash2, Search } from 'lucide-react'
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
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'today' | 'week'>('all')
  const visible = items.filter(
    (item) =>
      item.title.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()) &&
      (filter === 'all' ||
        (filter === 'today'
          ? new Date(item.updated_at).toDateString() === new Date().toDateString()
          : Date.now() - new Date(item.updated_at).getTime() < 7 * 86400000))
  )
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
      <div className="conversation-heading">
        <h2>对话</h2>
        <button className="new-chat" aria-label="创建新对话" onClick={onCreate} disabled={creating}>
          <Plus size={20} />
          <span className="sr-only">新建对话</span>
        </button>
      </div>
      <label className="conversation-search">
        <Search size={16} />
        <input
          type="search"
          aria-label="搜索对话"
          placeholder="搜索对话…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <div className="conversation-filters" role="group" aria-label="筛选对话">
        {(
          [
            ['all', '全部'],
            ['today', '今天'],
            ['week', '最近 7 天'],
          ] as const
        ).map(([value, label]) => (
          <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>
            {label}
          </button>
        ))}
      </div>
      <div className="conversation-scroll">
        {['今日', '昨日', '更早'].map((label) => {
          const rows = visible.filter((conversation) => group(conversation.updated_at) === label)
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
                    aria-label={conversation.title}
                    onClick={() => {
                      setMenu(null)
                      onSelect(conversation.id)
                    }}
                  >
                    <MessageSquare size={17} />
                    <span>
                      {conversation.title}
                      <small>{conversation.model_override || '息流对话'}</small>
                    </span>
                    <time dateTime={conversation.updated_at}>
                      {new Date(conversation.updated_at).toLocaleTimeString('zh-CN', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </time>
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
        {!visible.length && items.length > 0 && <p className="list-empty">没有找到匹配的对话。</p>}
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
