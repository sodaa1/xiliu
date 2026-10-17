export function publicAsset(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`
}

export function usesHashRouting(): boolean {
  return import.meta.env.MODE === 'demo' && import.meta.env.VITE_DEMO_ROUTER === 'hash'
}
