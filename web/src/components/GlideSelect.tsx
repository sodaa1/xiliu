import { useEffect, useId, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown } from 'lucide-react'
import './glide-select.css'

export interface GlideOption {
  value: string
  label: string
  tag?: string
}
interface Props {
  options: GlideOption[]
  value?: string
  defaultValue?: string
  onChange?: (value: string, option: GlideOption) => void
  ariaLabel: string
  showTags?: boolean
  accentColor?: string
  surfaceColor?: string
  highlightColor?: string
  textColor?: string
  size?: 'sm' | 'md' | 'lg'
  radius?: number
  menuWidth?: number
  placement?: 'top' | 'bottom'
  align?: 'left' | 'right'
  popDuration?: number
  glideDuration?: number
  rememberPosition?: boolean
  disabled?: boolean
}
export function GlideSelect({
  options,
  value,
  defaultValue,
  onChange,
  ariaLabel,
  showTags = false,
  accentColor = 'var(--accent)',
  surfaceColor = 'var(--surface)',
  highlightColor = 'var(--accent-soft)',
  textColor = 'var(--text)',
  size = 'md',
  radius = 10,
  menuWidth = 240,
  placement = 'bottom',
  align = 'left',
  popDuration = 180,
  glideDuration = 220,
  rememberPosition = true,
  disabled = false,
}: Props) {
  const [local, setLocal] = useState(defaultValue ?? options[0]?.value ?? '')
  const selected = value ?? local
  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === selected)
  )
  const [open, setOpen] = useState(false),
    [active, setActive] = useState(selectedIndex)
  const [position, setPosition] = useState({ left: 0, top: 0, width: menuWidth, maxHeight: 320 })
  const trigger = useRef<HTMLButtonElement>(null),
    menu = useRef<HTMLDivElement>(null)
  const id = useId(),
    search = useRef({ value: '', at: 0 })
  const rowHeight = size === 'sm' ? 36 : size === 'lg' ? 48 : 42
  const visible = open && !disabled && options.length > 0
  const close = (focus = false) => {
    setOpen(false)
    if (focus) trigger.current?.focus()
  }
  function show() {
    if (disabled || !options.length) return
    const rect = trigger.current!.getBoundingClientRect()
    const width = Math.max(120, Math.min(menuWidth, window.innerWidth - 24))
    const height = Math.min(options.length * rowHeight + 12, 320)
    const below = window.innerHeight - rect.bottom - 12
    const above = rect.top - 12
    const top =
      placement === 'top' ? above >= height || above > below : below < height && above > below
    const maxHeight = Math.max(80, Math.min(320, top ? above : below))
    setPosition({
      width,
      maxHeight,
      left: Math.max(
        12,
        Math.min(align === 'right' ? rect.right - width : rect.left, window.innerWidth - width - 12)
      ),
      top: top ? Math.max(12, rect.top - Math.min(height, maxHeight) - 6) : rect.bottom + 6,
    })
    setActive(rememberPosition ? selectedIndex : 0)
    setOpen(true)
  }
  useEffect(() => {
    if (!visible) return
    menu.current?.focus()
    function outside(event: PointerEvent) {
      if (
        !trigger.current?.contains(event.target as Node) &&
        !menu.current?.contains(event.target as Node)
      )
        setOpen(false)
    }
    const dismiss = () => setOpen(false)
    function scroll(event: Event) {
      if (!menu.current?.contains(event.target as Node)) dismiss()
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('scroll', scroll, true)
    window.addEventListener('resize', dismiss)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('scroll', scroll, true)
      window.removeEventListener('resize', dismiss)
    }
  }, [visible])
  useEffect(() => {
    if (visible)
      menu.current
        ?.querySelector<HTMLElement>(`[data-index="${active}"]`)
        ?.scrollIntoView({ block: 'nearest' })
  }, [active, visible])
  function choose(index: number) {
    const option = options[index]
    if (!option) return
    setLocal(option.value)
    onChange?.(option.value, option)
    close(true)
  }
  function keyboard(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      if (visible) {
        event.preventDefault()
        close(true)
      }
      return
    }
    if (event.key === 'Tab') {
      if (visible) close(true)
      return
    }
    if (['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key))
      event.preventDefault()
    if (!visible) {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) show()
      return
    }
    if (event.key === 'ArrowDown') setActive((index) => (index + 1) % options.length)
    else if (event.key === 'ArrowUp')
      setActive((index) => (index + options.length - 1) % options.length)
    else if (event.key === 'Home') setActive(0)
    else if (event.key === 'End') setActive(options.length - 1)
    else if (event.key === 'Enter' || event.key === ' ') choose(active)
    else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
      const now = Date.now()
      search.current.value =
        (now - search.current.at < 700 ? search.current.value : '') + event.key.toLocaleLowerCase()
      search.current.at = now
      const found = options.findIndex((option) =>
        option.label.toLocaleLowerCase().startsWith(search.current.value)
      )
      if (found >= 0) setActive(found)
    }
  }
  const style = {
    '--glide-accent': accentColor,
    '--glide-surface': surfaceColor,
    '--glide-highlight': highlightColor,
    '--glide-text': textColor,
    '--glide-radius': `${radius}px`,
    '--glide-pop': `${popDuration}ms`,
    '--glide-time': `${glideDuration}ms`,
    '--glide-row': `${rowHeight}px`,
  } as CSSProperties
  return (
    <>
      <button
        type="button"
        ref={trigger}
        className={`glide-select glide-${size}`}
        style={style}
        role="combobox"
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={visible}
        aria-controls={visible ? id : undefined}
        disabled={disabled || !options.length}
        onClick={() => (visible ? close() : show())}
        onKeyDown={keyboard}
      >
        <span>{options[selectedIndex]?.label ?? '请选择'}</span>
        <ChevronDown size={15} className={visible ? 'glide-chevron open' : 'glide-chevron'} />
      </button>
      {visible &&
        createPortal(
          <div
            className="glide-menu"
            ref={menu}
            id={id}
            role="listbox"
            tabIndex={-1}
            aria-label={ariaLabel}
            aria-activedescendant={`${id}-${active}`}
            onKeyDown={keyboard}
            style={{ ...style, ...position }}
          >
            <div className="glide-options">
              <span
                className="glide-highlight"
                aria-hidden="true"
                style={{ transform: `translateY(${active * rowHeight}px)` }}
              />
              {options.map((option, index) => (
                <div
                  role="option"
                  id={`${id}-${index}`}
                  key={option.value}
                  data-index={index}
                  aria-selected={selected === option.value}
                  className={`glide-option ${active === index ? 'highlighted' : ''}`}
                  onPointerMove={() => setActive(index)}
                  onClick={() => choose(index)}
                >
                  <span>{option.label}</span>
                  {showTags && option.tag && <small>{option.tag}</small>}
                  {selected === option.value && <Check size={15} aria-hidden="true" />}
                </div>
              ))}
            </div>
          </div>,
          document.body
        )}
    </>
  )
}
export default GlideSelect
