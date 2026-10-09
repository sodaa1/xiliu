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
} from 'lucide-react'
import { safeHttpUrl, workspaceApi, type FeedItem } from '../../lib/workspace-api'
import { useAskAI } from '../content/useAskAI'

export function FeedCard({ item }: { item: FeedItem }) {
  const cache = useQueryClient(),
    ask = useAskAI()
  const save = useMutation({
    mutationFn: () => workspaceApi.saveFeed(item.id),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['content'] })
      void cache.invalidateQueries({ queryKey: ['content-tags'] })
      void cache.invalidateQueries({ queryKey: ['today'] })
      void cache.invalidateQueries({ queryKey: ['data-settings'] })
    },
  })
  const url = safeHttpUrl(item.url),
    Icon = item.source === 'github' ? Github : Newspaper
  return (
    <article className="feed-card">
      <div className="feed-card-top">
        <span className={`item-symbol ${item.source}`}>
          <Icon size={22} />
        </span>
        <div>
          <span className="feed-source">
            {item.source === 'github' ? 'GitHub Top 5' : 'AI Hot'}
          </span>
          <h2>{item.title}</h2>
        </div>
      </div>
      <p>{item.summary || '打开原文，看看这条新发现。'}</p>
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
              Read
              <ArrowUpRight size={14} />
            </a>
          )}
          <button disabled={save.isPending || save.isSuccess} onClick={() => save.mutate()}>
            {save.isSuccess ? <Check size={14} /> : <BookmarkPlus size={14} />}
            {save.isSuccess ? '已收进 Inbox' : 'Save'}
          </button>
          <button
            disabled={ask.isPending}
            onClick={() =>
              ask.mutate({
                draft: '请解读这条资讯，说明它值得关注的地方。',
                reference: { title: item.title, content: `${item.summary}\n\n来源：${item.url}` },
              })
            }
          >
            <Sparkles size={14} />
            Ask AI
          </button>
        </div>
      </div>
      {(save.error || ask.error) && (
        <p className="workspace-error" role="alert">
          {(save.error || ask.error)!.message}
        </p>
      )}
    </article>
  )
}
export function FeedPage() {
  const cache = useQueryClient(),
    [source, setSource] = useState(''),
    [q, setQ] = useState('')
  const feed = useQuery({
    queryKey: ['feed', source, q],
    queryFn: () => workspaceApi.feed(source, q),
  })
  const refresh = useMutation({
    mutationFn: workspaceApi.refreshFeed,
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['feed'] })
      void cache.invalidateQueries({ queryKey: ['today'] })
    },
  })
  return (
    <section className="workspace-page feed-page">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">信息汇聚，思路生长</span>
          <h1>Feed</h1>
          <p>AI 与开源世界的新发现。</p>
        </div>
        <button
          className="secondary-button"
          disabled={refresh.isPending}
          onClick={() => refresh.mutate()}
        >
          <RefreshCw size={16} className={refresh.isPending ? 'spinning' : ''} />
          {refresh.isPending ? '更新中…' : '刷新资讯'}
        </button>
      </header>
      <div className="workspace-toolbar">
        <div className="segmented" aria-label="资讯来源">
          {[
            ['', '全部'],
            ['aihot', 'AI Hot'],
            ['github', 'GitHub Top 5'],
          ].map(([value, label]) => (
            <button
              key={value}
              className={value === source ? 'selected' : ''}
              aria-pressed={value === source}
              onClick={() => setSource(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="search-field">
          <Search size={17} />
          <input
            aria-label="搜索资讯"
            placeholder="搜索你关心的内容"
            value={q}
            onChange={(event) => setQ(event.target.value)}
          />
        </div>
      </div>
      {!!feed.data?.sources.length && (
        <div className="source-statuses">
          {feed.data.sources
            .filter((item) => !source || item.source === source)
            .map((item) => (
              <div key={item.source} className="source-status">
                <strong>{item.label}</strong>
                <span>
                  {item.message ||
                    (item.status === 'ok' || item.status === 'success'
                      ? '已更新'
                      : item.status === 'empty'
                        ? '暂时没有新内容'
                        : '暂时无法更新，请稍后重试')}
                </span>
                {item.updated_at && (
                  <time dateTime={item.updated_at}>
                    {new Date(item.updated_at).toLocaleTimeString('zh-CN', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </time>
                )}
              </div>
            ))}
        </div>
      )}
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
        <div className="feed-grid">
          {feed.data.items.map((item) => (
            <FeedCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  )
}
