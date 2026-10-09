import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Folder, Plus, Search } from 'lucide-react'
import { workspaceApi, type KnowledgeFolder } from '../../lib/workspace-api'
import { ContentPage } from '../content/ContentPage'
import { ContentDialog } from '../content/ContentDialog'
import './knowledge.css'

function FolderEditor({
  folder,
  onClose,
}: {
  folder: KnowledgeFolder | null
  onClose: () => void
}) {
  const cache = useQueryClient()
  const [name, setName] = useState(folder?.name ?? ''),
    [summary, setSummary] = useState(folder?.summary ?? ''),
    [tags, setTags] = useState(folder?.tags.join(', ') ?? ''),
    [priority, setPriority] = useState(String(folder?.priority ?? 0))
  const save = useMutation({
    mutationFn: () => {
      const body = {
        name: name.trim(),
        summary: summary.trim(),
        tags: [
          ...new Set(
            tags
              .split(/[,，]/)
              .map((tag) => tag.trim())
              .filter(Boolean)
          ),
        ],
        priority: Number(priority),
      }
      return folder ? workspaceApi.updateFolder(folder.id, body) : workspaceApi.createFolder(body)
    },
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ['knowledge-folders'] })
      onClose()
    },
  })
  return (
    <ContentDialog title={folder ? '编辑文件夹规则' : '新建文件夹'} onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <label>
          文件夹名称
          <input required value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          规则摘要
          <textarea rows={3} value={summary} onChange={(event) => setSummary(event.target.value)} />
        </label>
        <label>
          匹配标签
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            placeholder="用逗号分隔"
          />
        </label>
        <label>
          优先级
          <input
            required
            type="number"
            step="1"
            value={priority}
            onChange={(event) => setPriority(event.target.value)}
          />
        </label>
        <p className="section-description">
          标签匹配的内容会进入对应文件夹；匹配相同时优先级较高的规则优先。未匹配资料保留在未分类中。
        </p>
        {save.error && (
          <p className="workspace-error" role="alert">
            {save.error.message}
          </p>
        )}
        <div className="editor-actions">
          <button className="secondary-button" type="button" onClick={onClose}>
            取消
          </button>
          <button className="primary-button" disabled={save.isPending || !name.trim()}>
            保存规则
          </button>
        </div>
      </form>
    </ContentDialog>
  )
}

