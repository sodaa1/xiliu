import { setChatSource, useChatSource, useCloudSession } from './session'

export function TrialSelector({ busy, onConfigure }: { busy: boolean; onConfigure: () => void }) {
  const session = useCloudSession()
  const source = useChatSource()
  if (!session) return null
  const { trial } = session
  return (
    <div className="cloud-trial-selector" role="group" aria-label="本次回复使用的模型">
      <label>
        <input
          type="radio"
          name="model-source"
          checked={source === 'own'}
          disabled={busy}
          onChange={() => setChatSource('own')}
        />
        自有 API
      </label>
      <label>
        <input
          type="radio"
          name="model-source"
          checked={source === 'trial'}
          disabled={busy || !trial.enabled || trial.remaining < 1}
          onChange={() => setChatSource('trial')}
        />
        公共试用（剩余 {trial.remaining}/{trial.limit} 次）
      </label>
      <button type="button" onClick={onConfigure}>
        配置自有 API
      </button>
      <p>
        {!trial.enabled
          ? '公共试用尚未开放，连接自有 API 即可使用。'
          : trial.remaining < 1
            ? '累计 5 次试用已用完，请切换自有 API 继续。'
            : '每个账号累计 5 次；开始生成后停止或超时仍会计次，连接失败会返还。'}
      </p>
    </div>
  )
}
