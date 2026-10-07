import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { ArrowUp, Command as CommandIcon } from 'lucide-react'
import type { Capability, Command } from '../../lib/types'

const fallback: Command[] = [{name:'clear',description:'清除模型上下文，保留历史'},{name:'compress',description:'压缩当前上下文'},{name:'skill',description:'使用一个已安装技能'},{name:'mcp',description:'使用一个已连接服务'}]
export function Composer({text,onText,onSend,disabled,commands,skills,mcp}: {text:string;onText:(text:string)=>void;onSend:()=>void;disabled:boolean;commands?:Command[];skills?:Capability[];mcp?:Capability[]}) {
  const [highlight,setHighlight] = useState(0), [dismissed,setDismissed] = useState(false)
  const trimmed = text.trimStart(), match = /^\/(skill|mcp)\s+(\S*)$/.exec(trimmed)
  const entries = match ? (match[1] === 'skill' ? skills ?? [] : mcp ?? []).filter((entry) => entry.name.startsWith(match[2])).map((entry) => ({name:entry.name,description:entry.description,value:`/${match[1]} ${entry.name} `})) : (commands ?? fallback).filter((entry) => !trimmed.includes(' ') && `/${entry.name}`.startsWith(trimmed)).map((entry) => ({...entry,value:`/${entry.name} `}))
  const open = trimmed.startsWith('/') && entries.length > 0 && !dismissed
  const chosen = highlight % Math.max(entries.length,1)
  function complete(index: number) {onText(entries[index].value);setDismissed(true);setHighlight(0)}
  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.nativeEvent.isComposing || event.keyCode === 229) return
    if (open && ['ArrowDown','ArrowUp','Enter','Tab'].includes(event.key)) {
      event.preventDefault()
      if (event.key === 'ArrowDown') setHighlight((chosen + 1) % entries.length)
      else if (event.key === 'ArrowUp') setHighlight((chosen + entries.length - 1) % entries.length)
      else complete(chosen)
    } else if (event.key === 'Escape') setDismissed(true)
    else if (event.key === 'Enter' && !event.shiftKey) {event.preventDefault();if (!disabled && text.trim()) onSend()}
  }
  return <div className="composer-area"><div className="composer-box">
    {open && <div id="slash-options" className="command-palette" role="listbox" aria-label="命令建议">{entries.map((entry,index) => <button key={entry.name} role="option" id={`suggestion-${index}`} aria-selected={chosen === index} className={chosen === index ? 'highlighted' : ''} onMouseDown={(event) => event.preventDefault()} onClick={() => complete(index)}><span>{match ? entry.name : `/${entry.name}`}</span><small>{entry.description}</small></button>)}</div>}
    <textarea aria-label="消息" placeholder="Ask anything…" value={text} disabled={disabled} onChange={(event) => {onText(event.target.value);setDismissed(false);setHighlight(0)}} onKeyDown={keyDown} rows={3} aria-controls={open ? 'slash-options' : undefined} aria-activedescendant={open ? `suggestion-${chosen}` : undefined}/>
    <div className="composer-toolbar"><span className="composer-hint"><CommandIcon size={15}/><span>输入 / 查看快捷命令</span></span><button className="send-button" aria-label="发送消息" onClick={onSend} disabled={disabled || !text.trim()}><ArrowUp size={23}/></button></div>
  </div><p className="composer-disclaimer">息流可能会出错，请核对重要信息。<span>Enter 发送 · Shift + Enter 换行</span></p></div>
}
