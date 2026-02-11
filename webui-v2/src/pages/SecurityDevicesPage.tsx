import { useCallback, useEffect, useMemo, useState } from 'react'
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from '@mui/material'
import { usePageHeader } from '@/ui/layout'
import { CardCollectionWrap, ItemCard, type ItemCardAction, type ItemCardMeta } from '@/ui'
import { K, useTextTranslation } from '@/ui/text'
import { getToken } from '@/platform/auth/adminToken'
import { httpClient } from '@/platform/http'

type DeviceRequest = {
  id: string
  device_fingerprint: string
  device_name: string
  status: string
  created_at: number
  updated_at: number
}

type PairingCode = {
  pairing_code: string
  expires_at_ms: number
  ttl_sec: number
}

async function toQrDataUrl(text: string): Promise<string> {
  const QRCode = await import('qrcode')
  return QRCode.toDataURL(text, { errorCorrectionLevel: 'M', margin: 1, scale: 6 })
}

export default function SecurityDevicesPage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t(K.nav.securityDevices),
    subtitle: t(K.page.securityDevices.subtitle),
  })

  const [loading, setLoading] = useState(false)
  const [pending, setPending] = useState<DeviceRequest[]>([])
  const [approved, setApproved] = useState<DeviceRequest[]>([])
  const [error, setError] = useState<string>('')

  const [pairDialogOpen, setPairDialogOpen] = useState(false)
  const [pairingCode, setPairingCode] = useState<PairingCode | null>(null)
  const [qrDataUrl, setQrDataUrl] = useState<string>('')

  const [ttlInput, setTtlInput] = useState('60')

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const token = getToken()
      if (!token) {
        setError(t(K.page.securityDevices.adminTokenRequired))
        setPending([])
        setApproved([])
        return
      }
      setError('')
      const [p, a] = await Promise.all([
        httpClient.get('/api/devices/pending', { headers: { 'X-Admin-Token': token } }),
        httpClient.get('/api/devices/approved', { headers: { 'X-Admin-Token': token } }),
      ])
      setPending(Array.isArray(p.data?.items) ? p.data.items : [])
      setApproved(Array.isArray(a.data?.items) ? a.data.items : [])
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    refresh()
  }, [refresh])

  const openPairing = async () => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.securityDevices.adminTokenRequired))
      return
    }
    setError('')
    const ttl = Math.max(10, Math.min(600, Number(ttlInput || 60)))
    const resp = await httpClient.post<PairingCode>(
      `/api/devices/pairing-code/create?ttl_sec=${encodeURIComponent(String(ttl))}`,
      {},
      { headers: { 'X-Admin-Token': token } }
    )
    const pc = resp.data as any
    setPairingCode(pc)
    const dataUrl = await toQrDataUrl(String(pc.pairing_code || ''))
    setQrDataUrl(dataUrl)
    setPairDialogOpen(true)
  }

  const approve = async (id: string) => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.securityDevices.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(`/api/devices/${encodeURIComponent(id)}/approve`, {}, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const reject = async (id: string) => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.securityDevices.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(`/api/devices/${encodeURIComponent(id)}/reject`, {}, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const revoke = async (id: string) => {
    const token = getToken()
    if (!token) {
      setError(t(K.page.securityDevices.adminTokenRequired))
      return
    }
    setError('')
    await httpClient.post(`/api/devices/${encodeURIComponent(id)}/revoke`, {}, { headers: { 'X-Admin-Token': token } })
    await refresh()
  }

  const pendingCard = useMemo(() => {
    const meta: ItemCardMeta[] = [
      { key: 'pending_count', label: t(K.page.securityDevices.pendingCount), value: String(pending.length) },
      { key: 'approved_count', label: t(K.page.securityDevices.approvedCount), value: String(approved.length) },
    ]
    const actions: ItemCardAction[] = [
      { key: 'refresh', label: t('common.refresh'), onClick: () => void refresh(), variant: 'outlined' },
      { key: 'pair', label: t(K.page.securityDevices.createPairingQr), onClick: () => void openPairing(), variant: 'contained' },
    ]
    return <ItemCard title={t(K.page.securityDevices.title)} description={t(K.page.securityDevices.description)} icon="shield" meta={meta} actions={actions} />
  }, [approved.length, openPairing, pending.length, refresh, t])

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <CardCollectionWrap loading={loading}>{pendingCard}</CardCollectionWrap>
      {error ? (
        <Typography variant="body2" color="error">
          {error}
        </Typography>
      ) : null}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h6">{t(K.page.securityDevices.pending)}</Typography>
        {pending.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t(K.page.securityDevices.none)}
          </Typography>
        ) : (
          pending.map((r) => (
            <Box key={r.id} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <Typography variant="body2">
                  {r.device_name} ({r.status})
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t(K.page.securityDevices.deviceId)}: {r.id}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="contained" onClick={() => void approve(r.id)}>
                  {t('common.approve')}
                </Button>
                <Button variant="outlined" onClick={() => void reject(r.id)}>
                  {t('common.reject')}
                </Button>
              </Box>
            </Box>
          ))
        )}
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h6">{t(K.page.securityDevices.approved)}</Typography>
        {approved.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t(K.page.securityDevices.none)}
          </Typography>
        ) : (
          approved.map((r) => (
            <Box key={r.id} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <Typography variant="body2">
                  {r.device_name} ({r.status})
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t(K.page.securityDevices.deviceId)}: {r.id}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="outlined" onClick={() => void revoke(r.id)}>
                  {t('common.revoke')}
                </Button>
              </Box>
            </Box>
          ))
        )}
      </Box>

      <Dialog open={pairDialogOpen} onClose={() => setPairDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t(K.page.securityDevices.pairingQrTitle)}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'center' }}>
          <Box sx={{ display: 'flex', gap: 1, width: '100%' }}>
            <TextField
              label={t(K.page.securityDevices.ttlSeconds)}
              value={ttlInput}
              onChange={(e) => setTtlInput(e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
            <Button variant="outlined" onClick={() => void openPairing()} sx={{ whiteSpace: 'nowrap' }}>
              {t(K.page.securityDevices.regenerate)}
            </Button>
          </Box>

          {qrDataUrl ? <img src={qrDataUrl} alt="pairing-qr" style={{ width: 260, height: 260 }} /> : null}
          <Typography variant="body2" color="text.secondary" sx={{ wordBreak: 'break-all' }}>
            {t(K.page.securityDevices.pairingCode)}: {pairingCode?.pairing_code || '-'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t(K.page.securityDevices.expiresAt)}: {pairingCode?.expires_at_ms || '-'}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPairDialogOpen(false)}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
