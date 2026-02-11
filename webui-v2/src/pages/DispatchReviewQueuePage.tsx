import { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Button,
  Chip,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useSearchParams } from 'react-router-dom'
import { dispatchService, type DispatchProposal, type DispatchJob } from '@/services'
import { getToken, setToken } from '@/platform/auth/adminToken'
import { K, useTextTranslation } from '@/ui/text'

export default function DispatchReviewQueuePage() {
  const { t } = useTextTranslation()
  const [searchParams] = useSearchParams()
  const [proposals, setProposals] = useState<DispatchProposal[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [adminDialogOpen, setAdminDialogOpen] = useState(false)
  const [adminTokenInput, setAdminTokenInput] = useState('')
  const [reviewComment, setReviewComment] = useState('')
  const [jobs, setJobs] = useState<DispatchJob[]>([])
  const [jobLoading, setJobLoading] = useState(false)

  const selectedProposal = useMemo(
    () => proposals.find(proposal => proposal.proposal_id === selectedId) || null,
    [proposals, selectedId]
  )
  const selectedJob = useMemo(() => jobs[0] || null, [jobs])

  const loadProposals = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await dispatchService.listProposals(statusFilter, 50)
      setProposals(response.proposals || [])
    } catch (err) {
      console.error('[DispatchReview] Failed to load proposals', err)
      setError(t(K.page.dispatchReviewQueue.failedLoadProposals))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProposals()
  }, [statusFilter])

  useEffect(() => {
    const proposalFromQuery = searchParams.get('proposal')
    if (proposalFromQuery) {
      setSelectedId(proposalFromQuery)
    } else if (proposals.length > 0 && !selectedId) {
      setSelectedId(proposals[0].proposal_id)
    }
  }, [proposals, searchParams, selectedId])

  useEffect(() => {
    const loadJobs = async () => {
      if (!selectedProposal) {
        setJobs([])
        return
      }
      try {
        setJobLoading(true)
        const response = await dispatchService.listJobs({ proposal_id: selectedProposal.proposal_id, limit: 1 })
        setJobs(response.jobs || [])
      } catch (err) {
        console.error('[DispatchReview] Failed to load jobs', err)
      } finally {
        setJobLoading(false)
      }
    }
    loadJobs()
  }, [selectedProposal])

  const ensureAdminToken = (): string | null => {
    const existing = getToken()
    if (existing) return existing
    setAdminDialogOpen(true)
    return null
  }

  const handleSaveAdminToken = () => {
    if (adminTokenInput.trim()) {
      setToken(adminTokenInput.trim())
      setAdminDialogOpen(false)
      setAdminTokenInput('')
    }
  }

  const handleApprove = async () => {
    if (!selectedProposal) return
    const token = ensureAdminToken()
    if (!token) return

    await dispatchService.approveProposal(selectedProposal.proposal_id, reviewComment || null, token)
    setReviewComment('')
    await loadProposals()
  }

  const handleReject = async () => {
    if (!selectedProposal) return
    const token = ensureAdminToken()
    if (!token) return

    await dispatchService.rejectProposal(selectedProposal.proposal_id, reviewComment || null, token)
    setReviewComment('')
    await loadProposals()
  }

  const handleExecute = async () => {
    if (!selectedProposal) return
    const token = ensureAdminToken()
    if (!token) return

    await dispatchService.executeProposal(selectedProposal.proposal_id, token)
    await loadProposals()
  }

  const handleRetry = async () => {
    if (!selectedJob) return
    const token = ensureAdminToken()
    if (!token) return
    await dispatchService.retryJob(selectedJob.job_id, token)
    await loadProposals()
  }

  const handleRollback = async () => {
    if (!selectedJob) return
    const token = ensureAdminToken()
    if (!token) return
    await dispatchService.rollbackJob(selectedJob.job_id, token)
    await loadProposals()
  }

  return (
    <Box sx={{ display: 'flex', gap: 2, height: '100%' }}>
      <Paper sx={{ width: 360, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="h6">{t(K.page.dispatchReviewQueue.title)}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t(K.page.dispatchReviewQueue.subtitle)}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
            {[
              { value: 'pending', label: t(K.page.dispatchReviewQueue.statusPending) },
              { value: 'approved', label: t(K.page.dispatchReviewQueue.statusApproved) },
              { value: 'rejected', label: t(K.page.dispatchReviewQueue.statusRejected) },
            ].map(status => (
              <Chip
                key={status.value}
                label={status.label}
                size="small"
                variant={statusFilter === status.value ? 'filled' : 'outlined'}
                onClick={() => setStatusFilter(status.value)}
              />
            ))}
          </Stack>
        </Box>
        <Divider />
        <Box sx={{ flex: 1, overflowY: 'auto' }}>
          {loading && (
            <Typography variant="body2" sx={{ p: 2 }}>
              {t(K.common.loading)}
            </Typography>
          )}
          {error && (
            <Typography variant="body2" color="error" sx={{ p: 2 }}>
              {error}
            </Typography>
          )}
          <List disablePadding>
            {proposals.map(proposal => (
              <ListItemButton
                key={proposal.proposal_id}
                selected={proposal.proposal_id === selectedId}
                onClick={() => setSelectedId(proposal.proposal_id)}
              >
                <ListItemText
                  primary={proposal.proposal_type}
                  secondary={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip size="small" label={proposal.risk_level} />
                      <Typography variant="caption">{proposal.created_at}</Typography>
                    </Stack>
                  }
                />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Paper>

      <Paper sx={{ flex: 1, p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {selectedProposal ? (
          <>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h6">{selectedProposal.proposal_type}</Typography>
              <Chip label={selectedProposal.status} size="small" />
              <Chip label={`risk: ${selectedProposal.risk_level}`} size="small" color="warning" />
              <Chip
                label={selectedProposal.auto_execute_eligible ? t(K.page.dispatchReviewQueue.autoLabel) : t(K.page.dispatchReviewQueue.manualLabel)}
                size="small"
                color={selectedProposal.auto_execute_eligible ? 'success' : 'default'}
              />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {t(K.page.dispatchReviewQueue.proposalId)}: {selectedProposal.proposal_id}
            </Typography>
            <Divider />
            <Box>
              <Typography variant="subtitle2">{t(K.page.dispatchReviewQueue.reason)}</Typography>
              <Typography variant="body2">{selectedProposal.reason || t(K.page.dispatchReviewQueue.noReasonProvided)}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">{t(K.page.dispatchReviewQueue.payload)}</Typography>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                <pre style={{ margin: 0 }}>{JSON.stringify(selectedProposal.payload, null, 2)}</pre>
              </Paper>
            </Box>
            <Box>
              <Typography variant="subtitle2">{t(K.page.dispatchReviewQueue.evidence)}</Typography>
              <Typography variant="body2">
                {selectedProposal.evidence_refs?.length ? selectedProposal.evidence_refs.join(', ') : t(K.page.dispatchReviewQueue.none)}
              </Typography>
            </Box>

            <Box>
              <Typography variant="subtitle2">{t(K.page.dispatchReviewQueue.executionJob)}</Typography>
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
                {jobLoading && <Typography variant="body2">{t(K.page.dispatchReviewQueue.loadingJob)}</Typography>}
                {!jobLoading && !selectedJob && (
                  <Typography variant="body2" color="text.secondary">
                    {t(K.page.dispatchReviewQueue.noExecutionJob)}
                  </Typography>
                )}
                {selectedJob && (
                  <Stack spacing={1}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip size="small" label={selectedJob.status} />
                      <Typography variant="caption">{t(K.page.dispatchReviewQueue.jobId)}: {selectedJob.job_id}</Typography>
                    </Stack>
                    <Typography variant="caption">
                      {t(K.page.dispatchReviewQueue.attempts)}: {selectedJob.attempt}/{selectedJob.max_attempts}
                    </Typography>
                    {selectedJob.last_error_code && (
                      <Typography variant="caption" color="error">
                        {selectedJob.last_error_code}: {selectedJob.last_error_message}
                      </Typography>
                    )}
                  </Stack>
                )}
              </Paper>
            </Box>

            <TextField
              label={t(K.page.dispatchReviewQueue.reviewComment)}
              value={reviewComment}
              onChange={(event) => setReviewComment(event.target.value)}
              multiline
              minRows={2}
            />

            <Stack direction="row" spacing={2}>
              <Button variant="contained" onClick={handleApprove} disabled={selectedProposal.status !== 'pending'}>
                {t(K.page.dispatchReviewQueue.approve)}
              </Button>
              <Button variant="outlined" color="error" onClick={handleReject} disabled={selectedProposal.status !== 'pending'}>
                {t(K.page.dispatchReviewQueue.reject)}
              </Button>
              <Button variant="outlined" onClick={handleExecute} disabled={selectedProposal.status !== 'approved'}>
                {t(K.page.dispatchReviewQueue.execute)}
              </Button>
              <Button variant="outlined" onClick={handleRetry} disabled={!selectedJob || selectedJob.status !== 'failed'}>
                {t(K.common.retry)}
              </Button>
              <Button
                variant="outlined"
                onClick={handleRollback}
                disabled={!selectedJob || selectedJob.status !== 'succeeded'}
              >
                {t(K.page.dispatchReviewQueue.rollback)}
              </Button>
            </Stack>
          </>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {t(K.page.dispatchReviewQueue.selectProposal)}
          </Typography>
        )}
      </Paper>

      <Dialog open={adminDialogOpen} onClose={() => setAdminDialogOpen(false)}>
        <DialogTitle>{t(K.page.dispatchReviewQueue.adminTokenRequired)}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t(K.page.dispatchReviewQueue.adminToken)}
            type="password"
            fullWidth
            value={adminTokenInput}
            onChange={(event) => setAdminTokenInput(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAdminDialogOpen(false)}>{t(K.common.cancel)}</Button>
          <Button onClick={handleSaveAdminToken} variant="contained">{t(K.common.save)}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
