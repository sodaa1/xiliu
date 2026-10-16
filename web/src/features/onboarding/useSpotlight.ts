import { useEffect, useState } from 'react'
export function useSpotlight(target: string, running: boolean) {
  const [layout, setLayout] = useState({
    box: null as DOMRect | null,
    target: '',
    width: window.innerWidth,
    height: window.innerHeight,
  })
  useEffect(() => {
    if (!running) return
    let frame = 0
    let revealed: Element | null = null
    const measure = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        const element = target ? document.querySelector('[data-onboarding="' + target + '"]') : null
        if (element && element !== revealed) {
          element.scrollIntoView({ block: 'nearest', inline: 'nearest' })
          revealed = element
        }
        const rect = element?.getBoundingClientRect()
        setLayout((previous) => {
          const box = rect?.width && rect.height ? rect : null
          if (
            previous.target === target &&
            previous.width === window.innerWidth &&
            previous.height === window.innerHeight &&
            previous.box?.x === box?.x &&
            previous.box?.y === box?.y &&
            previous.box?.width === box?.width &&
            previous.box?.height === box?.height
          )
            return previous
          return { box, target, width: window.innerWidth, height: window.innerHeight }
        })
      })
    }
    measure()
    const observer = new MutationObserver(measure)
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['data-onboarding', 'data-route-path'],
    })
    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [target, running])
  return { ...layout, box: target && running && layout.target === target ? layout.box : null }
}
