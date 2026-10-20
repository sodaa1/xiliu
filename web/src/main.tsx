import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { Workspace } from './app/Workspace'
import { usesHashRouting } from './lib/deployment'
import { isCloud } from './lib/runtime-mode'
import { AuthRoot } from './features/auth/AuthRoot'
import './styles/app.css'
import './styles/display-type.css'
import './styles/typography.css'
import './features/feed/feed-workbench.css'
import './styles/ui-workbench.css'
import './features/content/collection-workbench.css'
import './features/knowledge/library-workbench.css'
import './features/settings/settings-workbench.css'
import './features/automations/automations-workbench.css'
import './features/onboarding/onboarding-workbench.css'
import './features/launch/launch-workbench.css'
import './features/companion/companion-workbench.css'
const Router = usesHashRouting() ? HashRouter : BrowserRouter
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Router>
      {isCloud ? (
        <AuthRoot>
          <Workspace />
        </AuthRoot>
      ) : (
        <Workspace />
      )}
    </Router>
  </StrictMode>
)
