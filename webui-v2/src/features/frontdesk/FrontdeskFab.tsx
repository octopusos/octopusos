import { Badge, Fab, Tooltip } from '@mui/material'
import { ChatBubbleIcon } from '@/ui/icons'
import { useFrontdeskChatStore } from './frontdeskChatStore'

export function FrontdeskFab() {
  const { open } = useFrontdeskChatStore()
  const unreadCount = 0

  return (
    <Tooltip title="Frontdesk Chat" placement="left">
      <Badge
        badgeContent={unreadCount}
        color="error"
        overlap="circular"
        sx={{
          position: 'fixed',
          right: 24,
          bottom: 24,
          zIndex: (theme) => theme.zIndex.appBar + 2,
        }}
      >
        <Fab color="primary" aria-label="frontdesk" onClick={open}>
          <ChatBubbleIcon />
        </Fab>
      </Badge>
    </Tooltip>
  )
}
