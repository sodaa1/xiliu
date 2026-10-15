import { useEffect, useState } from 'react'
import type { CompanionStatus } from '../../desktop/companion'

export type PetExpression = 'neutral' | 'blink' | 'happy' | 'surprised'
export function usePetExpression({
  dragging,
  active,
  hover = false,
  phase,
  reduced,
  raster,
}: {
  dragging: boolean
  active: boolean
  hover?: boolean
  phase: CompanionStatus['phase']
  reduced: boolean
  raster: boolean
}) {
  const [idleFace, setIdleFace] = useState<PetExpression>('neutral')
  const [hoverSmile, setHoverSmile] = useState(false)
  useEffect(() => {
    if (!hover) return
    setHoverSmile(true)
    const timeout = window.setTimeout(() => setHoverSmile(false), 1200)
    return () => window.clearTimeout(timeout)
  }, [hover])
  const engaged = active || (hover && hoverSmile) || phase === 'success'
  useEffect(() => {
    let wait: number | undefined,
      finish: number | undefined,
      cycle = 0
    const stop = () => {
      window.clearTimeout(wait)
      window.clearTimeout(finish)
      setIdleFace('neutral')
    }
    const schedule = () => {
      if (document.hidden || reduced || !raster || dragging || engaged) return
      wait = window.setTimeout(
        () => {
          const face = cycle % 3 === 1 ? 'happy' : 'blink'
          setIdleFace(face)
          finish = window.setTimeout(
            () => {
              setIdleFace('neutral')
              cycle++
              schedule()
            },
            face === 'happy' ? 1400 : 220
          )
        },
        cycle === 0 ? 1500 + Math.random() * 1200 : 3500 + Math.random() * 1800
      )
    }
    const visibility = () => {
      stop()
      cycle = 0
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
      : !reduced && raster
        ? idleFace
        : 'neutral'
  return expression
}
