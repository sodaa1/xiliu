import { useEffect, useRef, useState } from 'react'
import { useReducedMotion } from '../../lib/useReducedMotion'
import type { CompanionStatus } from '../../desktop/companion'
import type { PetForm } from './live2d-bundle'
import { readModel, watchModels } from './model-storage'
import type { mountLive2D } from './live2d-runtime'
export function PetAvatar({
  form = 'chibi',
  phase = 'idle',
  onError,
}: {
  form?: PetForm
  phase?: CompanionStatus['phase']
  onError?: (message: string) => void
}) {
  const root = useRef<HTMLSpanElement>(null),
    canvas = useRef<HTMLCanvasElement>(null)
  const controller = useRef<Awaited<ReturnType<typeof mountLive2D>> | null>(null)
  const [loaded, setLoaded] = useState('')
  const [revision, setRevision] = useState(0)
  const reduced = useReducedMotion()
  const renderKey = `${form}:${revision}:${reduced}`
  const ready = loaded === renderKey
  useEffect(() => watchModels(() => setRevision((value) => value + 1)), [])
  useEffect(() => {
    let disposed = false
    let local: Awaited<ReturnType<typeof mountLive2D>> | undefined
    let observer: ResizeObserver | undefined
    const start = async () => {
      const bundle = await readModel(form)
      if (!bundle || disposed || !canvas.current || !root.current) return
      const { mountLive2D } = await import('./live2d-runtime')
      if (disposed) return
      const rect = root.current!.getBoundingClientRect()
      const engine = await mountLive2D(
        canvas.current!,
        bundle,
        Math.max(1, rect.width),
        Math.max(1, rect.height),
        reduced
      )
      if (disposed) {
        engine.destroy()
        return
      }
      local = engine
      controller.current = engine
      setLoaded(renderKey)
      observer = new ResizeObserver((entries) => {
        const rect = entries[0]?.contentRect
        if (rect) engine.resize(Math.max(1, rect.width), Math.max(1, rect.height))
      })
      observer.observe(root.current!)
    }
    void start().catch((failure) => {
      if (!disposed) onError?.((failure as Error).message)
    })
    return () => {
      disposed = true
      observer?.disconnect()
      local?.destroy()
      if (controller.current === local) controller.current = null
    }
  }, [form, revision, reduced, renderKey, onError])
  useEffect(() => {
    if (ready) controller.current?.phase(phase)
  }, [phase, ready])
  return (
    <span
      ref={root}
      className="pet-avatar"
      data-renderer={ready ? 'live2d' : 'image'}
      onPointerMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect()
        controller.current?.focus(event.clientX - rect.left, event.clientY - rect.top)
      }}
    >
      <img src={`/companion/${form}.png`} alt="" draggable={false} hidden={ready} />
      <canvas
        ref={canvas}
        aria-hidden="true"
        style={{ visibility: ready ? 'visible' : 'hidden' }}
      />
    </span>
  )
}
