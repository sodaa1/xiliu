import { Sparkles } from 'lucide-react'
export function Brand({large = false}: {large?: boolean}) {
  return <span className={`brand-mark ${large ? 'brand-large' : ''}`} aria-hidden="true"><Sparkles strokeWidth={1.8}/></span>
}
