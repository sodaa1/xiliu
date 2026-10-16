import { DemoError, demoUnavailable } from './types'

export async function handleDemoRequest(input: string, init?: RequestInit): Promise<Response> {
  if (init?.signal?.aborted) throw new DOMException('请求已停止', 'AbortError')
  const url = new URL(input, 'https://demo.invalid')
  if (url.pathname === '/api/health') return Response.json({ status: 'ok', demo: true })
  return Response.json(
    { error: { code: new DemoError(demoUnavailable).code, message: demoUnavailable } },
    { status: 400 }
  )
}
