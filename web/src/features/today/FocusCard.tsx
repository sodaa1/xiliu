import { useEffect, useState } from 'react'
import { Clock3, Pause, Play } from 'lucide-react'
import { isDemo } from '../../lib/runtime-mode'
import { storageKey } from '../auth/session'
function day() {
  return new Date().toLocaleDateString('en-CA')
}
export function FocusCard() {
  const key = storageKey(isDemo ? 'xiliu-demo-home-focus-v1' : 'xiliu-home-focus-v1')
  const [value, setValue] = useState<{ day: string; seconds: number; started: number | null }>(
    () => {
      try {
        const raw = JSON.parse(localStorage.getItem(key) ?? 'null')
        if (
          raw?.day === day() &&
          Number.isFinite(raw.seconds) &&
          raw.seconds >= 0 &&
          (raw.started === null || (Number.isFinite(raw.started) && raw.started <= Date.now()))
        )
          return raw
      } catch {
        /* Start a fresh local timer. */
      }
      return { day: day(), seconds: 0, started: null }
    }
  )
  const [now, setNow] = useState(Date.now)
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      /* The active session still works in memory. */
    }
  }, [key, value])
  useEffect(() => {
    if (value.started === null) return
    const tick = () => {
      setNow(Date.now())
      if (value.day !== day()) setValue({ day: day(), seconds: 0, started: Date.now() })
    }
    const timer = window.setInterval(tick, 1000)
    return () => window.clearInterval(timer)
  }, [value.started, value.day])
  const seconds =
    value.seconds +
    (value.started === null ? 0 : Math.max(0, Math.floor((now - value.started) / 1000)))
  const label =
    seconds >= 3600 ? `${(seconds / 3600).toFixed(1)} 小时` : `${Math.floor(seconds / 60)} 分钟`
  return (
    <article className="wb-stat">
      <span className="wb-stat-icon violet">
        <Clock3 size={23} />
      </span>
      <div>
        <span className="wb-stat-label">专注时长</span>
        <strong aria-live="off">{label}</strong>
        <button
          className="wb-focus-toggle"
          aria-pressed={value.started !== null}
          onClick={() => {
            const time = Date.now()
            setNow(time)
            setValue((old) => ({
              ...old,
              day: day(),
              seconds:
                (old.day === day() ? old.seconds : 0) +
                (old.day !== day() || old.started === null
                  ? 0
                  : Math.max(0, Math.floor((time - old.started) / 1000))),
              started: old.started === null ? time : null,
            }))
          }}
        >
          {value.started === null ? <Play size={12} /> : <Pause size={12} />}{' '}
          {value.started === null ? '开始专注' : '暂停计时'}
        </button>
      </div>
    </article>
  )
}
