import { PanelsTopLeft, Sparkles } from 'lucide-react'
import { setHomeTheme, useHomeTheme } from './home-theme'
export function HomeThemeSwitch() {
  const theme = useHomeTheme()
  return (
    <div className="home-theme-switch" role="group" aria-label="首页主题">
      <button
        type="button"
        aria-pressed={theme === 'original'}
        aria-label="原有主题"
        title="原有主题"
        onClick={() => setHomeTheme('original')}
      >
        <Sparkles size={15} />
      </button>
      <button
        type="button"
        aria-pressed={theme === 'workbench'}
        aria-label="山水工作台"
        title="山水工作台"
        onClick={() => setHomeTheme('workbench')}
      >
        <PanelsTopLeft size={15} />
      </button>
    </div>
  )
}
