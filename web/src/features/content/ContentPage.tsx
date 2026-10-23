import { ActionMenu } from '../../components/ActionMenu'
import { useState } from 'react'
import { CaptureDialog } from './CaptureDialog'
import { ContentDialog } from './ContentDialog'
import './content-knowledge.css'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BookOpen,
  FileText,
  Link2,
  Paperclip,
  Plus,
  Search,
  Pencil,
  Sparkles,
  Trash2,
  Download,
  ArrowRight,
  LayoutGrid,
  List,
} from 'lucide-react'
import { safeHttpUrl, workspaceApi, type ContentItem } from '../../lib/workspace-api'
import { useAskAI } from './useAskAI'
import { GlideSelect } from '../../components/GlideSelect'
import { Link } from 'react-router-dom'

const icons = { note: FileText, link: Link2, file: Paperclip }
const tagsFrom = (value: string) => [
  ...new Set(
    value
      .split(/[,，]/)
      .map((tag) => tag.trim())
      .filter(Boolean)
  ),
]

function ContentEditor({
  item,
  onClose,
  onSaved,
}: {
  item: ContentItem
  onClose: () => void
  onSaved: () => void
}) {
  const [title, setTitle] = useState(item.title),
    [demoRevision] = useState(item.demo_revision),
    [content, setContent] = useState(item.content),
    [summary, setSummary] = useState(item.summary),
    [tags, setTags] = useState(item.tags.join(', ')),
    [folder, setFolder] = useState(item.folder_id ?? '')
  const folders = useQuery({ queryKey: ['knowledge-folders'], queryFn: workspaceApi.folders })
  const save = useMutation({
    mutationFn: () =>
      workspaceApi.updateContent(item.id, {
        demo_revision: demoRevision,
        title,
        content,
        summary,
        tags: tagsFrom(tags),
        ...(folder !== (item.folder_id ?? '') ? { folder_id: folder || null } : {}),
      }),
    onSuccess: () => {
      onSaved()
      onClose()
    },
  })
  return (
    <form
      className="content-editor"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate()
      }}
    >
      <label>
        标题
        <input required value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        内容
        <textarea rows={7} value={content} onChange={(event) => setContent(event.target.value)} />
      </label>
      <label>
        摘要
        <textarea rows={3} value={summary} onChange={(event) => setSummary(event.target.value)} />
      </label>
      <label>
        标签
        <input
          value={tags}
          onChange={(event) => setTags(event.target.value)}
          placeholder="用逗号分隔"
        />
      </label>
      <label>
        文件夹
        <GlideSelect
          ariaLabel="文件夹"
          value={folder}
          onChange={setFolder}
          options={[
            { value: '', label: '未分类' },
            ...(folders.data ?? []).map((value) => ({ value: value.id, label: value.name })),
          ]}
        />
      </label>
      {folders.error && (
        <p role="alert" className="workspace-error">
          无法加载文件夹：{folders.error.message}
        </p>
      )}
      {save.error && (
        <p role="alert" className="workspace-error">
          {save.error.message}
        </p>
      )}
      <div className="editor-actions">
        <button type="button" className="secondary-button" onClick={onClose}>
          取消
        </button>
        <button className="primary-button" disabled={save.isPending}>
          {save.isPending ? '保存中…' : '保存修改'}
        </button>
      </div>
    </form>
  )
}

