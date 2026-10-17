import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './App'

export function Workspace() {
  const [query] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
      })
  )
  return (
    <QueryClientProvider client={query}>
      <App />
    </QueryClientProvider>
  )
}
