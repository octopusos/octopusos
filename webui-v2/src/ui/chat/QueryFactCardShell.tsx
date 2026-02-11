import { Box, Paper, Stack, Typography } from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import type { ReactNode } from 'react'

type QueryFactCardShellProps = {
  title: string
  subtitle?: string
  headline?: string
  badges?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  embedded?: boolean
}

export function QueryFactCardShell({
  title,
  subtitle,
  headline,
  badges,
  children,
  footer,
  embedded = false,
}: QueryFactCardShellProps) {
  const theme = useTheme()
  const cardBackground = theme.palette.mode === 'dark'
    ? 'radial-gradient(120% 120% at 8% 0%, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.02) 26%, rgba(12,14,22,0.96) 78%)'
    : 'linear-gradient(160deg, rgba(17,24,39,0.96) 0%, rgba(31,41,55,0.93) 55%, rgba(15,23,42,0.97) 100%)'
  return (
    <Paper
      sx={{
        mb: embedded ? 0 : 1.25,
        p: { xs: 1.5, sm: 2 },
        borderRadius: 3,
        border: `1px solid ${alpha(theme.palette.common.white, 0.18)}`,
        background: cardBackground,
        color: 'common.white',
        backdropFilter: 'blur(10px)',
        overflow: 'hidden',
      }}
    >
      <Stack spacing={1}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          {badges}
        </Stack>
        {subtitle && (
          <Typography variant="body2" sx={{ opacity: 0.85 }}>
            {subtitle}
          </Typography>
        )}
        {headline && (
          <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
            {headline}
          </Typography>
        )}
        {children && <Box>{children}</Box>}
        {footer && (
          <Typography variant="caption" sx={{ opacity: 0.72 }}>
            {footer}
          </Typography>
        )}
      </Stack>
    </Paper>
  )
}
