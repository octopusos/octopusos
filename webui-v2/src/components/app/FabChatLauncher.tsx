import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  ButtonBase,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  Drawer,
  Fab,
  IconButton,
  Paper,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  AddIcon,
  ChatBubbleIcon,
  CloseIcon,
  FavoriteIcon,
  PublicIcon,
  WorkIcon,
} from '@/ui/icons'
import { useTextTranslation } from '@/ui/text'
import { useFrontdeskChatStore } from '@/features/frontdesk'
import { CHAT_PRESET_LIST, type ChatPreset, type ChatPresetId } from '@/features/chat/presets/chat_presets'

const PRESET_ICONS: Record<ChatPresetId, JSX.Element> = {
  frontdesk: <PublicIcon />,
  life: <FavoriteIcon />,
  work: <WorkIcon />,
  free: <ChatBubbleIcon />,
}

export function FabChatLauncher() {
  const { t } = useTextTranslation()
  const navigate = useNavigate()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'))
  const { open: openFrontdesk } = useFrontdeskChatStore()
  const [open, setOpen] = useState(false)

  const cards = useMemo(() => CHAT_PRESET_LIST, [])

  const handleLaunch = (preset: ChatPreset) => {
    setOpen(false)
    if (preset.id === 'frontdesk') {
      openFrontdesk()
      return
    }
    navigate('/chat', { state: { presetId: preset.id } })
  }

  const content = (
    <Stack spacing={2} sx={{ py: 1 }} data-testid="fab-chat-quick-actions">
      {cards.map((preset) => (
        <Paper
          key={preset.id}
          variant="outlined"
          sx={{
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <ButtonBase
            onClick={() => handleLaunch(preset)}
            data-testid={`fab-chat-action-${preset.id}`}
            aria-label={preset.id === 'frontdesk' ? t('component.fabChatLauncher.openFrontdesk') : undefined}
            sx={{
              width: '100%',
              textAlign: 'left',
              p: 2,
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Box
              sx={{
                width: 44,
                height: 44,
                borderRadius: 1.5,
                bgcolor: 'action.hover',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {PRESET_ICONS[preset.id]}
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                {preset.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {preset.subtitle}
              </Typography>
            </Box>
          </ButtonBase>
        </Paper>
      ))}
    </Stack>
  )

  return (
    <>
      <Box
        data-testid="frontdesk-open"
        onClick={() => setOpen(true)}
        sx={{
          position: 'fixed',
          right: 24,
          bottom: 24,
          zIndex: (theme) => theme.zIndex.appBar + 2,
          display: 'inline-flex',
        }}
      >
        <Fab
          color="primary"
          aria-label={t('component.fabChatLauncher.openFrontdesk')}
          onClick={() => setOpen(true)}
          data-testid="fab-chat-launcher"
        >
          <AddIcon />
        </Fab>
      </Box>

      {isMobile ? (
        <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
          <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {t('component.fabChatLauncher.quickActions')}
            <Box sx={{ flex: 1 }} />
            <IconButton onClick={() => setOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent>{content}</DialogContent>
        </Dialog>
      ) : (
        <Drawer
          anchor="right"
          open={open}
          onClose={() => setOpen(false)}
          sx={{
            '& .MuiDrawer-paper': {
              width: 360,
              maxWidth: '100%',
              p: 3,
            },
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              Quick Actions
            </Typography>
            <Box sx={{ flex: 1 }} />
            <IconButton onClick={() => setOpen(false)} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Divider sx={{ my: 2 }} />
          {content}
        </Drawer>
      )}
    </>
  )
}
