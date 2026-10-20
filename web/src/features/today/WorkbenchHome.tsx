import { useCallback, useState, type CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowRight,
  BookOpen,
  CalendarCheck2,
  Check,
  CheckSquare2,
  FileText,
  House,
  Inbox,
  Newspaper,
  Paperclip,
  Plus,
  RefreshCw,
  Sparkles,
  SquarePen,
  UserRound,
  Zap,
} from 'lucide-react'
import { usePreferences } from '../../lib/preferences'
import { ArtworkImage } from '../../components/ArtworkImage'
import { FeedCover } from '../feed/FeedDiscovery'
import { safeHttpUrl, workspaceApi, type FeedItem, type Task } from '../../lib/workspace-api'
import { api } from '../../lib/api'
import { ContentDialog } from '../content/ContentDialog'
import { CaptureDialog } from '../content/CaptureDialog'
import { useAskAI } from '../content/useAskAI'
import { Modal } from '../../components/Modal'
import { TaskForm, type PlanDraft } from '../plans/components/TaskForm'
import { dateKey, parsePlanDate, taskDate } from '../plans/plan-utils'
import { FocusCard } from './FocusCard'
import { useHomeDraft } from './useHomeDraft'
import './home-workbench.css'

type CaptureMode = 'note' | 'feed' | 'assistant'
function todayTask(task: Task) {
  const date = taskDate(task)
  return (task.scope ?? 'day') === 'day' && (!date || dateKey(date) === dateKey(new Date()))
}
function timeLabel(task: Task) {
  const start = parsePlanDate(task.starts_at),
    end = parsePlanDate(task.due_at)
  const time = (date: Date) =>
    date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return start && end ? `${time(start)} – ${time(end)}` : end ? time(end) : '待安排'
}
function relative(value: string) {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000))
  return minutes < 1
    ? '刚刚'
    : minutes < 60
      ? `${minutes} 分钟前`
      : minutes < 1440
        ? `${Math.floor(minutes / 60)} 小时前`
        : new Date(value).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

