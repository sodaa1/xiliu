import { FeedCover, FeedDiscovery, FeedSources, type FeedPresentation } from './FeedDiscovery'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpRight,
  Check,
  Github,
  Newspaper,
  RefreshCw,
  Search,
  Sparkles,
  BookmarkPlus,
  EyeOff,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
  Layers3,
} from 'lucide-react'
import { safeHttpUrl, workspaceApi, type FeedItem } from '../../lib/workspace-api'
import { useAskAI } from '../content/useAskAI'
import { ContentDialog } from '../content/ContentDialog'
import { isDemo } from '../../lib/runtime-mode'

function FeedEditor({ item, onClose }: { item?: FeedItem; onClose: () => void }) {
  const cache = useQueryClient()
  const [url, setUrl] = useState(item?.url ?? '')
  const [title, setTitle] = useState(item?.title ?? '')
  const [summary, setSummary] = useState(item?.summary ?? '')
  const [tags, setTags] = useState(item?.tags.join(', ') ?? '')
  const [fetchTitle, setFetchTitle] = useState(false)
  const [demoRevision] = useState(item?.demo_revision)
  const save = useMutation({
    mutationFn: () => {
      const body = {
        demo_revision: demoRevision,
        url,
        title,
        summary,
        tags: [
          ...new Set(
            tags
              .split(/[,，]/)
              .map((tag) => tag.trim())
              .filter(Boolean)
          ),
        ],
        fetch_title: fetchTitle,
      }
      return item ? workspaceApi.updateManualFeed(item.id, body) : workspaceApi.addManualFeed(body)
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['feed'] })
      void cache.invalidateQueries({ queryKey: ['today'] })
      onClose()
    },
  })
  return (
    <ContentDialog title={item ? '编辑资讯' : '添加资讯'} onClose={onClose}>
      <form
        className="feed-editor-form"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <label>
          资讯链接
          <input
            autoFocus
            required
            type="url"
            maxLength={2048}
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://"
          />
        </label>
        <label>
          资讯标题
          <input
            maxLength={500}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="留空则使用链接"
          />
        </label>
        <label>
          资讯摘要
          <textarea
            rows={3}
            maxLength={4000}
            value={summary}
            onChange={(event) => setSummary(event.target.value)}
          />
        </label>
        <label>
          资讯标签
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            placeholder="用逗号分隔"
          />
        </label>
        <label className="content-checkbox">
          <input
            type="checkbox"
            checked={fetchTitle}
            disabled={isDemo}
            onChange={(event) => setFetchTitle(event.target.checked)}
          />
          联网抓取网页标题
        </label>
        {isDemo && <p>演示版不联网抓取网页标题；请手动填写，留空将使用链接。</p>}
        <p>手动资讯会持续保留，删除后可以恢复。</p>
        {save.error && (
          <p className="workspace-error" role="alert">
            {save.error.message}
          </p>
        )}
        <div className="editor-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            取消
          </button>
          <button className="primary-button" disabled={save.isPending}>
            {save.isPending ? '保存中…' : '保存资讯'}
          </button>
        </div>
      </form>
    </ContentDialog>
  )
}

