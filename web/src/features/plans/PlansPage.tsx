import { PageToolbar } from '../../components/WorkspaceChrome'
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { gsap } from 'gsap'
import { Plus, Search, X } from 'lucide-react'
import { Modal } from '../../components/Modal'
import { useReducedMotion } from '../../lib/useReducedMotion'
import { workspaceApi, type Task } from '../../lib/workspace-api'
import { PlanCalendar } from './components/PlanCalendar'
import { PlanStats } from './components/PlanStats'
import { PlanReminders } from './components/PlanReminders'
import { PlanProgress } from './components/PlanProgress'
import { PlanEmpty, PlanTaskItem } from './components/PlanTaskItem'
import { TaskForm, type PlanDraft } from './components/TaskForm'
import {
  addDays,
  plansInWeek,
  rank,
  scopeLabels,
  taskDate,
  taskStatus,
  tasksOnDate,
  type PlanScope,
  type PlanStatus,
} from './plan-utils'
import '../today/today.css'
import './plans.css'

const emptyTasks: Task[] = []
const scopes: PlanScope[] = ['day', 'week', 'goal']
type FormState = { task?: Task; title?: string } | null

export function PlansPage({ initialDate }: { initialDate?: Date } = {}) {
  const cache = useQueryClient()
  const reduced = useReducedMotion()
  const [today, setToday] = useState(() => initialDate ?? new Date())
  const [selected, setSelected] = useState(() => initialDate ?? new Date())
  const [scope, setScope] = useState<PlanScope>('day')
  const [status, setStatus] = useState<'all' | PlanStatus>('all')
  const [search, setSearch] = useState('')
  const [parentFilter, setParentFilter] = useState<string | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [form, setForm] = useState<FormState>(null)
  const closeForm = useCallback(() => setForm(null), [])
  const list = useRef<HTMLUListElement>(null)
  const previousPositions = useRef(new Map<string, number>())
  const plans = useQuery({ queryKey: ['plans'], queryFn: workspaceApi.tasks })
  const all = plans.data ?? emptyTasks

  useEffect(() => {
    if (initialDate) return
    let timer: ReturnType<typeof setTimeout>
    const update = () => {
      const now = new Date()
      setToday(now)
      clearTimeout(timer)
      timer = setTimeout(update, addDays(now, 1).getTime() - now.getTime() + 50)
    }
    update()
    window.addEventListener('focus', update)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('focus', update)
    }
  }, [initialDate])

  const invalidate = () => {
    void cache.invalidateQueries({ queryKey: ['plans'] })
    void cache.invalidateQueries({ queryKey: ['today'] })
  }
  const save = useMutation({
    mutationFn: ({ draft, task }: { draft: PlanDraft; task?: Task }) =>
      task
        ? workspaceApi.updateTask(task.id, draft)
        : workspaceApi.createTask(draft.title, draft.due_at, draft),
    onSuccess: (_task, variables) => {
      const date = taskDate(_task)
      if (
        date &&
        (variables.draft.scope === 'day' ||
          (variables.draft.scope === 'week' && !plansInWeek([_task], selected).length))
      )
        setSelected(date)
      setForm(null)
      setDraftTitle('')
      setScope(variables.draft.scope)
      setStatus('all')
      setSearch('')
      setParentFilter((current) => (current === variables.draft.parent_id ? current : null))
      invalidate()
    },
  })
  const toggle = useMutation({
    mutationFn: (task: Task) => workspaceApi.updateTask(task.id, { completed: !task.completed }),
    onSuccess: invalidate,
  })
  const remove = useMutation({
    mutationFn: (task: Task) => workspaceApi.deleteTask(task.id),
    onSuccess: invalidate,
  })
  const updateStatus = useMutation({
    mutationFn: ({ task, status }: { task: Task; status: PlanStatus }) =>
      workspaceApi.updateTask(task.id, {
        status,
        completed: status === 'completed',
        demo_revision: task.demo_revision,
      }),
    onSuccess: invalidate,
  })
  const busy = toggle.isPending || updateStatus.isPending || remove.isPending || save.isPending
  const openForm = (value: FormState) => {
    save.reset()
    setForm(value)
  }
  const actions = {
    busy,
    onToggle: (task: Task) => toggle.mutate(task),
    onStatus: (task: Task, status: PlanStatus) => updateStatus.mutate({ task, status }),
    onEdit: (task: Task) => openForm({ task }),
    onDelete: (task: Task) => remove.mutate(task),
  }
  const query = search.trim().toLocaleLowerCase()
  const searched = all.filter((task) => !query || task.title.toLocaleLowerCase().includes(query))
  const parent = all.find((task) => task.id === parentFilter)
  const candidates = searched.filter(
    (task) => (task.scope ?? 'day') === scope && (!parent || task.parent_id === parent.id)
  )
  const scoped = parent
    ? candidates
    : scope === 'day'
      ? tasksOnDate(candidates, selected)
      : scope === 'week'
        ? plansInWeek(candidates, selected)
        : candidates
  const backlog =
    scope === 'day' && !parent
      ? candidates.filter(
          (task) => !taskDate(task) && (status === 'all' || taskStatus(task) === status)
        )
      : []
  const visible = scoped.filter((task) => status === 'all' || taskStatus(task) === status)
  const signature = visible.map((task) => `${task.id}:${task.completed}`).join('|')
  const error = toggle.error ?? updateStatus.error ?? remove.error

  useLayoutEffect(() => {
    const nodes = list.current?.querySelectorAll<HTMLElement>('[data-plan-task]') ?? []
    const positions = new Map<string, number>()
    const context = gsap.context(() => {
      for (const node of nodes) {
        const id = node.dataset.planTask!,
          top = node.offsetTop
        positions.set(id, top)
        if (reduced) continue
        const previous = previousPositions.current.get(id)
        if (previous === undefined)
          gsap.fromTo(
            node,
            { opacity: 0, y: 7 },
            { opacity: 1, y: 0, duration: 0.22, clearProps: 'opacity,transform' }
          )
        else if (previous !== top)
          gsap.fromTo(
            node,
            { y: previous - top },
            { y: 0, duration: 0.24, ease: 'power2.out', clearProps: 'transform' }
          )
      }
    }, list)
    previousPositions.current = positions
    return () => context.revert()
  }, [signature, reduced])

  const changeScope = (value: PlanScope) => {
    setScope(value)
    if (!parent || rank[value] <= rank[parent.scope ?? 'day']) setParentFilter(null)
    setStatus('all')
  }
  const openRelated = (value: PlanScope, parentId?: string) => {
    const children = all.filter((task) => task.parent_id === parentId)
    setScope(
      parentId &&
        value === 'week' &&
        !children.some((task) => task.scope === 'week') &&
        children.some((task) => (task.scope ?? 'day') === 'day')
        ? 'day'
        : value
    )
    setParentFilter(parentId ?? null)
    setStatus('all')
    setSearch('')
    list.current
      ?.closest('section')
      ?.scrollIntoView({ block: 'nearest', behavior: reduced ? 'auto' : 'smooth' })
  }

  return (
    <section className="workspace-page plans-page" data-plans-motion={reduced ? 'reduced' : 'full'}>
      <header className="plan-header">
        <PageToolbar />
        <div>
          <h1>个人计划</h1>
          <p>让每一天的行动，靠近想要的生活。</p>
        </div>
        <div className="plan-header-actions">
          <label className="plan-search">
            <Search size={16} />
            <input
              type="search"
              aria-label="搜索任务"
              placeholder="搜索任务…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <button className="plan-primary" onClick={() => openForm({})} disabled={save.isPending}>
            <Plus size={17} />
            新建任务
          </button>
        </div>
      </header>
      <PlanStats
        tasks={all}
        today={today}
        reduced={reduced}
        loading={plans.isLoading}
        unavailable={plans.isError && !plans.data}
        referenceDate={selected}
        onOpenScope={(value) => {
          setParentFilter(null)
          changeScope(value)
          setSearch('')
        }}
      />
      <PlanReminders tasks={all} />
      {plans.error && (
        <div className="plan-error plan-query-error" role="alert">
          读取计划失败：{plans.error.message}
          <button onClick={() => void plans.refetch()}>重新加载</button>
        </div>
      )}
      {error && (
        <div className="plan-error plan-query-error" role="alert">
          {error.message}
          <button
            onClick={() => {
              toggle.reset()
              updateStatus.reset()
              remove.reset()
            }}
          >
            关闭提示
          </button>
        </div>
      )}
      <div className="plan-workbench">
        <PlanCalendar
          tasks={searched}
          allTasks={all}
          selected={selected}
          today={today}
          onSelect={(date) => {
            setSelected(date)
            setParentFilter(null)
          }}
          actions={actions}
          loading={plans.isLoading}
        />
        <section className="plan-card plan-list-card" aria-label="个人任务清单">
          <div
            className="plan-scope-tabs"
            role="tablist"
            aria-label="计划类型"
            style={{ '--plan-tab-index': scopes.indexOf(scope) } as CSSProperties}
          >
            {scopes.map((value) => (
              <button
                key={value}
                type="button"
                id={`plan-tab-${value}`}
                role="tab"
                aria-selected={scope === value}
                aria-controls="plan-task-panel"
                tabIndex={scope === value ? 0 : -1}
                onClick={() => changeScope(value)}
                onKeyDown={(event) => {
                  let next = scopes.indexOf(value)
                  if (event.key === 'ArrowRight') next = (next + 1) % 3
                  else if (event.key === 'ArrowLeft') next = (next + 2) % 3
                  else if (event.key === 'Home') next = 0
                  else if (event.key === 'End') next = 2
                  else return
                  event.preventDefault()
                  changeScope(scopes[next])
                  document.getElementById(`plan-tab-${scopes[next]}`)?.focus()
                }}
              >
                {scopeLabels[value]}
              </button>
            ))}
          </div>
          <div
            className="plan-task-panel"
            id="plan-task-panel"
            role="tabpanel"
            aria-labelledby={`plan-tab-${scope}`}
          >
            <header className="plan-list-heading">
              <h2>
                {scopeLabels[scope]} <span>· {scoped.length}</span>
              </h2>
              <div className="plan-status-filters" aria-label="任务状态">
                {(
                  [
                    { value: 'all', label: '全部' },
                    { value: 'not_started', label: '未开始' },
                    { value: 'in_progress', label: '进行中' },
                    { value: 'completed', label: '已完成' },
                  ] as const
                ).map((item) => (
                  <button
                    key={item.value}
                    aria-pressed={status === item.value}
                    className={`state-${item.value}`}
                    aria-label={item.label}
                    onClick={() => setStatus(item.value)}
                  >
                    {item.label}
                    <span>
                      {item.value === 'all'
                        ? scoped.length
                        : scoped.filter((task) => taskStatus(task) === item.value).length}
                    </span>
                  </button>
                ))}
              </div>
            </header>
            {parent && (
              <div className="plan-filter-chip">
                <span>关联：{parent.title}</span>
                <button aria-label="清除上级计划筛选" onClick={() => setParentFilter(null)}>
                  <X size={13} />
                </button>
              </div>
            )}
            {plans.isLoading ? (
              <p className="plan-panel-note" role="status">
                正在读取计划…
              </p>
            ) : (
              !visible.length && (
                <PlanEmpty>
                  {query
                    ? '没有找到匹配的任务，试试其他关键词。'
                    : status === 'completed'
                      ? '完成的计划会留在这里。'
                      : parent
                        ? '还没有关联任务，可以在下方添加。'
                        : '留下一件想完成的事。'}
                </PlanEmpty>
              )
            )}
            <ul className="plan-task-rows plan-main-task-rows" ref={list} aria-busy={busy}>
              {visible.map((task) => (
                <PlanTaskItem
                  key={task.id}
                  task={task}
                  parent={all.find((item) => item.id === task.parent_id)}
                  {...actions}
                />
              ))}
            </ul>
            {backlog.length > 0 && (
              <details className="plan-backlog" open>
                <summary>未安排日期 · {backlog.length}</summary>
                <ul className="plan-task-rows">
                  {backlog.map((task) => (
                    <PlanTaskItem
                      key={task.id}
                      task={task}
                      parent={all.find((item) => item.id === task.parent_id)}
                      {...actions}
                    />
                  ))}
                </ul>
              </details>
            )}
            <form
              className="plan-quick-add"
              onSubmit={(event) => {
                event.preventDefault()
                if (draftTitle.trim()) openForm({ title: draftTitle.trim() })
              }}
            >
              <Plus size={16} />
              <input
                aria-label="添加任务标题"
                placeholder="添加任务"
                value={draftTitle}
                onChange={(event) => setDraftTitle(event.target.value)}
              />
              <button type="submit" aria-label="添加任务详情" disabled={!draftTitle.trim() || busy}>
                <Plus size={16} />
              </button>
            </form>
          </div>
        </section>
        <PlanProgress tasks={all} today={selected} onOpen={openRelated} loading={plans.isLoading} />
      </div>
      {form && (
        <Modal
          title={form.task ? '编辑任务' : '新建任务'}
          onClose={closeForm}
          className="plan-task-dialog"
          headerContent={
            <div className="plan-rich-heading">
              <span>
                <Plus size={26} />
              </span>
              <div>
                <h2>{form.task ? '编辑任务' : '新建任务'}</h2>
                <p>记录一个想要完成的事，让每一天更有方向。</p>
              </div>
            </div>
          }
        >
          <TaskForm
            task={form.task}
            tasks={all}
            initialScope={scope}
            initialTitle={form.title}
            initialParent={parentFilter ?? ''}
            initialDate={selected}
            busy={save.isPending}
            error={save.error}
            onCancel={closeForm}
            onSubmit={(draft) => save.mutate({ draft, task: form.task })}
          />
        </Modal>
      )}
    </section>
  )
}
