import { Box, Paper } from '@mui/material'
import { usePageHeader } from '@/ui/layout'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import contractsMarkdown from '@/content/CONTRACTS.md?raw'

export default function ContractDocsPage() {
  usePageHeader({
    title: 'Contracts',
    subtitle: 'API contract source of truth and hard rules',
  })

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, md: 3 },
          borderRadius: 2,
          border: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          '& h1': { fontSize: '1.75rem', mt: 0, mb: 2 },
          '& h2': { fontSize: '1.25rem', mt: 3, mb: 1.5 },
          '& p': { mb: 1.25 },
          '& ul, & ol': { pl: 3, mb: 1.25 },
          '& code': {
            px: 0.5,
            py: 0.25,
            borderRadius: 0.75,
            bgcolor: 'action.hover',
            fontFamily: 'monospace',
          },
          '& pre': {
            p: 1.5,
            borderRadius: 1,
            overflowX: 'auto',
            bgcolor: 'action.hover',
          },
        }}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{contractsMarkdown}</ReactMarkdown>
      </Paper>
    </Box>
  )
}
