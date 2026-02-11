import { ReactNode, useEffect, useMemo, useRef } from 'react'
import { useSnackbar } from 'notistack'
import { getToken } from '@/platform/auth/adminToken'
import { evaluateWriteAccess, getCachedRuntimeMode } from '@/platform/auth/writeAccess'

interface AuthGateProps {
  children: ReactNode
}

export default function AuthGate({ children }: AuthGateProps) {
  const { enqueueSnackbar } = useSnackbar()
  const warnedRef = useRef<string | null>(null)

  const writeAccess = useMemo(
    () => evaluateWriteAccess(getCachedRuntimeMode(), getToken()),
    []
  )

  const warning = useMemo(() => {
    if (writeAccess.reason === 'TOKEN_REQUIRED') {
      return '当前模式需要 Admin Token 才能执行写操作。'
    }
    if (writeAccess.reason === 'MODE_READONLY') {
      return '当前运行模式为只读，写操作已禁用。'
    }
    if (writeAccess.reason === 'MODE_UNKNOWN') {
      return '未识别运行模式，已按只读策略保护写操作。'
    }
    return null
  }, [writeAccess.reason])

  useEffect(() => {
    if (!warning) {
      warnedRef.current = null
      return
    }
    if (warnedRef.current === warning) {
      return
    }

    warnedRef.current = warning
    enqueueSnackbar(warning, {
      variant: 'warning',
      autoHideDuration: 4000,
      preventDuplicate: true,
    })
  }, [warning, enqueueSnackbar])

  return <>{children}</>
}
