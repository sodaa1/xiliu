import { useState, type ReactNode } from 'react'
import {
  LayoutGrid,
  List,
  CheckCircle2,
  AlertCircle,
  Clock3,
  Newspaper,
  Github,
  BookmarkPlus,
} from 'lucide-react'
import { ContentDialog } from '../content/ContentDialog'
import { ArtworkImage } from '../../components/ArtworkImage'
import { topicForContent } from '../../lib/artwork'
import { safeHttpUrl, type FeedItem, type SourceStatus } from '../../lib/workspace-api'
export type FeedPresentation = 'standard' | 'hero' | 'compact' | 'reader'
export function FeedCover({
  item,
  featured = false,
  placement = 'standard',
}: {
  item: FeedItem
  featured?: boolean
  placement?: FeedPresentation | 'preview' | 'home'
}) {
  const remote = [item.metadata.image_url, item.metadata.cover_image, item.metadata.thumbnail].find(
    (value) => typeof value === 'string' && safeHttpUrl(value)
  ) as string | undefined
  return (
    <ArtworkImage
      className="feed-cover"
      topic={topicForContent(item.title, item.tags, 'technology')}
      slot={`feed:${placement}:${featured ? 'featured' : 'card'}:${item.id}`}
      remote={remote}
      sizes={featured ? '(max-width: 760px) 90vw, 65vw' : '(max-width: 760px) 88px, 320px'}
      loading={featured ? 'eager' : 'lazy'}
      referrerPolicy="no-referrer"
    />
  )
}
export function FeedDiscovery({
  items,
  renderCard,
}: {
  items: FeedItem[]
  renderCard: (item: FeedItem, variant: FeedPresentation, onOpen?: () => void) => ReactNode
}) {
  const [tag, setTag] = useState('')
  const [view, setView] = useState<'list' | 'grid'>('grid')
  const [sort, setSort] = useState('newest')
  const [selected, setSelected] = useState<string | null>(null)
  const [opened, setOpened] = useState(false)
  const tags = [...new Set(items.flatMap((item) => item.tags))].slice(0, 8)
  const activeTag = tags.includes(tag) ? tag : ''
  const timestamp = (item: FeedItem) => Date.parse(item.published_at || item.created_at || '') || 0
  const visible = items
    .filter((item) => !activeTag || item.tags.includes(activeTag))
    .sort((a, b) => (sort === 'oldest' ? timestamp(a) - timestamp(b) : timestamp(b) - timestamp(a)))
  const focus = visible.find((item) => item.id === selected) ?? visible[0]
  const reading = opened && !!focus
  const layout = reading ? 'list' : view
  const open = (id: string) => {
    setSelected(id)
    setOpened(true)
  }
  return (
    <div
      className={`feed-reading-workspace feed-layout-${layout} ${reading ? 'has-selected-article' : ''}`}
    >
      <div className="feed-article-queue">
        <header className="feed-queue-heading">
          <h2>
            最新资讯 <small>{visible.length}</small>
          </h2>
          <div className="feed-view-controls">
            <div role="group" aria-label="资讯布局">
              <button
                aria-label="列表视图"
                aria-pressed={layout === 'list'}
                onClick={() => {
                  setOpened(false)
                  setView('list')
                }}
              >
                <List size={16} />
              </button>
              <button
                aria-label="卡片视图"
                aria-pressed={layout === 'grid'}
                onClick={() => {
                  setOpened(false)
                  setView('grid')
                }}
              >
                <LayoutGrid size={16} />
              </button>
            </div>
          </div>
        </header>
        <div className="feed-topic-tabs" role="group" aria-label="资讯话题">
          <button aria-pressed={!activeTag} onClick={() => setTag('')}>
            全部话题
          </button>
          {tags.map((value) => (
            <button key={value} aria-pressed={activeTag === value} onClick={() => setTag(value)}>
              {value}
            </button>
          ))}
        </div>
        <div className="feed-queue-sort">
          <span>{visible.length} 条资料</span>
          <select
            aria-label="资讯排序"
            value={sort}
            onChange={(event) => setSort(event.target.value)}
          >
            <option value="newest">最新优先</option>
            <option value="oldest">最早优先</option>
          </select>
        </div>
        <div className={`feed-continuous-list feed-view-${layout}`}>
          {!visible.length ? (
            <p className="workspace-empty">这个话题暂时没有内容。</p>
          ) : (
            visible.map((item) =>
              layout === 'grid' ? (
                <div key={item.id}>{renderCard(item, 'standard', () => open(item.id))}</div>
              ) : (
                <button
                  className={`feed-queue-row ${focus?.id === item.id ? 'is-current' : ''}`}
                  key={item.id}
                  aria-label={`阅读：${item.title}`}
                  aria-current={focus?.id === item.id ? 'true' : undefined}
                  onClick={() => open(item.id)}
                >
                  <span className="feed-queue-source">
                    {item.source === 'github'
                      ? 'GitHub 热门项目'
                      : item.source === 'manual'
                        ? '我的资讯'
                        : '人工智能热点'}
                    <time dateTime={item.published_at}>
                      {item.published_at
                        ? new Date(item.published_at).toLocaleDateString('zh-CN')
                        : ''}
                    </time>
                  </span>
                  <span className="feed-queue-title">{item.title}</span>
                  <span className="feed-queue-excerpt">{item.summary || '打开原文了解详情。'}</span>
                  <span className="feed-queue-tags">
                    {item.tags
                      .slice(0, 3)
                      .map((t) => '# ' + t)
                      .join('　')}
                  </span>
                </button>
              )
            )
          )}
        </div>
      </div>
      {reading && focus && (
        <section className="feed-article-pane" aria-label="资讯阅读">
          <div className="feed-pane-heading">
            <button className="secondary-button feed-reader-back" onClick={() => setOpened(false)}>
              返回资讯列表
            </button>
            <span>摘要与来源链接 · 未加载全文</span>
          </div>
          <div className="feed-reader-scroll" key={focus.id}>
            {renderCard(focus, 'reader')}
          </div>
        </section>
      )}
    </div>
  )
}
export function FeedSources({
  sources,
  onClose,
  onBrowse,
}: {
  sources: SourceStatus[]
  onClose: () => void
  onBrowse: (source: string) => void
}) {
  const names: Record<string, string> = {
    aihot: '人工智能热点',
    github: 'GitHub 热门项目',
    manual: '我的资讯',
  }
  return (
    <ContentDialog title="来源状态" onClose={onClose}>
      <div className="feed-sources-dialog">
        <p>查看已接入来源的实际更新状态。</p>
        {sources.map((item) => {
          const healthy = item.status === 'ok' || item.status === 'success'
          const HealthIcon = healthy ? CheckCircle2 : item.status === 'error' ? AlertCircle : Clock3
          const Icon =
            item.source === 'github' ? Github : item.source === 'manual' ? BookmarkPlus : Newspaper
          return (
            <section className="feed-source-status-row" key={item.source}>
              <span className="feed-source-status-icon">
                <Icon size={24} />
              </span>
              <div>
                <h3>{names[item.source] || item.label}</h3>
                <p>
                  {item.message ||
                    (item.status === 'ok' || item.status === 'success'
                      ? '已更新'
                      : '暂时没有新内容')}
                </p>
                {item.updated_at && (
                  <time>{new Date(item.updated_at).toLocaleString('zh-CN')}</time>
                )}
              </div>
              <span className={`feed-health health-${item.status}`}>
                <HealthIcon size={14} />
                {item.status === 'ok' || item.status === 'success'
                  ? '已更新'
                  : item.status === 'error'
                    ? '暂不可用'
                    : '待更新'}
              </span>
              <button className="secondary-button" onClick={() => onBrowse(item.source)}>
                浏览
              </button>
            </section>
          )
        })}
      </div>
    </ContentDialog>
  )
}
