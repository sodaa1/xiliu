import { useState, type ReactNode } from 'react'
import {
  LayoutGrid,
  List,
  Sparkles,
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
export type FeedPresentation = 'standard' | 'hero' | 'compact'
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
  renderCard: (item: FeedItem, variant: FeedPresentation) => ReactNode
}) {
  const [tag, setTag] = useState(''),
    [view, setView] = useState<'list' | 'grid'>('list'),
    [sort, setSort] = useState('newest'),
    [featured, setFeatured] = useState(0)
  const tags = [...new Set(items.flatMap((item) => item.tags))].slice(0, 8)
  const activeTag = tags.includes(tag) ? tag : ''
  const timestamp = (item: FeedItem) => Date.parse(item.published_at || item.created_at || '') || 0
  const visible = items
    .filter((item) => !activeTag || item.tags.includes(activeTag))
    .sort((a, b) => (sort === 'oldest' ? timestamp(a) - timestamp(b) : timestamp(b) - timestamp(a)))
  const candidates = visible.filter((item) => !item.deleted_at && !item.hidden).slice(0, 5)
  const hasFeature = candidates.length >= 3,
    focus = hasFeature ? candidates[featured % candidates.length] : null
  const remaining = focus ? visible.filter((item) => item.id !== focus.id) : visible
  return (
    <>
      {tags.length > 0 && (
        <div className="feed-topic-tabs" role="group" aria-label="资讯话题">
          <button aria-pressed={!activeTag} onClick={() => setTag('')}>
            全部话题
          </button>
          {tags.map((value) => (
            <button
              key={value}
              aria-pressed={activeTag === value}
              onClick={() => {
                setTag(value)
                setFeatured(0)
              }}
            >
              {value}
            </button>
          ))}
        </div>
      )}
      {focus && (
        <section className="feed-discovery-top" aria-label="焦点阅读">
          <div className="feed-featured">
            {renderCard(focus, 'hero')}
            <div className="feed-feature-pagination" role="group" aria-label="焦点资讯切换">
              {candidates.map((item, index) => (
                <button
                  key={item.id}
                  aria-label={`焦点阅读第 ${index + 1} 篇`}
                  aria-pressed={item.id === focus.id}
                  onClick={() => setFeatured(index)}
                />
              ))}
            </div>
          </div>
          <aside className="feed-picks" aria-label="本页精选">
            <header>
              <h2>
                <Sparkles size={18} />
                本页精选
              </h2>
              <span>{Math.min(4, remaining.length)} 篇</span>
            </header>
            {remaining
              .filter((item) => !item.deleted_at && !item.hidden)
              .slice(0, 4)
              .map((item) => (
                <div key={item.id}>{renderCard(item, 'compact')}</div>
              ))}
          </aside>
        </section>
      )}
      <header className="feed-library-heading">
        <div>
          <h2>最新资讯</h2>
          <p>{visible.length} 条内容，按自己的节奏阅读。</p>
        </div>
        <div className="feed-view-controls">
          <div role="group" aria-label="资讯布局">
            <button
              aria-label="列表视图"
              aria-pressed={view === 'list'}
              onClick={() => setView('list')}
            >
              <List size={18} />
            </button>
            <button
              aria-label="卡片视图"
              aria-pressed={view === 'grid'}
              onClick={() => setView('grid')}
            >
              <LayoutGrid size={18} />
            </button>
          </div>
          <select
            aria-label="资讯排序"
            value={sort}
            onChange={(event) => setSort(event.target.value)}
          >
            <option value="newest">最新优先</option>
            <option value="oldest">最早优先</option>
          </select>
        </div>
      </header>
      {!visible.length ? (
        <p className="workspace-empty">这个话题暂时没有内容。</p>
      ) : (
        <div className={`feed-grid feed-view-${view}`}>
          {visible.map((item) => (
            <div className="feed-card-wrap" key={item.id}>
              {renderCard(item, 'standard')}
            </div>
          ))}
        </div>
      )}
    </>
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
