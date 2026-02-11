-- Phase 2: Inbox delivery channel (Frontdesk/Workdesk cards, no chat insertion)

CREATE TABLE IF NOT EXISTS inbox_items (
  inbox_item_id TEXT PRIMARY KEY,
  card_id TEXT NOT NULL,
  scope_type TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  delivery_type TEXT NOT NULL, -- inbox_only|notify|confirm
  status TEXT NOT NULL, -- unread|read|archived
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inbox_items_status_created
  ON inbox_items(status, created_at_ms);

CREATE INDEX IF NOT EXISTS idx_inbox_items_scope_status_updated
  ON inbox_items(scope_type, scope_id, status, updated_at_ms);

CREATE UNIQUE INDEX IF NOT EXISTS ux_inbox_items_card_delivery
  ON inbox_items(card_id, delivery_type);

