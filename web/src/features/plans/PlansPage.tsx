import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, CalendarCheck2 } from 'lucide-react'
import { workspaceApi, type Task } from '../../lib/workspace-api'
import '../today/today.css'
import './plans.css'
function TaskEditor({ task, onDone }: { task: Task; onDone: () => void }) {
  const [title, setTitle] = useState(task.title),
    [demoRevision] = useState(task.demo_revision),
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
      workspaceApi.updateTask(task.id, {
        title,
        due_at: due ? new Date(due).toISOString() : null,
        demo_revision: demoRevision,
      }),
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
export function PlansPage() {
  const cache = useQueryClient()
  const [scope, setScope] = useState<'day' | 'week' | 'goal'>('day')
  const [title, setTitle] = useState(''),
    [due, setDue] = useState(''),
    [parent, setParent] = useState('')
  const [tab, setTab] = useState('active'),
    [editing, setEditing] = useState<string | null>(null)
  const plans = useQuery({ queryKey: ['plans'], queryFn: workspaceApi.tasks })
  const all = plans.data ?? []
  const rank = { goal: 0, week: 1, day: 2 }
  const parents = all.filter((item) => rank[item.scope ?? 'day'] < rank[scope] && !item.completed)
  const invalidate = () => {
    void cache.invalidateQueries({ queryKey: ['plans'] })
    void cache.invalidateQueries({ queryKey: ['today'] })
  }
  const create = useMutation({
    mutationFn: () =>
      workspaceApi.createTask(title.trim(), due ? new Date(due).toISOString() : null, {
        scope,
        parent_id: parent || null,
      }),
    onSuccess: () => {
      setTitle('')
      setDue('')
      setParent('')
      invalidate()
    },
  })
  const toggle = useMutation({
    mutationFn: (task: Task) => workspaceApi.updateTask(task.id, { completed: !task.completed }),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: workspaceApi.deleteTask, onSuccess: invalidate })
  const scoped = all.filter((task) => (task.scope ?? 'day') === scope)
  const tasks = scoped.filter((task) => (tab === 'done' ? task.completed : !task.completed))
  const error = create.error ?? toggle.error ?? remove.error ?? plans.error
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
            {task.parent_id && (
              <small className="plan-parent">
                {all.find((item) => item.id === task.parent_id)?.title}
              </small>
            )}
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
        {scope === 'goal' ? '新增目标' : scope === 'week' ? '新增周计划' : '新增待办'}
      </label>
      <div className="task-input">
        <Plus size={17} />
        <input
          id="task-title"
          required
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={
            scope === 'goal'
              ? '写下一个长期目标…'
              : scope === 'week'
                ? '这周想推进什么？'
                : '添加一项待办…'
          }
        />
      </div>
      {parents.length > 0 && (
        <label>
          关联上级计划
          <select
            aria-label="关联上级计划"
            value={parent}
            onChange={(event) => setParent(event.target.value)}
          >
            <option value="">独立计划</option>
            {parents.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title}
              </option>
            ))}
          </select>
        </label>
      )}
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
    <section className="workspace-page plans-page">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">把想法落到行动</span>
          <h1>
            <CalendarCheck2 size={26} />
            个人计划
          </h1>
          <p>从长期目标，到每周推进，再到今天的一小步。</p>
        </div>
      </header>
      <div className="plans-scope" aria-label="计划范围">
        {(
          [
            { value: 'goal', label: '长期目标' },
            { value: 'week', label: '周计划' },
            { value: 'day', label: '日待办' },
          ] as const
        ).map((item) => (
          <button
            key={item.value}
            aria-pressed={scope === item.value}
            onClick={() => {
              setScope(item.value)
              setParent('')
              setEditing(null)
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
      <section className="plans-board">
        <div className="segmented" aria-label="待办状态">
          <button aria-pressed={tab === 'active'} onClick={() => setTab('active')}>
            待完成 {scoped.filter((task) => !task.completed).length}
          </button>
          <button aria-pressed={tab === 'done'} onClick={() => setTab('done')}>
            已完成 {scoped.filter((task) => task.completed).length}
          </button>
        </div>
        {plans.isLoading && <p role="status">正在读取计划…</p>}
        <div className="task-list">
          {tasks.length ? (
            tasks.map(renderTask)
          ) : (
            <p className="task-empty">
              {tab === 'done' ? '完成的计划会留在这里。' : '留下一件想完成的事。'}
            </p>
          )}
        </div>
        {taskForm}
        {error && (
          <p role="alert" className="workspace-error">
            {error.message}
            <button className="secondary-button" onClick={() => void plans.refetch()}>
              重新加载
            </button>
          </p>
        )}
      </section>
    </section>
  )
}
