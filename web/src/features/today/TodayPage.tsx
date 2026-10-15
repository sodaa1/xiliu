import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  ArrowUp,
  CheckCheck,
  Inbox,
  Newspaper,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { workspaceApi, type Task } from '../../lib/workspace-api'
import { useAskAI } from '../content/useAskAI'
import { FeedCard } from '../feed/FeedPage'
import { usePreferences } from '../../lib/preferences'
import { Modal } from '../../components/Modal'
import { GlideSelect } from '../../components/GlideSelect'
import { Avatar } from '../../components/Avatar'
import { useLocation } from 'react-router-dom'
import './today.css'

function TaskEditor({ task, onDone }: { task: Task; onDone: () => void }) {
  const [title, setTitle] = useState(task.title),
    [due, setDue] = useState(
      task.due_at
        ? new Date(
            new Date(task.due_at).getTime() - new Date(task.due_at).getTimezoneOffset() * 60000
          )
            .toISOString()
            .slice(0, 16)
        : ''
    )
  const save = useMutation({
    mutationFn: () =>
      workspaceApi.updateTask(task.id, { title, due_at: due ? new Date(due).toISOString() : null }),
    onSuccess: onDone,
  })
  return (
    <form
      className="task-edit"
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate()
      }}
    >
      <input
        required
        aria-label="修改待办标题"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
      />
      <input
        type="datetime-local"
        aria-label="修改待办时间"
        value={due}
        onChange={(event) => setDue(event.target.value)}
      />
      <div className="row-actions">
        <button disabled={save.isPending}>保存</button>
        <button type="button" onClick={onDone}>
          取消
        </button>
      </div>
      {save.error && (
        <p role="alert" className="workspace-error">
          {save.error.message}
        </p>
      )}
    </form>
  )
}
export function TodayPage() {
  const location = useLocation()
  const preferences = usePreferences()
  const [allTasks, setAllTasks] = useState(false)
  const closeTasks = useCallback(() => setAllTasks(false), [])
  const cache = useQueryClient(),
    ask = useAskAI()
  const [title, setTitle] = useState(''),
    [due, setDue] = useState(''),
    [draft, setDraft] = useState(''),
    [tab, setTab] = useState('active'),
    [editing, setEditing] = useState<string | null>(null)
  const today = useQuery({ queryKey: ['today'], queryFn: workspaceApi.today })
  const invalidate = () => {
    void cache.invalidateQueries({ queryKey: ['today'] })
  }
  const create = useMutation({
    mutationFn: () =>
      workspaceApi.createTask(title.trim(), due ? new Date(due).toISOString() : null),
    onSuccess: () => {
      setTitle('')
      setDue('')
      invalidate()
    },
  })
  const toggle = useMutation({
    mutationFn: (task: Task) => workspaceApi.updateTask(task.id, { completed: !task.completed }),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: workspaceApi.deleteTask, onSuccess: invalidate })
  const tasks = (today.data?.tasks ?? []).filter((task) =>
    tab === 'done' ? task.completed : !task.completed
  )
  const error = create.error ?? toggle.error ?? remove.error ?? ask.error
  const hour = new Date().getHours(),
    greeting = hour < 12 ? '早上好' : hour < 18 ? '下午好' : '晚上好'
  const renderTask = (task: Task) => (
    <div className={`task-row ${task.completed ? 'completed' : ''}`} key={task.id}>
      {editing === task.id ? (
        <TaskEditor
          task={task}
          onDone={() => {
            setEditing(null)
            invalidate()
          }}
        />
      ) : (
        <>
          <input
            type="checkbox"
            aria-label={`${task.completed ? '恢复' : '完成'} ${task.title}`}
            checked={task.completed}
            disabled={toggle.isPending}
            onChange={() => toggle.mutate(task)}
          />
          <button className="task-title" title="编辑待办" onClick={() => setEditing(task.id)}>
            {task.title}
            {task.due_at && (
              <time dateTime={task.due_at}>
                {new Date(task.due_at).toLocaleString('zh-CN', {
                  month: 'numeric',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </time>
            )}
          </button>
          <button
            className="icon-button"
            disabled={remove.isPending}
            aria-label={`删除待办 ${task.title}`}
            onClick={() => remove.mutate(task.id)}
          >
            <Trash2 size={15} />
          </button>
        </>
      )}
    </div>
  )
  const taskForm = (
    <form
      className="task-create"
      onSubmit={(event) => {
        event.preventDefault()
        if (title.trim()) create.mutate()
      }}
    >
      <label className="sr-only" htmlFor="task-title">
        新增待办
      </label>
      <div className="task-input">
        <Plus size={17} />
        <input
          id="task-title"
          required
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="添加一项待办…"
        />
      </div>
      <div className="task-create-bottom">
        <label>
          时间（可选）
          <input
            aria-label="待办时间"
            type="datetime-local"
            value={due}
            onChange={(event) => setDue(event.target.value)}
          />
        </label>
        <button className="primary-button" disabled={create.isPending || !title.trim()}>
          添加
        </button>
      </div>
    </form>
  )
  return (
    <section className="workspace-page today-page">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">TODAY · 每天一点新进展</span>
          <div className="today-title-row">
            <h1>
              {greeting}，{preferences.displayName ? `${preferences.displayName}。` : ''}
              今天从容开始。
            </h1>
            <div className="today-header-actions">
              <Link
                to="/settings?section=profile"
                state={{ backgroundLocation: location }}
                aria-label={`${preferences.displayName || '你'}的个人设置`}
              >
                <Avatar />
              </Link>
            </div>
          </div>
          <p>
            {new Date().toLocaleDateString('zh-CN', {
              month: 'long',
              day: 'numeric',
              weekday: 'long',
            })}
          </p>
        </div>
        {today.error && (
          <div className="workspace-error" role="alert">
            {today.error.message}
            <button className="secondary-button" onClick={() => void today.refetch()}>
              重新加载
            </button>
          </div>
        )}
        {today.isLoading && <p role="status">正在准备今天的空间…</p>}
      </header>
      <div className="today-grid">
        <section className="today-card morning-brief">
          <div className="section-heading">
            <h2>
              <Newspaper size={19} />
              今日简报
            </h2>
            <Link to="/feed">
              查看全部
              <ArrowRight size={15} />
            </Link>
          </div>
          <p className="section-description">来自 AI 与开源世界的最新发现。</p>
          {today.data?.feed.length ? (
            today.data.feed.slice(0, 3).map((item) => <FeedCard key={item.id} item={item} />)
          ) : (
            <div className="workspace-empty">
              <Newspaper size={28} />
              <p>还没有资讯，去 Feed 更新今日发现。</p>
              <Link className="secondary-button" to="/feed">
                打开 Feed
              </Link>
            </div>
          )}
          <Link to="/inbox" className="inbox-summary">
            <Inbox size={19} />
            <span>
              Inbox 中有 <strong>{today.data?.inbox_count ?? '—'}</strong> 项内容，等你整理。
            </span>
            <ArrowRight size={16} />
          </Link>
        </section>
        <section className="today-card task-card">
          <div className="section-heading">
            <h2>
              <CheckCheck size={20} />
              我的待办
            </h2>
            <button className="today-see-tasks" onClick={() => setAllTasks(true)}>
              查看全部
              <ArrowRight size={15} />
            </button>
          </div>
          <p className="section-description">把今天想完成的事，放在这里。</p>
          <div className="segmented" aria-label="待办状态">
            <button
              aria-pressed={tab === 'active'}
              className={tab === 'active' ? 'selected' : ''}
              onClick={() => setTab('active')}
            >
              待完成 {today.data?.tasks.filter((task) => !task.completed).length ?? 0}
            </button>
            <button
              aria-pressed={tab === 'done'}
              className={tab === 'done' ? 'selected' : ''}
              onClick={() => setTab('done')}
            >
              已完成 {today.data?.tasks.filter((task) => task.completed).length ?? 0}
            </button>
          </div>
          <div className="task-list">
            {tasks.length ? (
              tasks.slice(0, 5).map(renderTask)
            ) : (
              <p className="task-empty">
                {tab === 'done' ? '完成的事项会留在这里。' : '给今天留一点值得完成的事。'}
              </p>
            )}
          </div>
          {!allTasks && taskForm}
          {error && (
            <p className="workspace-error" role="alert">
              {error.message}
            </p>
          )}
        </section>
      </div>
      <form
        className="quick-ask"
        onSubmit={(event) => {
          event.preventDefault()
          if (draft.trim()) ask.mutate({ draft: draft.trim() })
        }}
      >
        <Sparkles size={24} />
        <input
          aria-label="问问息流"
          placeholder="问问息流，帮你把想法往前推进…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button
          className="primary-button"
          disabled={ask.isPending || !draft.trim()}
          aria-label="在 Assistant 中继续"
        >
          <ArrowUp size={20} />
        </button>
      </form>
      {allTasks && (
        <Modal title="全部待办" onClose={closeTasks}>
          <GlideSelect
            ariaLabel="全部待办状态"
            value={tab}
            onChange={setTab}
            options={[
              { value: 'active', label: '待完成' },
              { value: 'done', label: '已完成' },
            ]}
          />
          <div className="task-list">
            {tasks.length ? (
              tasks.map(renderTask)
            ) : (
              <p className="task-empty">这里暂时没有事项。</p>
            )}
          </div>
          {taskForm}
          {error && (
            <p className="workspace-error" role="alert">
              {error.message}
            </p>
          )}
        </Modal>
      )}
    </section>
  )
}
