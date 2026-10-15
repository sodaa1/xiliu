import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, X } from 'lucide-react'
import { fileBase64, workspaceApi, type ContentItem } from '../../lib/workspace-api'
import { ContentDialog } from './ContentDialog'

export function CaptureDialog({
  onClose,
  onSaved,
}: {
  onClose: () => void
  onSaved: (item: ContentItem) => void
}) {
  return (
    <ContentDialog title="添加到 Inbox" onClose={onClose}>
      <CaptureForm onClose={onClose} onSaved={onSaved} />
    </ContentDialog>
  )
}

export function CaptureForm({
  onClose,
  onSaved,
  draftKey,
}: {
  onClose: () => void
  onSaved: (item: ContentItem) => void
  draftKey?: string
}) {
  const submitting = useRef(false)
  const [text, setText] = useState(() => {
      try {
        return draftKey ? (sessionStorage.getItem(draftKey) ?? '') : ''
      } catch {
        return ''
      }
    }),
    [file, setFile] = useState<File | null>(null),
    [useAI, setUseAI] = useState(true),
    [fileError, setFileError] = useState(''),
    [dragging, setDragging] = useState(false)
  useEffect(() => {
    if (!draftKey) return
    try {
      if (text) sessionStorage.setItem(draftKey, text)
      else sessionStorage.removeItem(draftKey)
    } catch {
      /* The in-memory draft remains usable. */
    }
  }, [text, draftKey])
  const chooseFile = (value?: File) => {
    if (submitting.current) return
    if (!value) return
    if (value.size > 20 * 1024 * 1024) {
      setFileError('文件不能超过 20 MiB。')
      return
    }
    setFile(value)
    setFileError('')
  }
  const create = useMutation({
    mutationFn: async () => {
      if (!text.trim() && !file) throw new Error('请粘贴文字、链接，或选择一个文件。')
      return workspaceApi.importContent({
        ...(text.trim() ? { text: text.trim() } : {}),
        ...(file ? { filename: file.name, data_base64: await fileBase64(file) } : {}),
        use_ai: useAI,
      })
    },
    onSuccess: (item) => {
      setText('')
      setFile(null)
      onSaved(item)
    },
    onSettled: () => {
      submitting.current = false
    },
  })
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (submitting.current) return
        submitting.current = true
        create.mutate()
      }}
    >
      <label>
        文字或链接
        <textarea
          rows={5}
          disabled={create.isPending}
          value={text}
          onChange={(event) => {
            if (!submitting.current) setText(event.target.value)
          }}
          placeholder="粘贴一段文字，或一个 https:// 链接"
          onPaste={(event) => {
            const value = event.clipboardData.files[0]
            if (value) {
              event.preventDefault()
              chooseFile(value)
            }
          }}
        />
      </label>
      <label
        className={`content-dropzone ${dragging ? 'dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          chooseFile(event.dataTransfer.files[0])
        }}
      >
        <Upload size={24} />
        <span>{file ? file.name : '拖放文件到这里，或点击选择'}</span>
        <small>单个文件最多 20 MiB · 保留原件</small>
        <input
          type="file"
          disabled={create.isPending}
          aria-label="选择文件"
          onChange={(event) => chooseFile(event.target.files?.[0])}
        />
      </label>
      {file && (
        <button
          className="secondary-button"
          type="button"
          disabled={create.isPending}
          onClick={() => {
            setFile(null)
            setFileError('')
          }}
        >
          <X size={14} />
          移除文件
        </button>
      )}
      <label className="content-checkbox">
        <input
          type="checkbox"
          disabled={create.isPending}
          checked={useAI}
          onChange={(event) => setUseAI(event.target.checked)}
        />
        使用 AI 整理
      </label>
      <p className="section-description">
        保存后在后台生成标题、摘要与标签，并按文件夹规则归类。关闭 AI 时使用本地内容整理。
      </p>
      {(fileError || create.error) && (
        <p role="alert" className="workspace-error">
          {fileError || create.error?.message}
        </p>
      )}
      <div className="editor-actions">
        <button className="secondary-button" type="button" onClick={onClose}>
          取消
        </button>
        <button className="primary-button" disabled={create.isPending || !!fileError}>
          {create.isPending ? '保存中…' : '收进 Inbox'}
        </button>
      </div>
    </form>
  )
}
