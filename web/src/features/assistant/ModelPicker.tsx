import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown, Cpu, Plus } from 'lucide-react'
import './model-picker.css'
import type { ModelConnection } from '../../lib/types'

export function ModelPicker({
  value,
  defaultModel,
  models,
  connections,
  provider,
  selectionDisabled,
  onChange,
  onConfigure,
}: {
  value: string
  defaultModel: string
  models: string[]
  connections?: ModelConnection[]
  provider?: string
  selectionDisabled: boolean
  onChange: (value: string) => void
  onConfigure: () => void
}) {
  const options = [
    { value: '', label: defaultModel || '选择模型', tag: '默认' },
    ...(connections?.length
      ? connections
          .filter((connection) => connection.enabled !== false)
          .map((connection) => ({
            value: connection.id,
            label: `${{ openai: 'OpenAI', deepseek: 'DeepSeek', mimo: '小米 MiMo', custom: '自定义' }[connection.provider]} · ${connection.label}`,
            tag: connection.api_key_set ? '' : '未配置',
          }))
      : [...new Set(models)].map((name) => ({ value: name, label: name, tag: '' }))),
  ]
  const selectedValue =
    connections?.find(
      (connection) => connection.model === value && connection.provider === provider
    )?.id ?? value
  const selected = Math.max(
    0,
    options.findIndex((option) => option.value === selectedValue)
  )
  const selectedProvider =
    connections?.find((connection) => connection.id === selectedValue)?.provider ?? provider
  const disabledSelection = connections?.find(
    (connection) => connection.id === selectedValue && connection.enabled === false
  )
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(selected)
  const [position, setPosition] = useState({ left: 0, bottom: 0, width: 288, maxHeight: 320 })
  const trigger = useRef<HTMLButtonElement>(null)
  const popup = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLDivElement>(null)
  const id = useId()
  function close(focus = false) {
    setOpen(false)
    if (focus) trigger.current?.focus()
  }
  function show() {
    const rect = trigger.current!.getBoundingClientRect()
    const width = Math.min(288, window.innerWidth - 24)
    setPosition({
      width,
      left: Math.max(12, Math.min(rect.left, window.innerWidth - width - 12)),
      bottom: window.innerHeight - rect.top + 8,
      maxHeight: Math.max(120, Math.min(360, rect.top - 20)),
    })
    setActive(selected)
    setOpen(true)
  }
  function choose(index: number) {
    if (selectionDisabled) return
    onChange(options[index].value)
    close(true)
  }
  function keyboard(event: KeyboardEvent) {
    if (event.key === 'Escape' && open) {
      event.preventDefault()
      close(true)
    } else if (['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' '].includes(event.key)) {
      event.preventDefault()
      if (!open) show()
      else if (event.key === 'ArrowDown') setActive((index) => (index + 1) % options.length)
      else if (event.key === 'ArrowUp')
        setActive((index) => (index + options.length - 1) % options.length)
      else if (event.key === 'Home') setActive(0)
      else if (event.key === 'End') setActive(options.length - 1)
      else choose(active)
    }
  }
  useEffect(() => {
    if (!open) return
    list.current?.focus()
    function outside(event: Event) {
      if (
        !popup.current?.contains(event.target as Node) &&
        !trigger.current?.contains(event.target as Node)
      )
        setOpen(false)
    }
    const dismiss = () => setOpen(false)
    function scroll(event: Event) {
      if (!popup.current?.contains(event.target as Node)) dismiss()
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('focusin', outside)
    document.addEventListener('scroll', scroll, true)
    window.addEventListener('resize', dismiss)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('focusin', outside)
      document.removeEventListener('scroll', scroll, true)
      window.removeEventListener('resize', dismiss)
    }
  }, [open])
  useEffect(() => {
    if (open)
      list.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [open, active])
  return (
    <>
      <button
        type="button"
        ref={trigger}
        className="model-picker-trigger"
        role="combobox"
        aria-label="当前对话模型"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => (open ? close() : show())}
        onKeyDown={keyboard}
      >
        <Cpu size={15} aria-hidden="true" />
        <span>
          {disabledSelection
            ? `${disabledSelection.label}（已停用，请切换）`
            : options[selected].label}
        </span>
        {!value && <small>默认</small>}
        <ChevronDown size={14} className={open ? 'open' : ''} aria-hidden="true" />
      </button>
      {open &&
        createPortal(
          <div className="model-picker-popover" ref={popup} style={position}>
            <div className="model-picker-heading">
              <span>对话模型</span>
              <small>
                {selectedProvider === 'deepseek'
                  ? 'DeepSeek'
                  : selectedProvider === 'openai'
                    ? 'OpenAI'
                    : selectedProvider === 'mimo'
                      ? '小米 MiMo'
                      : selectedProvider === 'custom'
                        ? '自定义'
                        : '未连接'}
              </small>
            </div>
            <div
              ref={list}
              role="listbox"
              id={id}
              tabIndex={-1}
              aria-label="可用模型"
              aria-activedescendant={`${id}-${active}`}
              className="model-picker-options"
              onKeyDown={keyboard}
            >
              {options.map((option, index) => (
                <div
                  key={option.value}
                  id={`${id}-${index}`}
                  role="option"
                  data-index={index}
                  aria-selected={selectedValue === option.value}
                  aria-disabled={selectionDisabled}
                  className={`model-picker-option ${active === index ? 'highlighted' : ''}`}
                  onPointerMove={() => setActive(index)}
                  onClick={() => choose(index)}
                >
                  <span>{option.label}</span>
                  {option.tag && <small>{option.tag}</small>}
                  {selectedValue === option.value && <Check size={15} aria-hidden="true" />}
                </div>
              ))}
            </div>
            {selectionDisabled && (
              <p className="model-picker-note">新建对话或当前回复结束后可切换模型。</p>
            )}
            <button
              type="button"
              className="model-picker-add"
              onKeyDown={(event) => {
                if (event.key === 'Escape') {
                  event.preventDefault()
                  close(true)
                }
              }}
              onClick={() => {
                close(true)
                onConfigure()
              }}
            >
              <Plus size={17} aria-hidden="true" />
              <span>添加或配置模型</span>
            </button>
          </div>,
          document.body
        )}
    </>
  )
}
