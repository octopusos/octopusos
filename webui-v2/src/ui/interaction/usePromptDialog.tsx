import { useCallback, useRef, useState } from 'react'
import { Dialog, DialogActions, DialogContent, DialogTitle, Button, Typography } from '@/ui'

type DialogColor = 'primary' | 'warning' | 'error'
type DialogKind = 'alert' | 'confirm'

interface BasePromptOptions {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  color?: DialogColor
  testId?: string
}

interface PromptRequest extends BasePromptOptions {
  kind: DialogKind
  resolve: (value: boolean) => void
}

export interface UsePromptDialogReturn {
  alert: (options: BasePromptOptions) => Promise<void>
  confirm: (options: BasePromptOptions) => Promise<boolean>
  dialog: JSX.Element
}

export function usePromptDialog(): UsePromptDialogReturn {
  const queueRef = useRef<PromptRequest[]>([])
  const [activeRequest, setActiveRequest] = useState<PromptRequest | null>(null)

  const showNext = useCallback(() => {
    setActiveRequest((current) => {
      if (current) return current
      return queueRef.current.shift() ?? null
    })
  }, [])

  const enqueue = useCallback((request: PromptRequest) => {
    queueRef.current.push(request)
    showNext()
  }, [showNext])

  const finish = useCallback((value: boolean) => {
    setActiveRequest((current) => {
      if (current) {
        current.resolve(value)
      }
      return null
    })

    requestAnimationFrame(() => {
      showNext()
    })
  }, [showNext])

  const alert = useCallback((options: BasePromptOptions) => {
    return new Promise<void>((resolve) => {
      enqueue({
        ...options,
        kind: 'alert',
        resolve: () => resolve(),
      })
    })
  }, [enqueue])

  const confirm = useCallback((options: BasePromptOptions) => {
    return new Promise<boolean>((resolve) => {
      enqueue({
        ...options,
        kind: 'confirm',
        resolve,
      })
    })
  }, [enqueue])

  const dialog = (
    <Dialog
      open={Boolean(activeRequest)}
      onClose={() => finish(false)}
      maxWidth="xs"
      fullWidth
      data-testid={activeRequest?.testId || 'product-dialog'}
    >
      <DialogTitle data-testid="product-dialog-title">{activeRequest?.title}</DialogTitle>
      <DialogContent>
        <Typography data-testid="product-dialog-message" variant="body2" color="text.secondary">
          {activeRequest?.message}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 2 }}>
        {activeRequest?.kind === 'confirm' ? (
          <Button data-testid="product-dialog-cancel" onClick={() => finish(false)}>
            {activeRequest.cancelText || 'Cancel'}
          </Button>
        ) : null}
        <Button
          data-testid="product-dialog-confirm"
          variant="contained"
          color={activeRequest?.color || 'primary'}
          onClick={() => finish(true)}
        >
          {activeRequest?.confirmText || 'OK'}
        </Button>
      </DialogActions>
    </Dialog>
  )

  return { alert, confirm, dialog }
}
