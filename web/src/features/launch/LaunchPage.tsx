import { Link } from 'react-router-dom'
import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { Brand } from '../../components/Brand'
import { GalaxyCanvas } from './GalaxyCanvas'
import { useReducedMotion } from '../../lib/useReducedMotion'
import './launch.css'

export function LaunchPage() {
  const reducedMotion = useReducedMotion()
  const [introComplete, setIntroComplete] = useState(false)
  const ready = introComplete || reducedMotion
  return (
    <section className={`launch-page ${ready ? 'intro-complete' : ''}`}>
      <GalaxyCanvas introComplete={ready} />
      <div className="launch-vignette" aria-hidden="true" />
      {!ready && (
        <button className="launch-skip" onClick={() => setIntroComplete(true)}>
          跳过开场 <ArrowRight size={14} />
        </button>
      )}
      <div
        className="launch-content"
        onAnimationEnd={(event) => {
          if (event.target === event.currentTarget && event.animationName === 'launch-reveal')
            setIntroComplete(true)
        }}
      >
        <Brand large />
        <h1 className="launch-title">
          <span className="launch-script-wordmark">xiliu</span>
        </h1>
        <span className="launch-signature">息流</span>
        <p>让灵感相连。</p>
        <Link to="/today" className="btn launch-enter">
          <span>
            开始使用
            <ArrowRight size={18} />
          </span>
        </Link>
      </div>
      <span className="launch-version">xiliu · v0.1</span>
    </section>
  )
}
