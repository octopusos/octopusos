/**
 * DetailDrawer - 详情统一抽屉
 *
 * 🔒 硬契约：所有详情查看必须使用此组件
 *
 * 目标：
 * - 统一抽屉宽度（600px）
 * - 统一 header 样式（标题 + 关闭按钮）
 * - 统一内边距
 * - 统一 footer 操作区（可选）
 */

import { useRef, useEffect } from 'react'
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Divider,
} from '@mui/material'
import { K, useTextTranslation } from '@/ui/text'
import { CloseIcon } from '@/ui/icons'

export interface DetailDrawerProps {
  /**
   * 抽屉是否打开
   */
  open: boolean

  /**
   * 关闭回调
   */
  onClose: () => void

  /**
   * 抽屉标题
   */
  title: string

  /**
   * 副标题（可选）
   */
  subtitle?: string

  /**
   * 抽屉宽度（默认 600px）
   */
  width?: number

  /**
   * Footer 操作区（可选）
   */
  actions?: React.ReactNode

  /**
   * 详情内容
   */
  children: React.ReactNode
}

/**
 * DetailDrawer 组件
 *
 * 🔒 详情查看必须使用此组件
 *
 * 特性：
 * - 默认 600px 宽度（适合详情展示）
 * - 右侧滑出
 * - Header: 标题 + 副标题 + 关闭按钮
 * - Content: 自动滚动
 * - Footer: 可选操作区（编辑/删除等）
 *
 * @example
 * ```tsx
 * <DetailDrawer
 *   open={open}
 *   onClose={handleClose}
 *   title="Task Detail"
 *   subtitle="#12345"
 *   actions={
 *     <>
 *       <Button onClick={handleEdit}>Edit</Button>
 *       <Button onClick={handleDelete} color="error">Delete</Button>
 *     </>
 *   }
 * >
 *   <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
 *     <Box>
 *       <Typography variant="caption" color="text.secondary">Name</Typography>
 *       <Typography variant="body1">Sample Task</Typography>
 *     </Box>
 *     <Box>
 *       <Typography variant="caption" color="text.secondary">Status</Typography>
 *       <Typography variant="body1">Active</Typography>
 *     </Box>
 *   </Box>
 * </DetailDrawer>
 * ```
 */
export function DetailDrawer({
  open,
  onClose,
  title,
  subtitle,
  width = 600,
  actions,
  children,
}: DetailDrawerProps) {
  const { t } = useTextTranslation()
  const lastActiveElementRef = useRef<HTMLElement | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    if (open) {
      lastActiveElementRef.current = document.activeElement as HTMLElement
      // Move focus into the drawer to avoid aria-hidden focus warnings on background content.
      const timer = window.setTimeout(() => {
        closeButtonRef.current?.focus()
      }, 0)
      return () => window.clearTimeout(timer)
    }
  }, [open])

  const handleClose = () => {
    // Best-effort focus restore for trigger element.
    try {
      lastActiveElementRef.current?.focus()
    } catch {
      // noop
    }
    onClose()
  }

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={handleClose}
      sx={{
        zIndex: (theme) => theme.zIndex.modal + 2,
        '& .MuiDrawer-paper': {
          width,
          maxWidth: '100%',
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          p: 3,
          pb: 2,
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h6" component="div" gutterBottom>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <IconButton
          ref={closeButtonRef}
          aria-label={t(K.common.close)}
          onClick={handleClose}
          size="small"
          sx={{ ml: 2, mt: -0.5 }}
        >
          <CloseIcon />
        </IconButton>
      </Box>

      <Divider />

      {/* Content */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 3,
        }}
      >
        {children}
      </Box>

      {/* Footer (optional) */}
      {actions && (
        <>
          <Divider />
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 1,
              justifyContent: 'flex-end',
              p: 3,
              pt: 2,
            }}
          >
            {actions}
          </Box>
        </>
      )}
    </Drawer>
  )
}
