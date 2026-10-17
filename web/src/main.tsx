import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './app/App'
import { usesHashRouting } from './lib/deployment'
import './styles/app.css'
import './styles/display-type.css'
const query = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10_000 } } })
const Router = usesHashRouting() ? HashRouter : BrowserRouter
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={query}>
      <Router>
        <App />
      </Router>
    </QueryClientProvider>
  </StrictMode>
)
