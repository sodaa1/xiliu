import { BookOpen, Flag, Target } from 'lucide-react'
import type { Task } from '../../../lib/workspace-api'
import {
  linkedProgress,
  plansInWeek,
  statusLabels,
  taskStatus,
  type PlanScope,
} from '../plan-utils'
import { PlanEmpty } from './PlanTaskItem'

function Progress({ tasks, plan }: { tasks: Task[]; plan: Task }) {
  const { done, total, percent } = linkedProgress(tasks, plan.id)
  const value = plan.completed ? 100 : percent
  return (
    <div className="plan-progress-line">
      <div
        className="plan-progress-track"
        role="progressbar"
        aria-label={`${plan.title}关联任务完成进度`}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={
          plan.completed
            ? '计划已完成'
            : total
              ? `${done} / ${total}，${percent}%`
              : statusLabels[taskStatus(plan)]
        }
      >
        <span style={{ width: `${value}%` }} />
      </div>
      <span>
        {plan.completed ? '已完成' : total ? `${done}/${total}` : statusLabels[taskStatus(plan)]}
      </span>
    </div>
  )
}

export function PlanProgress({
  tasks,
  today,
  onOpen,
  loading,
}: {
  tasks: Task[]
  today: Date
  onOpen: (scope: PlanScope, parentId?: string) => void
  loading: boolean
}) {
  const weekly = plansInWeek(tasks, today)
    .sort((a, b) => Number(a.completed) - Number(b.completed))
    .slice(0, 4)
  const goals = tasks
    .filter((task) => task.scope === 'goal')
    .sort((a, b) => Number(a.completed) - Number(b.completed))
    .slice(0, 3)
  return (
    <aside className="plan-progress-column" aria-label="目标与进度">
      <section className="plan-card plan-focus-card" aria-label="本周专注">
        <header className="plan-card-heading">
          <h2>本周专注</h2>
          <button onClick={() => onOpen('week')}>查看全部</button>
        </header>
        {loading ? (
          <p className="plan-panel-note">正在读取计划…</p>
        ) : weekly.length ? (
          <div className="plan-focus-list">
            {weekly.map((plan, i) => (
              <div className="plan-focus-item" key={plan.id}>
                <span className={`plan-mini-icon tone-${i % 3}`}>
                  <Flag size={15} />
                </span>
                <button onClick={() => onOpen('day', plan.id)}>{plan.title}</button>
                <Progress tasks={tasks} plan={plan} />
              </div>
            ))}
          </div>
        ) : (
          <PlanEmpty>这一周还没有计划，添加一件想推进的事。</PlanEmpty>
        )}
      </section>
      <section className="plan-card plan-goals-card" aria-label="长期目标进度">
        <header className="plan-card-heading">
          <h2>长期目标</h2>
          <button onClick={() => onOpen('goal')}>查看全部</button>
        </header>
        {loading ? (
          <p className="plan-panel-note">正在读取计划…</p>
        ) : goals.length ? (
          <div className="plan-goal-list">
            {goals.map((goal, i) => {
              const progress = linkedProgress(tasks, goal.id)
              const Icon = [Target, Flag, BookOpen][i % 3]
              return (
                <div className="plan-goal-item" key={goal.id}>
                  <span className={`plan-goal-icon tone-${i % 3}`}>
                    <Icon size={23} strokeWidth={1.6} />
                  </span>
                  <div className="plan-goal-copy">
                    <button onClick={() => onOpen('week', goal.id)}>{goal.title}</button>
                    <p>
                      {progress.total
                        ? `${progress.total} 项关联计划 · ${progress.done} 项已完成`
                        : '从一项关联计划开始'}
                    </p>
                    <Progress tasks={tasks} plan={goal} />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <PlanEmpty>把想去的方向，写成一个目标。</PlanEmpty>
        )}
      </section>
    </aside>
  )
}