function FeedPreview({
  item,
  onClose,
  onAsk,
  onSave,
  saved,
  saving,
  saveError,
  saveDisabled,
  inline = false,
}: {
  item: FeedItem
  onClose: () => void
  onAsk: () => void
  onSave: () => void
  saved: boolean
  saving: boolean
  saveError: Error | null
  saveDisabled: boolean
  inline?: boolean
}) {
  const url = safeHttpUrl(item.url)
  const sourceLabel =
    item.source === 'manual'
      ? '我的资讯'
      : item.source === 'github'
        ? 'GitHub 热门项目'
        : '人工智能热点'
  const summarize = useMutation({ mutationFn: () => workspaceApi.summarizeFeed(item.id) })
  const detailed = summarize.data?.summary
  const reading = (
    <div className="feed-preview">
      <FeedCover item={item} featured placement="preview" />
      <div className="feed-preview-meta">
        <span className="feed-source">{sourceLabel}</span>
        {item.published_at && (
          <time dateTime={item.published_at}>
            {new Date(item.published_at).toLocaleDateString('zh-CN')}
          </time>
        )}
      </div>
      <p className="feed-preview-summary">
        {item.summary || '这条资讯暂无摘要，打开原文了解详情。'}
      </p>
      {detailed && (
        <div className="feed-preview-detail">
          <span className="feed-preview-detail-label">
            <Sparkles size={13} />
            AI 总结
          </span>
          <p>{detailed}</p>
        </div>
      )}
      {summarize.error && (
        <p className="workspace-error" role="alert">
          {summarize.error.message}
        </p>
      )}
      {saveError && (
        <p className="workspace-error" role="alert">
          {saveError.message}
        </p>
      )}
      {!!item.tags.length && (
        <div className="tag-list">
          {item.tags.map((tag) => (
            <span key={tag}># {tag}</span>
          ))}
        </div>
      )}
      <div className="editor-actions">
        {!detailed && (
          <button
            type="button"
            className="secondary-button"
            disabled={summarize.isPending}
            onClick={() => summarize.mutate()}
          >
            <Sparkles size={15} className={summarize.isPending ? 'spinning' : ''} />
            {summarize.isPending ? '生成中…' : 'AI 总结'}
          </button>
        )}
        <button type="button" className="secondary-button" disabled={saveDisabled} onClick={onSave}>
          {saved ? <Check size={15} /> : <BookmarkPlus size={15} />}
          {saved ? '已收进收件箱' : saving ? '保存中…' : '收进收件箱'}
        </button>
        <button type="button" className="secondary-button" onClick={onAsk}>
          <Sparkles size={15} />
          引用提问
        </button>
        {url && (
          <a className="primary-link" href={url} target="_blank" rel="noreferrer">
            阅读原文
            <ArrowUpRight size={16} />
          </a>
        )}
      </div>
    </div>
  )
  return inline ? (
    reading
  ) : (
    <ContentDialog title={item.title} onClose={onClose}>
      {reading}
    </ContentDialog>
  )
}

