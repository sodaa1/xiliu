import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { Workspace } from './app/Workspace'
import { usesHashRouting } from './lib/deployment'
import { isCloud } from './lib/runtime-mode'
import { AuthRoot } from './features/auth/AuthRoot'
import './styles/app.css'
import './styles/display-type.css'
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
