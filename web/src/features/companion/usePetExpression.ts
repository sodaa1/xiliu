import { useEffect, useState } from 'react'
import type { CompanionStatus } from '../../desktop/companion'

export type PetExpression = 'neutral' | 'blink' | 'happy' | 'surprised'
export function usePetExpression({
  dragging,
  active,
  phase,
  reduced,
  raster,
}: {
  dragging: boolean
  active: boolean
  phase: CompanionStatus['phase']
  reduced: boolean
  raster: boolean
}) {
  const [blink, setBlink] = useState(false)
  const engaged = active || phase === 'success'
  useEffect(() => {
    let wait: number | undefined, close: number | undefined
    const stop = () => {
      window.clearTimeout(wait)
      window.clearTimeout(close)
      setBlink(false)
    }
    const schedule = () => {
      if (document.hidden || reduced || !raster || dragging || engaged) return
      wait = window.setTimeout(
        () => {
          setBlink(true)
          close = window.setTimeout(() => {
            setBlink(false)
            schedule()
          }, 140)
        },
        4000 + Math.random() * 2500
      )
    }
    const visibility = () => {
      stop()
      schedule()
    }
    schedule()
    document.addEventListener('visibilitychange', visibility)
    return () => {
      stop()
      document.removeEventListener('visibilitychange', visibility)
    }
  }, [dragging, engaged, raster, reduced])
  const expression: PetExpression = dragging
    ? 'surprised'
    : engaged
      ? 'happy'
      : blink && !reduced && raster
        ? 'blink'
        : 'neutral'
  return expression
}