export function FeedCard({
  item,
  onEdit,
  variant = 'standard',
  onOpen,
}: {
  item: FeedItem
  onEdit?: () => void
  variant?: FeedPresentation
  onOpen?: () => void
}) {
  const cache = useQueryClient(),
    ask = useAskAI()
  const [preview, setPreview] = useState(false)
  const save = useMutation({
    mutationFn: () => workspaceApi.saveFeed(item.id),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['content'] })
      void cache.invalidateQueries({ queryKey: ['content-tags'] })
      void cache.invalidateQueries({ queryKey: ['today'] })
      void cache.invalidateQueries({ queryKey: ['data-settings'] })
    },
  })
  const visibility = useMutation({
    mutationFn: () =>
      item.source === 'manual'
        ? item.deleted_at
          ? workspaceApi.restoreManualFeed(item.id)
          : workspaceApi.removeManualFeed(item.id)
        : item.hidden
          ? workspaceApi.unhideExternalFeed(item.id)
          : workspaceApi.hideExternalFeed(item.id),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['feed'] })
      void cache.invalidateQueries({ queryKey: ['today'] })
    },
  })
  const removed = Boolean(item.hidden || item.deleted_at)
  const visibilityLabel =
    item.source === 'manual' ? (removed ? '恢复' : '删除') : removed ? '取消隐藏' : '隐藏'
  const url = safeHttpUrl(item.url),
    Icon = item.source === 'github' ? Github : Newspaper
  const askAI = () =>
    ask.mutate({
      draft: '请解读这条资讯，说明它值得关注的地方。',
      reference: {
        title: item.title,
        content: `以下仅为资讯摘要与来源链接，未加载全文。\n\n${item.summary}\n\n来源：${item.url}`,
      },
    })
  if (variant === 'reader')
    return (
      <article className="feed-reader-document">
        <div className="feed-document-actions">
          {item.source === 'manual' && onEdit && !removed && (
            <button className="secondary-button" aria-label={`编辑 ${item.title}`} onClick={onEdit}>
              <Pencil size={14} />
              编辑
            </button>
          )}
          <button
            className="secondary-button"
            disabled={visibility.isPending}
            aria-label={`${visibilityLabel} ${item.title}`}
            onClick={() => visibility.mutate()}
          >
            {removed ? <RotateCcw size={14} /> : <EyeOff size={14} />} {visibilityLabel}
          </button>
        </div>
        <h2>{item.title}</h2>
        <FeedPreview
          inline
          item={item}
          onClose={() => setPreview(false)}
          onAsk={askAI}
          onSave={() => save.mutate()}
          saved={save.isSuccess}
          saving={save.isPending}
          saveError={save.error}
          saveDisabled={removed || save.isPending || save.isSuccess}
        />
        {(ask.error || visibility.error) && (
          <p className="workspace-error" role="alert">
            {(ask.error || visibility.error)!.message}
          </p>
        )}
      </article>
    )
  return (
    <article
      className={`feed-card is-openable feed-card-${variant}`}
      onClick={(event) => {
        if ((event.target as HTMLElement).closest('button, a, input, label')) return
        if (onOpen) onOpen()
        else setPreview(true)
      }}
    >
      <FeedCover item={item} featured={variant === 'hero'} placement={variant} />
      <div className="feed-card-top">
        <span className={`item-symbol ${item.source}`}>
          <Icon size={22} />
        </span>
        <div>
          <span className="feed-source">
            {item.source === 'manual'
              ? '我的资讯'
              : item.source === 'github'
                ? 'GitHub 热门项目'
                : '人工智能热点'}
            {removed && (item.deleted_at ? ' · 已删除' : ' · 已隐藏')}
          </span>
          <h2>
            <button
              type="button"
              className="content-row-open"
              onClick={() => (onOpen ? onOpen() : setPreview(true))}
            >
              {item.title}
            </button>
          </h2>
        </div>
      </div>
      <p>{item.summary || '打开原文，看看这条新发现。'}</p>
      {item.metadata.fetch_status === 'failed' && <p role="status">网页标题未补齐，链接已保留。</p>}
      <div className="tag-list">
        {item.tags.map((tag) => (
          <span key={tag}># {tag}</span>
        ))}
      </div>
      <div className="feed-card-bottom">
        <time dateTime={item.published_at}>
          {item.published_at ? new Date(item.published_at).toLocaleDateString('zh-CN') : ''}
        </time>
        <div className="row-actions">
          {url && (
            <a href={url} target="_blank" rel="noreferrer">
              阅读原文
              <ArrowUpRight size={14} />
            </a>
          )}
          <button
            title={save.isSuccess ? '已收进收件箱' : '收藏'}
            disabled={removed || save.isPending || save.isSuccess}
            onClick={() => save.mutate()}
          >
            {save.isSuccess ? <Check size={14} /> : <BookmarkPlus size={14} />}
            {save.isSuccess ? '已收进收件箱' : '收藏'}
          </button>
          {item.source === 'manual' && onEdit && !removed && (
            <button title="编辑" aria-label={`编辑 ${item.title}`} onClick={onEdit}>
              <Pencil size={14} />
              编辑
            </button>
          )}
          <button
            disabled={visibility.isPending}
            title={visibilityLabel}
            aria-label={`${visibilityLabel} ${item.title}`}
            onClick={() => visibility.mutate()}
          >
            {removed ? (
              <RotateCcw size={14} />
            ) : item.source === 'manual' ? (
              <Trash2 size={14} />
            ) : (
              <EyeOff size={14} />
            )}
            {visibilityLabel}
          </button>
          <button title="引用提问" disabled={ask.isPending} onClick={askAI}>
            <Sparkles size={14} />
            引用提问
          </button>
        </div>
      </div>
      {(save.error || ask.error || visibility.error) && (
        <p className="workspace-error" role="alert">
          {(save.error || ask.error || visibility.error)!.message}
        </p>
      )}
      {preview && (
        <FeedPreview
          item={item}
          onClose={() => setPreview(false)}
          onAsk={() => {
            setPreview(false)
            askAI()
          }}
          onSave={() => save.mutate()}
          saved={save.isSuccess}
          saving={save.isPending}
          saveError={save.error}
          saveDisabled={removed || save.isPending || save.isSuccess}
        />
      )}
    </article>
  )
}
export function FeedPage() {
  const cache = useQueryClient(),
    [source, setSource] = useState(''),
    [q, setQ] = useState(''),
    [includeHidden, setIncludeHidden] = useState(false),
    [editor, setEditor] = useState<FeedItem | 'new' | null>(null),
    [sourcesOpen, setSourcesOpen] = useState(false)
  const feed = useQuery({
    queryKey: ['feed', source, q, includeHidden],
    queryFn: () => workspaceApi.feed(source, q, includeHidden),
  })
  const refresh = useMutation({
    mutationFn: workspaceApi.refreshFeed,
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['feed'] })
      void cache.invalidateQueries({ queryKey: ['today'] })
    },
  })
  return (
    <section className="workspace-page feed-page feed-workbench">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">信息汇聚，思路生长</span>
          <h1>资讯</h1>
          <p>从你关心的来源，发现值得阅读的内容。</p>
        </div>
        <label className="search-field feed-header-search">
          <Search size={17} />
          <input
            aria-label="搜索资讯"
            placeholder="搜索你关心的内容"
            value={q}
            onChange={(event) => setQ(event.target.value)}
          />
        </label>
        <div className="row-actions">
          <button className="secondary-button" onClick={() => setEditor('new')}>
            <Plus size={16} />
            添加资讯
          </button>
          <button
            className="secondary-button"
            disabled={refresh.isPending}
            onClick={() => refresh.mutate()}
          >
            <RefreshCw size={16} className={refresh.isPending ? 'spinning' : ''} />
            {refresh.isPending ? '更新中…' : '刷新资讯'}
          </button>
        </div>
      </header>
      {editor && (
        <FeedEditor item={editor === 'new' ? undefined : editor} onClose={() => setEditor(null)} />
      )}
      {sourcesOpen && (
        <FeedSources
          sources={feed.data?.sources ?? []}
          onClose={() => setSourcesOpen(false)}
          onBrowse={(value) => {
            setSource(value)
            setSourcesOpen(false)
          }}
        />
      )}
      <div className="feed-workspace">
        <aside className="feed-source-panel" aria-label="资讯来源与状态">
          <div className="segmented" aria-label="资讯来源">
            {[
              { value: '', label: '全部资讯', icon: Layers3 },
              { value: 'aihot', label: '人工智能热点', icon: Newspaper },
              { value: 'github', label: 'GitHub 热门项目', icon: Github },
              { value: 'manual', label: '我的资讯', icon: BookmarkPlus },
            ].map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                className={value === source ? 'selected' : ''}
                aria-pressed={value === source}
                onClick={() => setSource(value)}
              >
                <Icon size={17} aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>
          <label className="content-checkbox">
            <input
              type="checkbox"
              checked={includeHidden}
              onChange={(event) => setIncludeHidden(event.target.checked)}
            />
            显示已移除资讯
          </label>
          <button
            className="feed-source-manage"
            disabled={!feed.data?.sources.length}
            onClick={() => setSourcesOpen(true)}
          >
            来源状态
          </button>
        </aside>
        <section className="feed-reading" aria-label="资讯列表">
          {refresh.error && (
            <p className="workspace-error" role="alert">
              {refresh.error.message}
            </p>
          )}
          {feed.isLoading ? (
            <p className="workspace-empty">正在汇聚资讯…</p>
          ) : feed.error ? (
            <div className="workspace-empty">
              <p role="alert">{feed.error.message}</p>
              <button className="secondary-button" onClick={() => void feed.refetch()}>
                重新加载
              </button>
            </div>
          ) : !feed.data?.items.length ? (
            <div className="workspace-empty">
              <Newspaper size={32} />
              <h2>{q ? '没有找到相关资讯' : '等待下一次新发现'}</h2>
              <p>{q ? '换个关键词试试。' : '点击刷新，获取来源中的最新内容。'}</p>
            </div>
          ) : (
            <FeedDiscovery
              items={feed.data.items}
              renderCard={(item, variant, onOpen) => (
                <FeedCard
                  key={item.id}
                  item={item}
                  variant={variant}
                  onOpen={onOpen}
                  onEdit={() => setEditor(item)}
                />
              )}
            />
          )}
        </section>
      </div>
    </section>
  )
}
