import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ArrowUpRight, BookOpen, CheckCircle2, Circle, Inbox } from 'lucide-react'
import { safeHttpUrl, workspaceApi } from '../../lib/workspace-api'
import { taskStatus } from '../plans/plan-utils'
const statusLabels = { not_started: '未开始', in_progress: '进行中', completed: '已完成' }
export function TodayWorkspace() {
  const daily = useQuery({ queryKey: ['today'], queryFn: workspaceApi.today })
  const inbox = useQuery({ queryKey: ['inbox'], queryFn: workspaceApi.inbox })
  return (
    <div className="today-workspace-summary">
      <section className="today-workspace-tasks" aria-label="今日要做">
        <header>
          <h2>
            今日要做 <small>{daily.data?.tasks?.length ?? '—'}</small>
          </h2>
          <Link to="/plans">
            查看计划 <ArrowUpRight size={14} />
          </Link>
        </header>
        {daily.isLoading ? (
          <p role="status">正在读取任务…</p>
        ) : daily.error ? (
          <p role="alert">{daily.error.message}</p>
        ) : !daily.data?.tasks?.length ? (
          <p className="today-summary-empty">今天还没有安排，先从一件小事开始。</p>
        ) : (
          daily.data.tasks.slice(0, 5).map((task) => (
            <Link className="today-summary-task" to="/plans" key={task.id}>
              {task.completed ? <CheckCircle2 size={16} /> : <Circle size={16} />}
              <strong>{task.title}</strong>
              <span className={`task-state-${taskStatus(task)}`}>
                {statusLabels[taskStatus(task)]}
              </span>
            </Link>
          ))
        )}
        <section className="today-workspace-inbox" aria-label="待处理">
          <header>
            <h2>
              待处理 <small>{inbox.data?.length ?? '—'}</small>
            </h2>
            <Link to="/inbox">
              打开收件箱 <ArrowUpRight size={14} />
            </Link>
          </header>
          {inbox.isLoading ? (
            <p role="status">正在读取收件箱…</p>
          ) : inbox.error ? (
            <p role="alert">{inbox.error.message}</p>
          ) : !inbox.data?.length ? (
            <p className="today-summary-empty">收件箱已清空，有新想法时随手收录。</p>
          ) : (
            inbox.data.slice(0, 3).map((item) => (
              <Link
                className="today-summary-task"
                to={`/inbox?item=${encodeURIComponent(item.id)}`}
                key={item.id}
              >
                <Inbox size={16} />
                <strong>{item.title}</strong>
                <span>
                  {item.processing_status === 'pending'
                    ? '正在整理'
                    : item.processing_status === 'failed'
                      ? '整理失败'
                      : '待整理'}
                </span>
              </Link>
            ))
          )}
        </section>
      </section>
      <section className="today-workspace-feed" aria-label="值得关注">
        <header>
          <h2>值得关注</h2>
          <Link to="/feed">
            查看资讯 <ArrowUpRight size={14} />
          </Link>
        </header>
        {daily.isLoading ? (
          <p role="status">正在读取资讯…</p>
        ) : daily.error ? (
          <p role="alert">{daily.error.message}</p>
        ) : !daily.data?.feed?.length ? (
          <p className="today-summary-empty">暂时没有新资讯，稍后再来看看。</p>
        ) : (
          daily.data.feed.slice(0, 3).map((item) => {
            const url = safeHttpUrl(item.url)
            return (
              <article className="today-summary-news" key={item.id}>
                <small>
                  {item.source === 'github'
                    ? 'GitHub 热门项目'
                    : item.source === 'manual'
                      ? '我的资讯'
                      : '资讯'}
                </small>
                {url ? (
                  <a href={url} target="_blank" rel="noreferrer">
                    {item.title}
                    <ArrowUpRight size={14} />
                  </a>
                ) : (
                  <Link to="/feed">{item.title}</Link>
                )}
                <p>{item.summary}</p>
              </article>
            )
          })
        )}
        <Link className="today-knowledge-link" to="/knowledge">
          <BookOpen size={17} />
          <span>
            接续上一次思考<small>回到已经整理好的资料</small>
          </span>
          <ArrowUpRight size={15} />
        </Link>
      </section>
    </div>
  )
}
