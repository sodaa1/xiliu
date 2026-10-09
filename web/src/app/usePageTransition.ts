import { useLayoutEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import type { Location } from 'react-router-dom'

const pages = ['/today', '/assistant', '/feed', '/inbox', '/knowledge']
const easing = 'cubic-bezier(0.16, 1, 0.3, 1)'

// Keep the current route mounted until its exit finishes. ChatProvider lives above
// this boundary, and same-page query changes / settings overlays never replay it.
export function usePageTransition(
  target: Location,
  root: RefObject<HTMLDivElement | null>,
  reducedMotion: boolean
) {
  const [displayed, setDisplayed] = useState(target)
  const current = useRef(target)
  const exit = useRef<Animation | null>(null)
  const enter = useRef<Animation | null>(null)
  const pending = useRef<{ fade: boolean; direction: number } | null>(null)

  useLayoutEffect(() => {
    let cancelled = false
    enter.current?.cancel()
    exit.current?.cancel()
    pending.current = null
    const previous = current.current
    const fade = previous.pathname === '/' || target.pathname === '/'
    const element = fade ? root.current : root.current?.querySelector<HTMLElement>('.main-stage')
    const commit = () => {
      if (cancelled) return
      current.current = target
      setDisplayed(target)
    }
    if (previous.pathname === target.pathname || reducedMotion || !element?.animate) {
      commit()
      return () => {
        cancelled = true
      }
    }
    const direction = pages.indexOf(target.pathname) < pages.indexOf(previous.pathname) ? -1 : 1
    element.dataset.routePhase = 'exit'
    exit.current = element.animate(
      [
        { opacity: 1, transform: 'translateY(0)' },
        { opacity: 0, transform: `translateY(${fade ? 0 : -14 * direction}px)` },
      ],
      { duration: fade ? 220 : 140, easing, fill: 'forwards' }
    )
    void exit.current.finished
      .then(() => {
        if (cancelled) return
        pending.current = { fade, direction }
        commit()
      })
      .catch(() => {
        // Cancellation by a newer route is stale; other animation failures must
        // still leave navigation usable.
        commit()
      })
    return () => {
      cancelled = true
      exit.current?.cancel()
      delete element.dataset.routePhase
    }
  }, [target, root, reducedMotion])

  useLayoutEffect(() => {
    const motion = pending.current
    pending.current = null
    exit.current?.cancel()
    if (!motion) return
    const element = motion.fade
      ? root.current
      : root.current?.querySelector<HTMLElement>('.main-stage')
    if (!element?.animate || reducedMotion) return
    delete element.dataset.routePhase
    element.dataset.routePhase = 'enter'
    const animation = element.animate(
      [
        { opacity: 0, transform: `translateY(${motion.fade ? 0 : 24 * motion.direction}px)` },
        { opacity: 1, transform: 'translateY(0)' },
      ],
      { duration: motion.fade ? 380 : 320, easing, fill: 'both' }
    )
    enter.current = animation
    void animation.finished
      .then(() => {
        animation.cancel()
        delete element.dataset.routePhase
      })
      .catch(() => {})
    return () => {
      animation.cancel()
      delete element.dataset.routePhase
    }
  }, [displayed, root, reducedMotion])

  return displayed
}
