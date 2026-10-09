import { useRef } from 'react'

export function ResizeHandle({
  label,
  value,
  min,
  max,
  onChange,
  vertical = false,
}: {
  label: string
  value: number
  min: number
  max: number
  onChange: (value: number) => void
  vertical?: boolean
}) {
  const start = useRef<{ coordinate: number; value: number } | null>(null)
  const change = (next: number) => onChange(Math.max(min, Math.min(max, next)))
  return (
    <div
      className={`resize-handle ${vertical ? 'resize-height' : 'resize-width'}`}
      role="separator"
      aria-label={label}
      aria-orientation={vertical ? 'horizontal' : 'vertical'}
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={value}
      tabIndex={0}
      onPointerDown={(event) => {
        event.preventDefault()
        event.currentTarget.setPointerCapture(event.pointerId)
        start.current = { coordinate: vertical ? event.clientY : event.clientX, value }
      }}
      onPointerMove={(event) => {
        if (!start.current) return
        const delta = (vertical ? event.clientY : event.clientX) - start.current.coordinate
        change(start.current.value + delta * (vertical ? -1 : 1))
      }}
      onPointerUp={() => {
        start.current = null
      }}
      onPointerCancel={() => {
        start.current = null
      }}
      onLostPointerCapture={() => {
        start.current = null
      }}
      onKeyDown={(event) => {
        const keys = vertical ? ['ArrowDown', 'ArrowUp'] : ['ArrowLeft', 'ArrowRight']
        if (keys.includes(event.key) || ['Home', 'End'].includes(event.key)) {
          event.preventDefault()
          change(
            event.key === 'Home'
              ? min
              : event.key === 'End'
                ? max
                : value + (event.key === keys[0] ? -10 : 10)
          )
        }
      }}
    />
  )
}
