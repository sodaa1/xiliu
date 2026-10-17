import { useEffect, useRef, useState } from 'react'
import { isDesktop } from '../../desktop/bridge'
import { companionListen } from '../../desktop/companion'
import { createStandingMotion } from './standing-motion'
import { publicAsset } from '../../lib/deployment'

export function StandingMotion({
  dragging,
  reduced,
  enabled,
}: {
  dragging: boolean
  reduced: boolean
  enabled: boolean
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const renderer = useRef<ReturnType<typeof createStandingMotion> | null>(null)
  const held = useRef(dragging)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    held.current = dragging
    renderer.current?.dragging(dragging)
  }, [dragging])
  useEffect(() => {
    if (reduced || !enabled) return
    let disposed = false
    let observer: ResizeObserver | undefined
    let engine: ReturnType<typeof createStandingMotion> | undefined
    const image = new Image()
    image.onload = () => {
      if (disposed || !canvas.current) return
      const parent = canvas.current.parentElement!
      try {
        engine = createStandingMotion(
          canvas.current,
          image,
          (angle) => parent.style.setProperty('--pet-lean', `${angle}rad`),
          () => setReady(false)
        )
        renderer.current = engine
        const resize = () => {
          const rect = parent.getBoundingClientRect()
          engine?.resize(rect.width, rect.height)
        }
        resize()
        observer = new ResizeObserver(resize)
        observer.observe(parent)
        engine.dragging(held.current)
        setReady(true)
      } catch {
        setReady(false)
      }
    }
    image.src = publicAsset('companion/standing.png')
    return () => {
      disposed = true
      image.onload = null
      observer?.disconnect()
      engine?.destroy()
      if (renderer.current === engine) renderer.current = null
    }
  }, [reduced, enabled])
  useEffect(() => {
    let disposed = false,
      stop: (() => void) | undefined
    if (isDesktop()) {
      void companionListen<[number, number]>('position', ([x, y]) => {
        const dpr = window.devicePixelRatio || 1
        renderer.current?.move(x / dpr, y / dpr)
      })
        .then((unlisten) => {
          if (disposed) unlisten()
          else stop = unlisten
        })
        .catch(() => {})
    }
    const pointer = (event: PointerEvent) => {
      if (!isDesktop()) renderer.current?.move(event.clientX, event.clientY)
    }
    window.addEventListener('pointermove', pointer)
    return () => {
      disposed = true
      stop?.()
      window.removeEventListener('pointermove', pointer)
    }
  }, [])
  const visible = ready && enabled && !reduced
  return (
    <>
      <img src={publicAsset('companion/standing.png')} alt="" draggable={false} hidden={visible} />
      <canvas ref={canvas} className="pet-cloth-motion" aria-hidden="true" hidden={!visible} />
    </>
  )
}
