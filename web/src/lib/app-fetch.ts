import { isDemo } from './runtime-mode'

export async function appFetch(input: string, init?: RequestInit): Promise<Response> {
  if (isDemo) {
    const { handleDemoRequest } = await import('../features/demo/handler')
    return handleDemoRequest(input, init)
  }
  return fetch(input, init)
}
