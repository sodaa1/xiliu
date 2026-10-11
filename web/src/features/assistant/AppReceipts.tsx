import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { api } from '../../lib/api'

interface Receipt {
  status: string
  confirmation_id?: string
  description?: string
  arguments?: Record<string, unknown>
  data?: { job_id?: string }
}

function ArchiveProgress({ jobId }: { jobId: string }) {
  const job = useQuery({
    queryKey: ['archive-job', jobId],
    queryFn: () => api.archiveJob(jobId),
    refetchInterval: (query) =>
      ['pending', 'running'].includes(query.state.data?.status ?? 'pending') ? 1500 : false,
    retry: 1,
  })
  const labels: Record<string, string> = {
    pending: '正在生成标签，随后自动归档…',
    running: '正在归档…',
    completed: '标签已生成，已归档到知识库。',
    partial: '部分资料未完成，请检查收件箱中的处理结果。',
    conflict: '资料已有人工修改，已保留修改并停止自动归档。',
    failed: '归档未完成，请到收件箱查看资料和处理结果。',
    cancelled: '已停止自动归档。',
  }
  const counts = job.data?.counts
  const unfinished = counts
    ? (counts.failed ?? 0) + (counts.conflict ?? 0) + (counts.cancelled ?? 0)
    : 0
  return (
    <p role="status">
      {job.error ? '归档进度暂不可用。' : labels[job.data?.status ?? 'pending']}
      {counts && !job.error &&
        ` 已归档 ${counts.completed ?? 0}/${counts.total}；待处理 ${(counts.pending ?? 0) + (counts.running ?? 0)}；未完成 ${unfinished}。`}
    </p>
  )
}

function ReviewAction({ receipt, sessionId }: { receipt: Receipt; sessionId: string }) {
  const cache = useQueryClient()
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const confirm = useMutation({
    mutationFn: () => api.confirmAction(sessionId, receipt.confirmation_id!),
    onSuccess: async () => {
      setOpen(false)
      await cache.invalidateQueries()
    },
  })
  if (confirm.isSuccess)
    return <p role="status">{confirm.data.ok ? '操作已完成。' : '操作未完成，请检查结果。'}</p>
  return (
    <>
      <button className="secondary-button" onClick={() => setOpen(true)}>
        审核操作
      </button>
      {open && (
        <Modal title="确认操作" onClose={close}>
          <p>{receipt.description ?? '请确认本次操作'}</p>
          <dl>
            {Object.entries(receipt.arguments ?? {}).map(([key, value]) => (
              <div key={key}>
                <dt>
                  {key.endsWith('_id')
                    ? '目标'
                    : key === 'enabled'
                      ? '启用状态'
                      : key === 'prompt'
                        ? '任务内容'
                        : key === 'name'
                          ? '名称'
                          : '参数'}
                </dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
          {confirm.error && <p role="alert">{confirm.error.message}</p>}
          <div className="form-actions">
            <button className="secondary-button" onClick={close} disabled={confirm.isPending}>
              取消
            </button>
            <button
              className="primary-button"
              onClick={() => confirm.mutate()}
              disabled={confirm.isPending}
            >
              {confirm.isPending ? '正在执行…' : '确认执行'}
            </button>
          </div>
        </Modal>
      )}
    </>
  )
}

export function AppReceipts({
  metadata,
  sessionId,
  resolved = [],
}: {
  metadata: string
  sessionId: string
  resolved?: string[]
}) {
  let receipts: Receipt[] = []
  try {
    const raw: unknown = JSON.parse(metadata).app_receipts
    if (Array.isArray(raw))
      receipts = raw.filter((r) => r && typeof r === 'object').slice(0, 32) as Receipt[]
  } catch {
    /* Historical messages have no action receipts. */
  }
  return (
    <>
      {receipts.map((receipt) =>
        receipt.confirmation_id &&
        receipt.status === 'confirmation_required' &&
        !resolved.includes(receipt.confirmation_id) ? (
          <ReviewAction key={receipt.confirmation_id} receipt={receipt} sessionId={sessionId} />
        ) : receipt.data?.job_id ? (
          <ArchiveProgress key={receipt.data.job_id} jobId={receipt.data.job_id} />
        ) : null
      )}
    </>
  )
}