export function KnowledgePage() {
  const cache = useQueryClient(),
    [params, setParams] = useSearchParams()
  const folderId = params.get('folder')
  const [editing, setEditing] = useState<KnowledgeFolder | null | undefined>(undefined),
    [deleting, setDeleting] = useState<KnowledgeFolder | null>(null),
    [q, setQ] = useState(''),
    [search, setSearch] = useState('')
  const folders = useQuery({ queryKey: ['knowledge-folders'], queryFn: workspaceApi.folders })
  const results = useQuery({
    queryKey: ['knowledge-search', search],
    queryFn: () => workspaceApi.searchKnowledge(search),
    enabled: !!search,
  })
  const remove = useMutation({
    mutationFn: workspaceApi.deleteFolder,
    onSuccess: () => {
      setDeleting(null)
      void cache.invalidateQueries({ queryKey: ['knowledge-folders'] })
      void cache.invalidateQueries({ queryKey: ['content'] })
    },
  })
  const activeFolder = folders.data?.find((folder) => folder.id === folderId)
  if (folderId)
    return (
      <div className="knowledge-detail">
        <div className="knowledge-detail-heading">
          <button className="secondary-button" onClick={() => setParams({})}>
            <ArrowLeft size={16} />
            返回文件夹
          </button>
          <span>
            {folderId === 'all'
              ? '全部资料'
              : folderId === 'unfiled'
                ? '未分类'
                : (activeFolder?.name ?? '文件夹资料')}
          </span>
        </div>
        <ContentPage
          key={folderId}
          status="knowledge"
          documentId={params.get('document') ?? undefined}
          folderId={folderId === 'all' ? undefined : folderId}
        />
      </div>
    )
  return (
    <section className="workspace-page knowledge-page">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">让积累成为你的知识</span>
          <h1>Knowledge</h1>
          <p>通过标签规则自动归类，也可以随时手动调整。</p>
        </div>
        <button className="primary-button" onClick={() => setEditing(null)}>
          <Plus size={17} />
          新建文件夹
        </button>
      </header>
      <form
        className="workspace-toolbar"
        onSubmit={(event) => {
          event.preventDefault()
          setSearch(q.trim())
        }}
      >
        <label className="search-field">
          <Search size={17} />
          <input
            aria-label="检索知识库"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="按标签、关键词或问题检索"
          />
        </label>
        <button className="secondary-button">检索</button>
        {search && (
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              setSearch('')
              setQ('')
            }}
          >
            清除
          </button>
        )}
      </form>
      <nav className="knowledge-links" aria-label="知识库浏览">
        <Link to="?folder=all">全部资料</Link>
        <Link to="?folder=unfiled">未分类</Link>
      </nav>
      {search && (
        <section className="knowledge-results" aria-label="知识库检索结果">
          <h2>检索结果</h2>
          {results.isLoading ? (
            <p role="status">正在检索…</p>
          ) : results.error ? (
            <p className="workspace-error" role="alert">
              {results.error.message}
            </p>
          ) : (
            <>
              <p className="section-description">
                {results.data?.items.length ?? 0} 条结果 · {results.data?.mode_used}
              </p>
              {results.data?.items.map((item) => (
                <article key={item.document_id}>
                  <Link to={`?folder=all&document=${encodeURIComponent(item.document_id)}`}>
                    <h3>{item.title}</h3>
                  </Link>
                  <p>{item.snippet || item.summary}</p>
                  <div className="tag-list">
                    {item.matched_tags.map((tag) => (
                      <span key={tag}># {tag}</span>
                    ))}
                  </div>
                </article>
              ))}
            </>
          )}
        </section>
      )}
      {folders.isLoading ? (
        <p className="workspace-empty">正在加载文件夹…</p>
      ) : folders.error ? (
        <div className="workspace-empty">
          <p role="alert">{folders.error.message}</p>
          <button className="secondary-button" onClick={() => void folders.refetch()}>
            重新加载
          </button>
        </div>
      ) : !folders.data?.length ? (
        <div className="workspace-empty">
          <Folder size={32} />
          <h2>建立第一条整理规则</h2>
          <p>新建文件夹并设置匹配标签，让导入的资料有处可去。</p>
        </div>
      ) : (
        <div className="knowledge-folder-grid">
          {folders.data.map((folder) => (
            <article className="knowledge-folder-card" key={folder.id}>
              <Link
                className="knowledge-folder-open"
                to={`?folder=${encodeURIComponent(folder.id)}`}
              >
                <div className="knowledge-folder-symbol">
                  <Folder size={26} />
                  <span>{folder.item_count} 项内容</span>
                </div>
                <h2>{folder.name}</h2>
                <p>{folder.summary || '尚未填写规则摘要'}</p>
              </Link>
              <div className="tag-list">
                {folder.tags.map((tag) => (
                  <span key={tag}># {tag}</span>
                ))}
              </div>
              <footer>
                <span>优先级 {folder.priority}</span>
                <div>
                  <button onClick={() => setEditing(folder)}>编辑规则</button>
                  <button
                    aria-label={`删除文件夹 ${folder.name}`}
                    onClick={() => setDeleting(folder)}
                  >
                    删除
                  </button>
                </div>
              </footer>
            </article>
          ))}
        </div>
      )}
      {editing !== undefined && (
        <FolderEditor
          key={editing?.id ?? 'new'}
          folder={editing}
          onClose={() => setEditing(undefined)}
        />
      )}
      {deleting && (
        <ContentDialog title={`删除文件夹 ${deleting.name}`} onClose={() => setDeleting(null)}>
          <p className="section-description">
            资料会保留在知识库中，移至未分类。确认删除这个文件夹？
          </p>
          {remove.error && (
            <p className="workspace-error" role="alert">
              {remove.error.message}
            </p>
          )}
          <div className="editor-actions">
            <button className="secondary-button" onClick={() => setDeleting(null)}>
              取消
            </button>
            <button
              className="primary-button"
              disabled={remove.isPending}
              onClick={() => remove.mutate(deleting.id)}
            >
              确认删除
            </button>
          </div>
        </ContentDialog>
      )}
    </section>
  )
}
