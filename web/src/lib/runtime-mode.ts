// Only the dedicated build can enable the sandbox; URLs cannot switch a real app.
export const isDemo = import.meta.env.MODE === 'demo'
export const isCloud = import.meta.env.MODE === 'cloud'
