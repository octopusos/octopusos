import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { usePageActions, usePageHeader } from '@/ui/layout'
import { useTextTranslation } from '@/ui/text'
import { toast } from '@/ui/feedback'
import { CreateCallModal } from '@/components/voice/CreateCallModal'
import { InCallPanel, type ActiveCall } from '@/components/voice/InCallPanel'
import { callService, type CallRuntime, type VoiceContact, type VoiceContactPayload } from '@/services/callService'
import { useCallSession } from '@/hooks/useCallSession'
import { PROVIDERS, PROVIDER_MODELS } from '@/components/voice/callOptions'

interface ContactFormState {
  display_name: string
  runtime: CallRuntime
  provider_id: string
  model_id: string
  voice_profile_id: string
  prefs_raw: string
}

const defaultContactForm: ContactFormState = {
  display_name: '',
  runtime: 'local',
  provider_id: '',
  model_id: '',
  voice_profile_id: '',
  prefs_raw: '{}',
}

export default function VoicePage() {
  const { t } = useTextTranslation()
  usePageHeader({
    title: t('page.voice.callsTitle'),
    subtitle: t('page.voice.callsSubtitle'),
  })

  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [inCallOpen, setInCallOpen] = useState(false)
  const [activeCall, setActiveCall] = useState<ActiveCall | null>(null)
  const [contacts, setContacts] = useState<VoiceContact[]>([])
  const [loadingContacts, setLoadingContacts] = useState(false)
  const [contactsError, setContactsError] = useState<string | null>(null)
  const [contactKeyword, setContactKeyword] = useState('')

  const [editorOpen, setEditorOpen] = useState(false)
  const [editingContactId, setEditingContactId] = useState<string | null>(null)
  const [contactForm, setContactForm] = useState<ContactFormState>(defaultContactForm)

  const { createSession, creating, error } = useCallSession()

  const filteredContacts = useMemo(() => {
    if (!contactKeyword.trim()) {
      return contacts
    }
    const keyword = contactKeyword.trim().toLowerCase()
    return contacts.filter((contact) => contact.display_name.toLowerCase().includes(keyword))
  }, [contactKeyword, contacts])

  const selectedModelOptions = useMemo(() => {
    if (!contactForm.provider_id) {
      return []
    }
    return PROVIDER_MODELS[contactForm.provider_id] ?? []
  }, [contactForm.provider_id])

  const loadContacts = useCallback(async () => {
    setLoadingContacts(true)
    setContactsError(null)
    try {
      const response = await callService.listVoiceContacts()
      setContacts(response.contacts)
    } catch (err) {
      const message = err instanceof Error ? err.message : t('page.voice.failedLoadContacts')
      setContactsError(message)
    } finally {
      setLoadingContacts(false)
    }
  }, [])

  useEffect(() => {
    void loadContacts()
  }, [loadContacts])

  usePageActions([
    {
      key: 'refresh-contacts',
      label: t('page.voice.refreshContacts'),
      variant: 'outlined',
      onClick: () => {
        void loadContacts()
      },
    },
    {
      key: 'new-contact',
      label: t('page.voice.newVoiceContact'),
      variant: 'outlined',
      onClick: () => {
        setEditingContactId(null)
        setContactForm(defaultContactForm)
        setEditorOpen(true)
      },
    },
    {
      key: 'new-call',
      label: t('page.voice.createCall'),
      variant: 'contained',
      onClick: () => {
        setCreateModalOpen(true)
      },
    },
  ])

  const startCallFromPayload = useCallback(
    async (
      payload: { runtime: CallRuntime; provider_id?: string; model_id?: string; voice_profile_id?: string },
      idempotencyKey?: string
    ) => {
      const response = await createSession(payload, idempotencyKey)
      setCreateModalOpen(false)
      setActiveCall({
        callSessionId: response.call_session_id,
        wsUrl: response.ws_url,
        runtime: payload.runtime,
        providerId: payload.provider_id,
        modelId: payload.model_id,
      })
      setInCallOpen(true)
    },
    [createSession]
  )

  const handleOneClickCall = async (contact: VoiceContact): Promise<void> => {
    try {
      await startCallFromPayload({
        runtime: contact.runtime,
        provider_id: contact.provider_id ?? undefined,
        model_id: contact.model_id ?? undefined,
        voice_profile_id: contact.voice_profile_id ?? undefined,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : t('page.voice.failedStartCallFromContact')
      toast.error(message)
    }
  }

  const openContactEditor = (contact: VoiceContact): void => {
    setEditingContactId(contact.id)
    setContactForm({
      display_name: contact.display_name,
      runtime: contact.runtime,
      provider_id: contact.provider_id ?? '',
      model_id: contact.model_id ?? '',
      voice_profile_id: contact.voice_profile_id ?? '',
      prefs_raw: JSON.stringify(contact.prefs_json ?? {}, null, 2),
    })
    setEditorOpen(true)
  }

  const handleSaveContact = async (): Promise<void> => {
    try {
      let prefs: Record<string, unknown> = {}
      try {
        prefs = JSON.parse(contactForm.prefs_raw || '{}')
      } catch {
        toast.error(t('page.voice.prefsJsonMustBeValid'))
        return
      }

      const payload: VoiceContactPayload = {
        display_name: contactForm.display_name.trim(),
        runtime: contactForm.runtime,
        provider_id: contactForm.runtime === 'cloud' ? contactForm.provider_id : undefined,
        model_id: contactForm.runtime === 'cloud' ? contactForm.model_id : undefined,
        voice_profile_id: contactForm.voice_profile_id || undefined,
        prefs_json: prefs,
      }

      if (!payload.display_name) {
        toast.error(t('page.voice.displayNameRequired'))
        return
      }

      if (payload.runtime === 'cloud' && (!payload.provider_id || !payload.model_id)) {
        toast.error(t('page.voice.cloudContactRequiresProviderModel'))
        return
      }

      if (editingContactId) {
        await callService.updateVoiceContact(editingContactId, payload)
      } else {
        await callService.createVoiceContact(payload)
      }

      setEditorOpen(false)
      setEditingContactId(null)
      setContactForm(defaultContactForm)
      await loadContacts()
      toast.success(t('page.voice.voiceContactSaved'))
    } catch (err) {
      const message = err instanceof Error ? err.message : t('page.voice.failedSaveVoiceContact')
      toast.error(message)
    }
  }

  const handleDeleteContact = async (contactId: string): Promise<void> => {
    try {
      await callService.deleteVoiceContact(contactId)
      await loadContacts()
      toast.success(t('page.voice.voiceContactDeleted'))
    } catch (err) {
      const message = err instanceof Error ? err.message : t('page.voice.failedDeleteVoiceContact')
      toast.error(message)
    }
  }

  return (
    <Stack spacing={2}>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="h6">{t('page.voice.voiceContacts')}</Typography>
            <TextField
              size="small"
              label={t('common.search')}
              value={contactKeyword}
              onChange={(event) => setContactKeyword(event.target.value)}
              data-testid="voice-contact-search"
            />

            {contactsError && <Alert severity="error">{contactsError}</Alert>}
            {loadingContacts && <Alert severity="info">{t('common.loading')}</Alert>}

            <Box sx={{ overflowX: 'auto' }}>
              <Table size="small" data-testid="voice-contact-table">
                <TableHead>
                  <TableRow>
                    <TableCell>{t('page.voice.name')}</TableCell>
                    <TableCell>{t('page.voice.runtime')}</TableCell>
                    <TableCell>{t('page.voice.provider')}</TableCell>
                    <TableCell>{t('page.voice.model')}</TableCell>
                    <TableCell align="right">{t('common.actions')}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredContacts.map((contact) => (
                    <TableRow key={contact.id} hover>
                      <TableCell>{contact.display_name}</TableCell>
                      <TableCell>{contact.runtime}</TableCell>
                      <TableCell>{contact.provider_id || '-'}</TableCell>
                      <TableCell>{contact.model_id || '-'}</TableCell>
                      <TableCell align="right">
                        <Stack direction="row" justifyContent="flex-end" spacing={1}>
                          <Button
                            size="small"
                            variant="contained"
                            data-testid={`voice-contact-call-${contact.id}`}
                            onClick={() => {
                              void handleOneClickCall(contact)
                            }}
                          >
                            {t('page.voice.call')}
                          </Button>
                          <Button
                            size="small"
                            onClick={() => {
                              openContactEditor(contact)
                            }}
                          >
                            {t('common.edit')}
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            onClick={() => {
                              void handleDeleteContact(contact.id)
                            }}
                          >
                            {t('common.delete')}
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <CreateCallModal
        open={createModalOpen}
        creating={creating}
        error={error}
        onClose={() => setCreateModalOpen(false)}
        onStart={async (payload, idempotencyKey) => {
          await startCallFromPayload(payload, idempotencyKey)
        }}
      />

      {activeCall && (
        <InCallPanel
          open={inCallOpen}
          call={activeCall}
          onClose={() => {
            setInCallOpen(false)
          }}
        />
      )}

      <Dialog open={editorOpen} onClose={() => setEditorOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingContactId ? t('page.voice.editVoiceContact') : t('page.voice.createVoiceContact')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label={t('page.voice.displayName')}
              value={contactForm.display_name}
              onChange={(event) => setContactForm((prev) => ({ ...prev, display_name: event.target.value }))}
              data-testid="voice-contact-name-input"
            />

            <TextField
              select
              label={t('page.voice.runtime')}
              value={contactForm.runtime}
              onChange={(event) =>
                setContactForm((prev) => ({
                  ...prev,
                  runtime: event.target.value as CallRuntime,
                  provider_id: event.target.value === 'local' ? '' : prev.provider_id,
                  model_id: event.target.value === 'local' ? '' : prev.model_id,
                }))
              }
              SelectProps={{ native: true }}
            >
              <option value="local">{t('page.voice.local')}</option>
              <option value="cloud">{t('page.voice.cloud')}</option>
            </TextField>

            {contactForm.runtime === 'cloud' && (
              <>
                <TextField
                  select
                  label={t('page.voice.provider')}
                  value={contactForm.provider_id}
                  onChange={(event) =>
                    setContactForm((prev) => ({ ...prev, provider_id: event.target.value, model_id: '' }))
                  }
                  SelectProps={{ native: true }}
                >
                  <option value="">{t('page.voice.selectProvider')}</option>
                  {PROVIDERS.map((provider) => (
                    <option key={provider} value={provider}>
                      {provider}
                    </option>
                  ))}
                </TextField>

                <TextField
                  select
                  label={t('page.voice.model')}
                  value={contactForm.model_id}
                  onChange={(event) => setContactForm((prev) => ({ ...prev, model_id: event.target.value }))}
                  SelectProps={{ native: true }}
                  disabled={!contactForm.provider_id}
                >
                  <option value="">{t('page.voice.selectModel')}</option>
                  {selectedModelOptions.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </TextField>
              </>
            )}

            <TextField
              label={t('page.voice.voiceProfile')}
              value={contactForm.voice_profile_id}
              onChange={(event) => setContactForm((prev) => ({ ...prev, voice_profile_id: event.target.value }))}
            />

            <TextField
              label={t('page.voice.prefsJson')}
              multiline
              minRows={4}
              value={contactForm.prefs_raw}
              onChange={(event) => setContactForm((prev) => ({ ...prev, prefs_raw: event.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditorOpen(false)}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={() => void handleSaveContact()}>
            {t('common.save')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