function ContentPreview({
  item,
  onClose,
  onEdit,
  onAsk,
  asking,
  standalone = false,
}: {
  item: ContentItem
  onClose: () => void
  onEdit: () => void
  onAsk: () => void
  asking: boolean
  standalone?: boolean
}) {
  const sourceUrl = safeHttpUrl(item.source)
  const body = item.content || item.summary || item.filename || item.source
  const reading = (
    <div className="content-reading">
      <aside className="content-reading-facts" aria-label="内容信息">
        <dl>
          <div>
            <dt>类型</dt>
            <dd>
              {item.type === 'link' ? '网页链接' : item.type === 'file' ? '文件' : '文字笔记'}
            </dd>
          </div>
          <div>
            <dt>收录时间</dt>
            <dd>{new Date(item.created_at).toLocaleDateString('zh-CN')}</dd>
          </div>
          <div>
            <dt>整理状态</dt>
            <dd>
              {item.processing_status === 'failed'
                ? '整理失败，原件已保留'
                : item.processing_status === 'pending'
                  ? '正在整理'
                  : item.ai_processed
                    ? 'AI 已整理'
                    : '本地整理'}
            </dd>
          </div>
        </dl>
      </aside>
      <div className="content-reading-main">
        <div className="feed-preview-meta">
          <span className="feed-source">
            {item.type === 'link' ? '链接' : item.type === 'file' ? '文件' : '笔记'}
          </span>
          <time dateTime={item.updated_at}>
            {new Date(item.updated_at).toLocaleDateString('zh-CN')}
          </time>
        </div>
        {item.summary && item.content && item.summary !== item.content && (
          <p className="feed-preview-summary">{item.summary}</p>
        )}
        <div className="content-preview-body">{body}</div>
        {sourceUrl && (
          <a className="source-link" href={sourceUrl} target="_blank" rel="noreferrer">
            {item.source}
          </a>
        )}
        {!!item.tags.length && (
          <div className="tag-list">
            {item.tags.map((tag) => (
              <span key={tag}># {tag}</span>
            ))}
          </div>
        )}
        <div className="editor-actions">
          <button type="button" className="secondary-button" onClick={onEdit}>
            <Pencil size={15} />
            编辑
          </button>
          <button type="button" className="secondary-button" disabled={asking} onClick={onAsk}>
            <Sparkles size={15} />
            引用提问
          </button>
          {item.filename && (
            <a
              className="secondary-button"
              href={workspaceApi.originalUrl(item.id)}
              download={item.filename}
            >
              <Download size={15} />
              下载原件
            </a>
          )}
          {sourceUrl && (
            <a className="primary-link" href={sourceUrl} target="_blank" rel="noreferrer">
              打开原文
              <ArrowRight size={16} />
            </a>
          )}
        </div>
      </div>
    </div>
  )
  return standalone ? (
    <section className="document-reading-page">
      <h2>{item.title}</h2>
      {reading}
    </section>
  ) : (
    <ContentDialog title={item.title} onClose={onClose} className="content-preview-compact">
      {reading}
    </ContentDialog>
  )
}

