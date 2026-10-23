import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { isDemo } from '../../lib/runtime-mode'
import { DemoBar } from '../demo/DemoBar'
import { resetDemoExperience } from '../demo/reset'
import { WorkspaceControls, WorkspaceSidebar } from '../../components/WorkspaceChrome'

export function WorkbenchShell({ children, inert }: { children: ReactNode; inert: boolean }) {
  const navigate = useNavigate()
  const cache = useQueryClient()
  return (
    <div className="app-shell workbench-shell workspace-v2">
      <WorkspaceSidebar inert={inert} />
      <main className="main-stage" inert={inert || undefined}>
        {isDemo && (
          <DemoBar
            onReset={async () => {
              await resetDemoExperience(cache)
              navigate('/today', { replace: true })
            }}
          />
        )}
        <WorkspaceControls />
        {children}
      </main>
    </div>
  )
}
