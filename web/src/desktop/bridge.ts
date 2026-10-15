type DesktopWindow = {
  minimize(): Promise<void>
  toggleMaximize(): Promise<void>
  close(): Promise<void>
}
declare global {
  interface Window {
    __TAURI__?: {
      window?: { getCurrentWindow(): DesktopWindow }
      core?: { invoke(command: string, args: Record<string, unknown>): Promise<unknown> }
      event?: { listen<T>(event: string, handler: (event: { payload: T }) => void): Promise<() => void> }
    }
  }
}
export const isDesktop = () => Boolean(window.__TAURI__)
export const desktopWindow = () => window.__TAURI__?.window?.getCurrentWindow()
export async function saveDesktopPreferences(json: string): Promise<void> {
  if (!isDesktop()) return
  const core = window.__TAURI__?.core
  if (!core) throw new Error('桌面偏好存储接口不可用。')
  await core.invoke('save_preferences', { json })
}
export async function persistDesktopSidebar(collapsed: boolean): Promise<void> {
  if (!isDesktop()) return
  const core = window.__TAURI__?.core
  if (!core) throw new Error('桌面侧栏存储接口不可用。')
  await core.invoke('save_sidebar', { collapsed })
}