export function ContentPage({
  status,
  folderId,
  documentId,
}: {
  status: ContentItem['status']
  folderId?: string
  documentId?: string
}) {
  const cache = useQueryClient(),
    ask = useAskAI()
  const [q, setQ] = useState(''),
    [tag, setTag] = useState(''),
    [type, setType] = useState(''),
    [editing, setEditing] = useState<ContentItem | null>(null),
    [previewing, setPreviewing] = useState<ContentItem | null>(null),
    [notice, setNotice] = useState(''),
    [captureOpen, setCaptureOpen] = useState(false),
    [recentIds, setRecentIds] = useState<string[]>([]),
    [selected, setSelected] = useState<string[]>([]),
    [view, setView] = useState<'list' | 'grid'>(status === 'inbox' ? 'grid' : 'list')
  const folders = useQuery({ queryKey: ['knowledge-folders'], queryFn: workspaceApi.folders })
  const recent = useQuery({
    queryKey: ['recent-imports', recentIds],
    queryFn: () => Promise.all(recentIds.map(workspaceApi.contentItem)),
    enabled: recentIds.length > 0,
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.processing_status === 'pending') ? 1500 : false,
  })
  const list = useQuery({
    queryKey: ['content', status, folderId, documentId, q, tag],
    queryFn: () =>
      documentId
        ? workspaceApi.contentItem(documentId).then((item) => [item])
        : folderId && folderId !== 'unfiled'
          ? workspaceApi.folderItems(folderId)
          : status === 'inbox'
            ? workspaceApi.inbox()
            : workspaceApi.content(status, q, tag),
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.processing_status === 'pending') ? 1500 : false,
  })
  const allTags = useQuery({
    queryKey: ['content-tags', status],
    queryFn: () => workspaceApi.content(status),
  })
  const invalidate = (refreshRecent = true) => {
    void cache.invalidateQueries({ queryKey: ['knowledge-folders'] })
    if (refreshRecent) void cache.invalidateQueries({ queryKey: ['recent-imports'] })
    void cache.invalidateQueries({ queryKey: ['content'] })
    void cache.invalidateQueries({ queryKey: ['content-tags'] })
    void cache.invalidateQueries({ queryKey: ['today'] })
    void cache.invalidateQueries({ queryKey: ['data-settings'] })
  }
  const update = useMutation({
    mutationFn: (item: ContentItem) =>
      workspaceApi.updateContent(item.id, { status: status === 'inbox' ? 'knowledge' : 'inbox' }),
    onSuccess: () => {
      setNotice(status === 'inbox' ? '已保存到知识库' : '已移回收件箱')
      invalidate()
    },
  })
  const remove = useMutation({
    mutationFn: workspaceApi.deleteContent,
    onSuccess: async (_, id) => {
      await cache.cancelQueries({ queryKey: ['recent-imports'] })
      cache.removeQueries({ queryKey: ['recent-imports'] })
      setRecentIds((ids) => ids.filter((value) => value !== id))
      setSelected((ids) => ids.filter((value) => value !== id))
      setNotice('已删除内容')
      // React has not rendered the new IDs yet; do not refetch the old query.
      invalidate(false)
    },
  })
  const classify = useMutation({
    mutationFn: workspaceApi.classifyBatch,
    onSuccess: ({ items }) => {
      setRecentIds((ids) => [...new Set([...ids, ...items.map((item) => item.id)])])
      setSelected([])
      setNotice('已提交分类，结果将在下方更新')
      invalidate()
    },
  })
  const retry = useMutation({
    mutationFn: workspaceApi.retryContent,
    onSuccess: () => invalidate(),
  })
  const tags = [...new Set((allTags.data ?? []).flatMap((item) => item.tags))].sort()
  const combined = [
    ...new Map(
      [...(list.data ?? []), ...(recent.data ?? [])].map((item) => [item.id, item])
    ).values(),
  ]
  const items = combined.filter(
    (item) =>
      (!type || item.type === type) &&
      (!tag || item.tags.includes(tag)) &&
      (!q ||
        [item.title, item.content, item.summary, ...item.tags]
          .join(' ')
          .toLowerCase()
          .includes(q.toLowerCase())) &&
      (folderId !== 'unfiled' || !item.folder_id)
  )
  const error =
    update.error ?? remove.error ?? classify.error ?? retry.error ?? recent.error ?? ask.error
  const inbox = status === 'inbox' && !documentId
  const preview = inbox ? items.find((item) => item.id === previewing?.id) : previewing
  const reading = inbox && !!preview
  const layout = reading ? 'list' : view
  return (
    <section
      className={`workspace-page content-page ui-page legacy-content-cards content-view-${layout} ${inbox ? 'inbox-library' : ''} ${reading ? 'has-selected-article' : ''} ${documentId ? 'is-document' : ''}`}
    >
      <div className="content-collection-queue">
        <header className="workspace-header">
          <div>
            <span className="eyebrow">
              {status === 'inbox' ? '留住每一个灵感' : '让积累成为你的知识'}
            </span>
            <h1>{status === 'inbox' ? '收件箱' : '知识库'}</h1>
            <p>
              {status === 'inbox'
                ? '链接、笔记、文件，在这里汇聚。'
                : '收藏已整理的内容，随时找回思路。'}
            </p>
          </div>
          <div className="content-header-actions">
            <div className="workspace-count">{allTags.data?.length ?? '—'} 项内容</div>
            {status === 'inbox' && (
              <button
                className="primary-button"
                aria-label="添加到收件箱"
                onClick={() => setCaptureOpen(true)}
              >
                <Plus size={18} />
                收集内容
              </button>
            )}
          </div>
        </header>
        {captureOpen && (
          <CaptureDialog
            onClose={() => setCaptureOpen(false)}
            onSaved={(item) => {
              setRecentIds((ids) => [...ids, item.id])
              cache.setQueryData<ContentItem[]>(
                ['recent-imports', [...recentIds, item.id]],
                [...(recent.data ?? []), item]
              )
              setCaptureOpen(false)
              setNotice('已保存，正在后台整理')
              invalidate()
            }}
          />
        )}
        <div className="workspace-toolbar">
          <div className="search-field">
            <Search size={17} />
            <input
              aria-label="搜索内容"
              placeholder="搜索标题、内容或标签"
              value={q}
              onChange={(event) => setQ(event.target.value)}
            />
          </div>
          <select
            aria-label="按标签筛选"
            value={tag}
            onChange={(event) => setTag(event.target.value)}
          >
            <option value="">全部标签</option>
            {tags.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div className="content-filter-row">
          <div className="segmented content-filter" aria-label="内容类型筛选">
            {[
              ['', '全部'],
              ['link', '链接'],
              ['note', '笔记'],
              ['file', '文件'],
            ].map(([value, label]) => (
              <button
                key={value}
                className={type === value ? 'selected' : ''}
                aria-pressed={type === value}
                onClick={() => setType(value)}
              >
                {label}
                <span className="content-type-count">
                  {combined.filter((item) => !value || item.type === value).length}
                </span>
              </button>
            ))}
          </div>
          <div className="collection-view-switch" role="group" aria-label="内容布局">
            <button
              aria-label="内容列表视图"
              aria-pressed={layout === 'list'}
              onClick={() => {
                setPreviewing(null)
                setView('list')
              }}
            >
              <List size={17} />
            </button>
            <button
              aria-label="内容卡片视图"
              aria-pressed={layout === 'grid'}
              onClick={() => {
                setPreviewing(null)
                setView('grid')
              }}
            >
              <LayoutGrid size={17} />
            </button>
          </div>
          {status === 'inbox' && items.length > 0 && (
            <div className="content-bulk">
              <label className="content-checkbox">
                <input
                  type="checkbox"
                  aria-label="选择全部内容"
                  checked={items.length > 0 && items.every((item) => selected.includes(item.id))}
                  onChange={(event) =>
                    setSelected(event.target.checked ? items.map((item) => item.id) : [])
                  }
                />
                全选
              </label>
              <button
                className="secondary-button"
                disabled={!selected.length || classify.isPending}
                onClick={() => classify.mutate(selected)}
              >
                归类所选{selected.length ? ` (${selected.length})` : ''}
              </button>
            </div>
          )}
        </div>
        {notice && (
          <p className="workspace-notice" role="status">
            {notice}
          </p>
        )}
        {error && (
          <p className="workspace-error" role="alert">
            {error.message}
          </p>
        )}
        {editing && (
          <ContentDialog title="编辑内容" onClose={() => setEditing(null)}>
            <ContentEditor
              key={editing.id}
              item={editing}
              onClose={() => setEditing(null)}
              onSaved={invalidate}
            />
          </ContentDialog>
        )}
        {previewing && !inbox && (
          <ContentPreview
            key={previewing.id}
            item={previewing}
            asking={ask.isPending}
            onClose={() => setPreviewing(null)}
            onEdit={() => {
              const item = previewing
              setPreviewing(null)
              setEditing(item)
            }}
            onAsk={() =>
              ask.mutate({
                draft: '请帮我梳理这份内容的要点。',
                reference: {
                  documentId: previewing.id,
                  title: previewing.title,
                  content: [previewing.content, previewing.summary, previewing.source]
                    .filter(Boolean)
                    .join('\n\n'),
                },
              })
            }
          />
        )}
        {list.isLoading ? (
          <p className="workspace-empty">正在找回你的内容…</p>
        ) : list.error ? (
          <div className="workspace-empty">
            <p role="alert">{list.error.message}</p>
            <button className="secondary-button" onClick={() => void list.refetch()}>
              重新加载
            </button>
          </div>
        ) : !items.length ? (
          <div className="workspace-empty">
            <BookOpen size={32} />
            <h2>
              {q || tag || type
                ? '没有匹配的内容'
                : status === 'inbox'
                  ? '这里准备好接住你的灵感'
                  : '知识从一点点积累开始'}
            </h2>
            <p>
              {q || tag || type
                ? '换个关键词，或试试其他筛选。'
                : status === 'inbox'
                  ? '点击添加，收进一段文字、一个链接或一份文件。'
                  : '把收件箱中整理好的内容保存到这里。'}
            </p>
            {!q && !tag && !type && status === 'inbox' && (
              <button className="primary-button" onClick={() => setCaptureOpen(true)}>
                <Plus size={16} />
                收集第一条内容
              </button>
            )}
          </div>
        ) : documentId && items[0] ? (
          <div className="document-reading-layout">
            <div className="document-more">
              <ActionMenu label={`内容操作：${items[0].title}`}>
                {status === 'inbox' && items[0].status === 'knowledge' ? (
                  <Link
                    to={`/knowledge?folder=${encodeURIComponent(items[0].folder_id ?? 'unfiled')}&document=${encodeURIComponent(items[0].id)}`}
                  >
                    查看归类结果
                  </Link>
                ) : (
                  <button
                    disabled={
                      update.isPending ||
                      classify.isPending ||
                      items[0].processing_status === 'pending'
                    }
                    onClick={() =>
                      status === 'inbox' ? classify.mutate([items[0].id]) : update.mutate(items[0])
                    }
                  >
                    <ArrowRight size={15} />
                    {status === 'inbox' ? '归档到知识库' : '移回收件箱'}
                  </button>
                )}
                <button
                  className="delete-action"
                  aria-label={`删除 ${items[0].title}`}
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(items[0].id)}
                >
                  <Trash2 size={15} />
                  删除
                </button>
              </ActionMenu>
            </div>
            {items[0].processing_status === 'failed' && (
              <div className="document-processing-error" role="alert">
                <p>
                  整理失败 · 原始内容已保留
                  {items[0].processing_error ? `：${items[0].processing_error}` : ''}
                </p>
                <button
                  className="secondary-button"
                  disabled={retry.isPending}
                  onClick={() => retry.mutate(items[0].id)}
                >
                  重新整理
                </button>
              </div>
            )}
            <ContentPreview
              standalone
              item={items[0]}
              onClose={() => setPreviewing(null)}
              onEdit={() => setEditing(items[0])}
              asking={ask.isPending}
              onAsk={() =>
                ask.mutate({
                  draft: '请帮我梳理这份内容的要点。',
                  reference: {
                    documentId: items[0].id,
                    title: items[0].title,
                    content: [items[0].content, items[0].summary, items[0].source]
                      .filter(Boolean)
                      .join('\n\n'),
                  },
                })
              }
            />
          </div>
        ) : (
          <div className="content-list">
            {items.map((item) => {
              const Icon = icons[item.type],
                sourceUrl = safeHttpUrl(item.source)
              return (
                <article
                  className={`content-row is-openable ${preview?.id === item.id ? 'is-current' : ''}`}
                  key={item.id}
                  onClick={(event) => {
                    // Let the card's own buttons, links, inputs and labels act on their own;
                    // a click anywhere else opens the preview.
                    if ((event.target as HTMLElement).closest('button, a, input, label')) return
                    setPreviewing(item)
                  }}
                >
                  {status === 'inbox' && (
                    <input
                      type="checkbox"
                      aria-label={`选择 ${item.title}`}
                      checked={selected.includes(item.id)}
                      onChange={(event) =>
                        setSelected((ids) =>
                          event.target.checked
                            ? [...ids, item.id]
                            : ids.filter((id) => id !== item.id)
                        )
                      }
                    />
                  )}
                  <div className={`item-symbol ${item.type}`}>
                    <Icon size={24} />
                  </div>
                  <div className="content-row-body">
                    <div className="content-row-title">
                      <h2>
                        <button
                          type="button"
                          className="content-row-open"
                          onClick={() => setPreviewing(item)}
                        >
                          {item.title}
                        </button>
                      </h2>
                      <time dateTime={item.updated_at}>
                        {new Date(item.updated_at).toLocaleDateString('zh-CN')}
                      </time>
                    </div>
                    <p className="content-excerpt">
                      {item.summary || item.content || item.filename || item.source}
                    </p>
                    {sourceUrl && (
                      <a className="source-link" href={sourceUrl} target="_blank" rel="noreferrer">
                        {item.source}
                      </a>
                    )}
                    <div className="content-processing" role="status">
                      {item.processing_status === 'pending'
                        ? '正在整理标题、摘要与标签…'
                        : item.processing_status === 'failed'
                          ? `整理失败 · 原始内容已保留${item.processing_error ? `：${item.processing_error}` : ''}`
                          : item.status === 'knowledge'
                            ? `已归类至 ${folders.data?.find((folder) => folder.id === item.folder_id)?.name ?? '未分类'} · ${item.ai_processed ? 'AI 已整理' : '本地整理'}`
                            : item.ai_processed
                              ? 'AI 已整理 · 待归类'
                              : '待整理'}
                    </div>
                    {item.processing_status === 'failed' && (
                      <button
                        className="secondary-button"
                        disabled={retry.isPending}
                        onClick={() => retry.mutate(item.id)}
                      >
                        重新整理
                      </button>
                    )}
                    <div className="tag-list">
                      {item.tags.map((value) => (
                        <button key={value} onClick={() => setTag(value)}>
                          # {value}
                        </button>
                      ))}
                    </div>
                    <div className="content-row-menu">
                      <ActionMenu label={`内容操作：${item.title}`}>
                        <button onClick={() => setEditing(item)}>
                          <Pencil size={14} />
                          编辑内容
                        </button>
                        {status === 'inbox' && item.status === 'knowledge' ? (
                          <Link
                            to={`/knowledge?folder=${encodeURIComponent(item.folder_id ?? 'unfiled')}&document=${encodeURIComponent(item.id)}`}
                          >
                            查看归类结果
                          </Link>
                        ) : (
                          <button
                            disabled={
                              update.isPending ||
                              classify.isPending ||
                              item.processing_status === 'pending'
                            }
                            onClick={() =>
                              status === 'inbox' ? classify.mutate([item.id]) : update.mutate(item)
                            }
                          >
                            <ArrowRight size={14} />
                            {status === 'inbox' ? '归档到知识库' : '移回收件箱'}
                          </button>
                        )}
                        <button
                          disabled={ask.isPending}
                          onClick={() =>
                            ask.mutate({
                              draft: '请帮我梳理这份内容的要点。',
                              reference: {
                                documentId: item.id,
                                title: item.title,
                                content: [
                                  item.filename
                                    ? `文件：${item.filename}\n以下参考仅包含文件名与备注，原文件内容未展开。`
                                    : '',
                                  item.content,
                                  item.summary,
                                  item.source,
                                ]
                                  .filter(Boolean)
                                  .join('\n\n'),
                              },
                            })
                          }
                        >
                          <Sparkles size={14} />
                          引用提问
                        </button>
                        {item.filename && (
                          <a href={workspaceApi.originalUrl(item.id)} download={item.filename}>
                            <Download size={14} />
                            下载原件
                          </a>
                        )}
                        <button
                          className="delete-action"
                          disabled={remove.isPending}
                          aria-label={`删除 ${item.title}`}
                          onClick={() => remove.mutate(item.id)}
                        >
                          <Trash2 size={14} />
                          删除
                        </button>
                      </ActionMenu>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </div>
      {inbox && preview && (
        <section className="content-article-pane" aria-label="资料阅读">
          <div className="feed-pane-heading">
            <button className="secondary-button" onClick={() => setPreviewing(null)}>
              返回内容卡片
            </button>
            <span>内容与来源</span>
          </div>
          <div className="content-reader-scroll" key={preview.id}>
            <ContentPreview
              standalone
              item={preview}
              asking={ask.isPending}
              onClose={() => setPreviewing(null)}
              onEdit={() => setEditing(preview)}
              onAsk={() =>
                ask.mutate({
                  draft: '请帮我梳理这份内容的要点。',
                  reference: {
                    documentId: preview.id,
                    title: preview.title,
                    content: [preview.content, preview.summary, preview.source]
                      .filter(Boolean)
                      .join('\n\n'),
                  },
                })
              }
            />
          </div>
        </section>
      )}
    </section>
  )
}
