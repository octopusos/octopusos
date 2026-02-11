-- Migration v87: session_event_ledger uniqueness constraints (Phase 1)
--
-- Enforce:
-- - (session_id, ordering_key) unique when ordering_key is not NULL
-- - (session_id, idempotency_key) unique when idempotency_key is not NULL/empty

CREATE UNIQUE INDEX IF NOT EXISTS ux_sel_session_ordering_key
ON session_event_ledger(session_id, ordering_key)
WHERE ordering_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sel_session_idempotency_key
ON session_event_ledger(session_id, idempotency_key)
WHERE idempotency_key IS NOT NULL AND idempotency_key != '';

