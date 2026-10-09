import { usePreferences } from '../lib/preferences'
export function Avatar({ large = false }: { large?: boolean }) {
  const preferences = usePreferences()
  return (
    <span className={`profile-avatar ${large ? 'large' : ''}`}>
      {preferences.avatar ? (
        <img src={preferences.avatar} alt="个人头像" />
      ) : (
        Array.from(preferences.displayName || '溪')[0]
      )}
    </span>
  )
}