export function WorkbenchHome() {
  const cache = useQueryClient(),
    preferences = usePreferences(),
    ask = useAskAI()
  const [draft, setDraft] = useHomeDraft()
  const [filter, setFilter] = useState<'all' | 'pending' | 'done'>('all'),
    [capture, setCapture] = useState<CaptureMode | null>(null),
    [captureDraft, setCaptureDraft] = useState(''),
    [feedUrl, setFeedUrl] = useState(''),
    [fileCapture, setFileCapture] = useState(false),
    [taskForm, setTaskForm] = useState(false),
    [feedPreview, setFeedPreview] = useState<FeedItem | null>(null),
    [feedOffset, setFeedOffset] = useState(0),
    [brief, setBrief] = useState(false),
    [notice, setNotice] = useState('')
  const data = useQuery({ queryKey: ['today'], queryFn: workspaceApi.today })
  const notes = useQuery({
    queryKey: ['home-content', 'inbox'],
    queryFn: () => workspaceApi.content('inbox'),
  })
  const knowledge = useQuery({
    queryKey: ['home-content', 'knowledge'],
    queryFn: () => workspaceApi.content('knowledge'),
  })
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: api.conversations })
  const tasks = (data.data?.tasks ?? [])
    .filter(todayTask)
    .sort(
      (a, b) =>
        (taskDate(a)?.getTime() ?? Number.MAX_SAFE_INTEGER) -
        (taskDate(b)?.getTime() ?? Number.MAX_SAFE_INTEGER)
    )
  const done = tasks.filter((task) => task.completed).length,
    percent = tasks.length ? Math.round((done / tasks.length) * 100) : 0
  const collected = [...(notes.data ?? []), ...(knowledge.data ?? [])]
  const todayNotes = collected.filter(
    (item) => dateKey(new Date(item.created_at)) === dateKey(new Date())
  )
  const visible = tasks.filter(
    (task) => filter === 'all' || (filter === 'done' ? task.completed : !task.completed)
  )
  const feed = data.data?.feed ?? []
  const invalidate = () => {
    for (const key of [
      'today',
      'plans',
      'content',
      'home-content',
      'content-tags',
      'feed',
      'data-settings',
    ])
      void cache.invalidateQueries({ queryKey: [key] })
  }
  const toggle = useMutation({
    mutationFn: (task: Task) =>
      workspaceApi.updateTask(task.id, {
        completed: !task.completed,
        demo_revision: task.demo_revision,
      }),
    onSuccess: invalidate,
  })
  const createTask = useMutation({
    mutationFn: (value: PlanDraft) => workspaceApi.createTask(value.title, value.due_at, value),
    onSuccess: () => {
      setTaskForm(false)
      setDraft('')
      invalidate()
    },
  })
  const saveFeed = useMutation({
    mutationFn: workspaceApi.saveFeed,
    onSuccess: () => {
      setNotice('已收进收件箱')
      invalidate()
    },
  })
  const closeTask = useCallback(() => {
    if (!createTask.isPending) setTaskForm(false)
  }, [createTask.isPending])
  const saveCapture = useMutation({
    mutationFn: async () => {
      if (!captureDraft.trim()) throw new Error('先记下一点内容吧。')
      if (capture === 'feed')
        await workspaceApi.addManualFeed({
          url: feedUrl.trim(),
          title: captureDraft.trim().split('\n')[0],
          summary: captureDraft.trim(),
        })
      else if (capture === 'assistant') await ask.mutateAsync({ draft: captureDraft.trim() })
      else await workspaceApi.importContent({ text: captureDraft.trim(), use_ai: false })
    },
    onSuccess: () => {
      setCapture(null)
      setDraft('')
      setNotice('已保存，灵感有了去处。')
      invalidate()
    },
  })
  const openCapture = (mode: CaptureMode) => {
    setCaptureDraft(draft)
    setFeedUrl('')
    saveCapture.reset()
    setCapture(mode)
  }
  const closeCapture = () => {
    if (saveCapture.isPending) return
    setDraft(captureDraft)
    setCapture(null)
  }
  const activities = [
    ...collected.map((item) => ({
      id: 'c' + item.id,
      title: `收录了${item.type === 'link' ? '链接' : item.type === 'file' ? '文件' : '笔记'}`,
      detail: item.title,
      time: item.created_at,
      to:
        item.status === 'inbox'
          ? `/inbox?item=${encodeURIComponent(item.id)}`
          : `/knowledge?folder=all&document=${encodeURIComponent(item.id)}`,
      type: 'note',
    })),
    ...(data.data?.tasks ?? [])
      .filter((item) => item.completed && item.completed_at)
      .map((item) => ({
        id: 't' + item.id,
        title: '完成了任务',
        detail: item.title,
        time: item.completed_at!,
        to: '/plans',
        type: 'task',
      })),
    ...(conversations.data ?? []).map((item) => ({
      id: 'a' + item.id,
      title: '更新了 AI 对话',
      detail: item.title,
      time: item.updated_at,
      to: `/assistant?c=${encodeURIComponent(item.id)}`,
      type: 'chat',
    })),
  ]
    .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
    .slice(0, 4)
  const briefText = `今日简报 · ${new Date().toLocaleDateString('zh-CN')}\n任务完成 ${done}/${tasks.length}\n今日收录 ${todayNotes.length} 条\n待整理 ${data.data?.inbox_count ?? 0} 条\n\n已完成任务\n${
    tasks
      .filter((task) => task.completed)
      .map((task) => '· ' + task.title)
      .join('\n') || '还没有已完成任务'
  }\n\n今日收录\n${todayNotes.map((item) => '· ' + item.title).join('\n') || '还没有新增收录'}`
  return (
    <section className="home-workbench" aria-label="山水工作台">
      <header className="wb-welcome">
        <picture className="wb-landscape">
          <ArtworkImage
            topic="nature"
            slot="home-landscape"
            sizes="(max-width: 760px) 100vw, 70vw"
            fetchPriority="high"
          />
        </picture>
        <div>
          <h1>
            {new Date().getHours() < 12
              ? '早上好'
              : new Date().getHours() < 18
                ? '下午好'
                : '晚上好'}
            ，{preferences.displayName || '朋友'}
            <Sparkles size={29} aria-hidden="true" />
          </h1>
          <p>新的一天，愿你在有序中，遇见更好的自己。</p>
          <button className="wb-brief-link" onClick={() => setBrief(true)}>
            <span>
              {new Date().toLocaleDateString('zh-CN', {
                month: 'long',
                day: 'numeric',
                weekday: 'long',
              })}
            </span>
            今日简报 <ArrowRight size={14} />
          </button>
        </div>
      </header>
      <div className="wb-content">
        <section className="wb-stats" aria-label="今日概览">
          <article className="wb-stat">
            <span className="wb-stat-icon violet">
              <CheckSquare2 size={24} />
            </span>
            <div>
              <span className="wb-stat-label">今日任务</span>
              <strong>{data.isLoading ? '—' : `${done} / ${tasks.length}`}</strong>
              <small>
                还有 <em>{tasks.length - done}</em> 项待完成
              </small>
            </div>
            <div
              className="wb-ring"
              style={{ '--progress': `${percent}%` } as CSSProperties}
              role="progressbar"
              aria-label="今日任务完成进度"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
            >
              <span>{percent}%</span>
            </div>
          </article>
          <Link to="/inbox" className="wb-stat">
            <span className="wb-stat-icon blue">
              <FileText size={24} />
            </span>
            <div>
              <span className="wb-stat-label">收集笔记</span>
              <strong>{notes.isLoading || knowledge.isLoading ? '—' : todayNotes.length}</strong>
              <small>今日新增 · 待整理 {data.data?.inbox_count ?? 0}</small>
            </div>
          </Link>
          <Link to="/feed" className="wb-stat">
            <span className="wb-stat-icon green">
              <BookOpen size={24} />
            </span>
            <div>
              <span className="wb-stat-label">可读资讯</span>
              <strong>{data.isLoading ? '—' : feed.length}</strong>
              <small>从关注中，发现新灵感</small>
            </div>
          </Link>
          <FocusCard />
        </section>
        {data.error && (
          <div className="wb-error" role="alert">
            首页数据未能加载：{data.error.message}
            <button onClick={() => void data.refetch()}>重新加载</button>
          </div>
        )}
        {notice && (
          <p className="wb-notice" role="status">
            {notice}
          </p>
        )}
        <div className="wb-columns">
          <div className="wb-column">
            <section className="wb-panel wb-task-panel" aria-labelledby="wb-task-heading">
              <header className="wb-panel-heading">
                <h2 id="wb-task-heading">
                  <CheckSquare2 size={21} />
                  今日任务
                </h2>
                <Link to="/plans">
                  查看全部 <ArrowRight size={15} />
                </Link>
              </header>
              <div className="wb-task-tabs" role="group" aria-label="首页任务筛选">
                {(
                  [
                    ['all', '全部', tasks.length],
                    ['pending', '进行中', tasks.length - done],
                    ['done', '已完成', done],
                  ] as const
                ).map(([value, label, count]) => (
                  <button
                    key={value}
                    aria-pressed={filter === value}
                    onClick={() => setFilter(value)}
                  >
                    {label}
                    <span>{count}</span>
                  </button>
                ))}
              </div>
              {data.isLoading ? (
                <div className="wb-skeleton" role="status" aria-label="正在加载任务">
                  <i />
                  <i />
                  <i />
                </div>
              ) : !visible.length ? (
                <div className="wb-empty">
                  <CheckSquare2 size={27} />
                  <p>
                    {filter === 'done' ? '完成的事，会留在这里。' : '给今天留下一件想完成的事。'}
                  </p>
                  <button className="wb-text-button" onClick={() => setTaskForm(true)}>
                    添加任务 <Plus size={14} />
                  </button>
                </div>
              ) : (
                <ul className="wb-task-list">
                  {visible.slice(0, 4).map((task) => (
                    <li key={task.id} className={task.completed ? 'is-done' : ''}>
                      <label>
                        <input
                          type="checkbox"
                          checked={task.completed}
                          aria-label={task.title}
                          disabled={toggle.isPending}
                          onChange={() => toggle.mutate(task)}
                        />
                        <span className="wb-checkbox" aria-hidden="true">
                          <Check size={14} />
                        </span>
                        <span className="wb-task-title">{task.title}</span>
                      </label>
                      <time>{timeLabel(task)}</time>
                      {task.category && <span className="wb-task-category">{task.category}</span>}
                    </li>
                  ))}
                </ul>
              )}
              {toggle.error && (
                <p className="wb-error" role="alert">
                  {toggle.error.message}
                </p>
              )}
            </section>
            <section className="wb-panel wb-feed-panel" aria-labelledby="wb-feed-heading">
              <header className="wb-panel-heading">
                <h2 id="wb-feed-heading">
                  <Newspaper size={21} />
                  灵感 · 资讯
                </h2>
                <button
                  disabled={feed.length <= 3}
                  onClick={() => setFeedOffset((offset) => (offset + 3) % feed.length)}
                >
                  <RefreshCw size={14} />
                  换一批
                </button>
              </header>
              {data.isLoading ? (
                <div className="wb-skeleton" role="status" aria-label="正在加载资讯">
                  <i />
                  <i />
                </div>
              ) : !feed.length ? (
                <div className="wb-empty">
                  <Newspaper size={27} />
                  <p>读一点新发现，让灵感慢慢汇聚。</p>
                  <Link to="/feed">
                    浏览资讯 <ArrowRight size={14} />
                  </Link>
                </div>
              ) : (
                <div className="wb-feed-cards">
                  {Array.from({ length: Math.min(3, feed.length) }, (_, index) => {
                    const item = feed[(feedOffset + index) % feed.length]
                    return (
                      <button
                        className="wb-feed-card"
                        key={item.id}
                        onClick={() => {
                          saveFeed.reset()
                          setFeedPreview(item)
                        }}
                      >
                        <FeedCover item={item} placement="home" />
                        <h3>{item.title}</h3>
                        <time dateTime={item.published_at}>{relative(item.published_at)}</time>
                      </button>
                    )
                  })}
                </div>
              )}
            </section>
          </div>
          <div className="wb-column">
            <section className="wb-panel wb-quick-panel" aria-labelledby="wb-quick-heading">
              <header className="wb-panel-heading">
                <h2 id="wb-quick-heading">
                  <SquarePen size={21} />
                  快速记录
                </h2>
                <button
                  className="wb-button"
                  aria-label="快速记录"
                  onClick={() => openCapture('note')}
                >
                  <Plus size={16} />
                  快速记录
                </button>
              </header>
              <textarea
                aria-label="快速记录内容"
                placeholder="记录你的想法、灵感或待办…"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                maxLength={20000}
                onKeyDown={(event) => {
                  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                    event.preventDefault()
                    openCapture('note')
                  }
                }}
              />
              <div className="wb-quick-actions">
                <button onClick={() => openCapture('note')}>
                  <span className="violet">
                    <Zap size={20} />
                  </span>
                  <strong>笔记</strong>
                  <small>随手记录想法</small>
                </button>
                <button onClick={() => setTaskForm(true)}>
                  <span className="green">
                    <CheckSquare2 size={20} />
                  </span>
                  <strong>任务</strong>
                  <small>添加待办事项</small>
                </button>
                <button onClick={() => openCapture('feed')}>
                  <span className="blue">
                    <BookOpen size={20} />
                  </span>
                  <strong>资讯</strong>
                  <small>保存稍后阅读</small>
                </button>
                <button onClick={() => openCapture('assistant')}>
                  <span className="violet">
                    <Sparkles size={20} />
                  </span>
                  <strong>AI 对话</strong>
                  <small>与 AI 一起思考</small>
                </button>
              </div>
            </section>
            <section className="wb-panel wb-activity-panel" aria-labelledby="wb-activity-heading">
              <header className="wb-panel-heading">
                <h2 id="wb-activity-heading">
                  <CalendarCheck2 size={21} />
                  最近活动
                </h2>
                <Link to="/inbox">
                  查看更多 <ArrowRight size={15} />
                </Link>
              </header>
              {notes.error || knowledge.error || conversations.error ? (
                <p className="wb-error" role="alert">
                  部分最近活动暂时无法读取，已保留可用内容。
                </p>
              ) : null}
              {activities.length ? (
                <ol className="wb-timeline">
                  {activities.map((item) => (
                    <li key={item.id}>
                      <time dateTime={item.time}>{relative(item.time)}</time>
                      <span className={`wb-timeline-dot ${item.type}`} aria-hidden="true" />
                      <Link to={item.to}>
                        <strong>{item.title}</strong>
                        <p>「{item.detail}」</p>
                      </Link>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="wb-empty">
                  <Sparkles size={27} />
                  <p>每一次记录，都会在这里留下足迹。</p>
                </div>
              )}
            </section>
          </div>
        </div>
      </div>
      <nav className="wb-mobile-nav" aria-label="首页底部导航">
        <Link className="active" to="/today">
          <House size={22} />
          今日
        </Link>
        <Link to="/inbox">
          <Inbox size={22} />
          收集
        </Link>
        <button aria-label="打开快速记录" onClick={() => openCapture('note')}>
          <Plus size={26} />
        </button>
        <Link to="/feed">
          <BookOpen size={22} />
          资讯
        </Link>
        <Link to="/settings?section=profile" state={{ backgroundLocation: { pathname: '/today' } }}>
          <UserRound size={22} />
          我的
        </Link>
      </nav>
      {capture && (
        <ContentDialog title="快速记录" onClose={closeCapture}>
          <form
            className="wb-capture-form"
            onSubmit={(event) => {
              event.preventDefault()
              saveCapture.mutate()
            }}
            onKeyDown={(event) => {
              if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault()
                if (!saveCapture.isPending) saveCapture.mutate()
              }
            }}
          >
            <div className="wb-capture-tabs" role="group" aria-label="记录类型">
              {(
                [
                  ['note', '笔记'],
                  ['task', '任务'],
                  ['feed', '资讯'],
                  ['assistant', 'AI 对话'],
                ] as const
              ).map(([value, label]) => (
                <button
                  type="button"
                  key={value}
                  aria-pressed={capture === value}
                  disabled={saveCapture.isPending}
                  onClick={() => {
                    if (value === 'task') {
                      setDraft(captureDraft)
                      setCapture(null)
                      setTaskForm(true)
                    } else {
                      setCapture(value)
                      saveCapture.reset()
                    }
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            {capture === 'feed' && (
              <label>
                资讯链接
                <input
                  type="url"
                  required
                  disabled={saveCapture.isPending}
                  placeholder="https://"
                  value={feedUrl}
                  onChange={(event) => setFeedUrl(event.target.value)}
                />
              </label>
            )}
            <label className="wb-capture-label">
              <span>{capture === 'feed' ? '资讯标题与想法' : '记录内容'}</span>
              <textarea
                aria-label="记录内容"
                autoFocus
                rows={4}
                required
                placeholder={
                  capture === 'assistant'
                    ? '想和 AI 一起思考什么？'
                    : '记录你的想法、灵感或任何内容…'
                }
                value={captureDraft}
                disabled={saveCapture.isPending}
                onChange={(event) => setCaptureDraft(event.target.value)}
              />
            </label>
            {saveCapture.error && (
              <p className="wb-error" role="alert">
                {saveCapture.error.message}
              </p>
            )}
            <footer>
              <button
                type="button"
                className="wb-attachment"
                aria-label="导入文件或链接"
                disabled={saveCapture.isPending}
                onClick={() => {
                  setDraft(captureDraft)
                  setCapture(null)
                  setFileCapture(true)
                }}
              >
                <Paperclip size={20} />
              </button>
              <span>Ctrl / ⌘ + Enter 快速保存</span>
              <button
                className="wb-button"
                aria-label="保存记录"
                disabled={saveCapture.isPending || !captureDraft.trim()}
              >
                {saveCapture.isPending ? '保存中…' : capture === 'assistant' ? '开始对话' : '保存'}
              </button>
            </footer>
          </form>
        </ContentDialog>
      )}
      {fileCapture && (
        <CaptureDialog
          initialText={draft}
          onClose={() => setFileCapture(false)}
          onSaved={() => {
            setFileCapture(false)
            setDraft('')
            invalidate()
          }}
        />
      )}
      {taskForm && (
        <Modal
          title="新建任务"
          onClose={closeTask}
          className="plan-task-dialog"
          headerContent={
            <div className="plan-rich-heading">
              <span>
                <Plus size={26} />
              </span>
              <div>
                <h2>新建任务</h2>
                <p>记录一个想要完成的事，让每一天更有方向。</p>
              </div>
            </div>
          }
        >
          <TaskForm
            tasks={data.data?.tasks ?? []}
            initialScope="day"
            initialTitle={draft}
            busy={createTask.isPending}
            error={createTask.error}
            onCancel={closeTask}
            onSubmit={(value) => createTask.mutate(value)}
          />
        </Modal>
      )}
      {feedPreview && (
        <ContentDialog title={feedPreview.title} onClose={() => setFeedPreview(null)}>
          <div className="wb-feed-preview">
            <span className="wb-source">
              {
                { aihot: '人工智能热点', github: 'GitHub 热门项目', manual: '我的资讯' }[
                  feedPreview.source
                ]
              }
            </span>
            <p>{feedPreview.summary}</p>
            <div className="wb-preview-actions">
              <button
                className="wb-button"
                disabled={saveFeed.isPending || saveFeed.isSuccess}
                onClick={() => saveFeed.mutate(feedPreview.id)}
              >
                {saveFeed.isSuccess ? '已收进收件箱' : '收藏到收件箱'}
              </button>
              {safeHttpUrl(feedPreview.url) && (
                <a href={safeHttpUrl(feedPreview.url)!} target="_blank" rel="noreferrer">
                  阅读原文 <ArrowRight size={16} />
                </a>
              )}
            </div>
            {saveFeed.error && <p role="alert">{saveFeed.error.message}</p>}
          </div>
        </ContentDialog>
      )}
      {brief && (
        <ContentDialog title="今日简报" onClose={() => setBrief(false)}>
          <div className="wb-brief">
            <p>
              {new Date().toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                weekday: 'long',
              })}
            </p>
            <div className="wb-brief-banner">
              <Sparkles size={28} />
              <div>
                今天你完成了 <strong>{done}</strong> 项任务，收录了{' '}
                <strong>{todayNotes.length}</strong> 条内容。<p>思考在串联，行动也在稳步前进。</p>
              </div>
            </div>
            <h3>今日亮点</h3>
            {tasks.filter((task) => task.completed).length ? (
              tasks
                .filter((task) => task.completed)
                .map((task) => <p key={task.id}>· {task.title}</p>)
            ) : (
              <p>一天从一个小小的行动开始。</p>
            )}
            <h3>收录与积累</h3>
            {todayNotes.slice(0, 5).map((item) => (
              <p key={item.id}>· {item.title}</p>
            ))}
            <footer>
              <button
                className="wb-text-button"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(briefText)
                    setNotice('今日简报已复制')
                  } catch {
                    setNotice('无法自动复制，请手动选择简报内容。')
                  }
                }}
              >
                复制简报
              </button>
              <button
                className="wb-button"
                disabled={ask.isPending}
                onClick={() =>
                  ask.mutate({
                    draft: `请根据以下真实记录帮我回顾今天，并给出明天的一条建议。\n\n${briefText}`,
                  })
                }
              >
                与 AI 一起复盘 <ArrowRight size={15} />
              </button>
            </footer>
            {ask.error && <p role="alert">{ask.error.message}</p>}
          </div>
        </ContentDialog>
      )}
    </section>
  )
}
