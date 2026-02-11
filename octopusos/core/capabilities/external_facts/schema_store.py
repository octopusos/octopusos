"""Schema store for External Facts card contracts (versioned + auditable)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from octopusos.core.db import registry_db


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_FACT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "stock": {"category": "Stock", "subtitle": "Equity quote snapshot", "primary_sample": "$189.42", "metric_labels": ["Open", "High", "Low", "Volume"], "trend_enabled": True},
    "crypto": {"category": "Crypto", "subtitle": "Crypto market snapshot", "primary_sample": "$96,210", "metric_labels": ["24h %", "High", "Low", "Volume $"], "trend_enabled": True},
    "index": {"category": "Index", "subtitle": "Market index status", "primary_sample": "5,882.4", "metric_labels": ["Day %", "YTD %", "Breadth", "Volume"], "trend_enabled": True},
    "etf": {"category": "ETF", "subtitle": "ETF last trade", "primary_sample": "$514.26", "metric_labels": ["Day %", "AUM", "PE", "Beta"], "trend_enabled": True},
    "bond_yield": {"category": "Bond", "subtitle": "Treasury yield", "primary_sample": "4.19%", "metric_labels": ["1D bp", "1W bp", "Real yield", "Curve spread"], "trend_enabled": True},
    "commodity": {"category": "Commodity", "subtitle": "Commodity quote", "primary_sample": "$2,038", "metric_labels": ["1D %", "High", "Low", "Open Interest"], "trend_enabled": True},
    "fx": {"category": "FX", "subtitle": "FX spot snapshot", "primary_sample": "0.6521", "metric_labels": ["Bid", "Ask", "Day %", "Spread"], "trend_enabled": True},
    "news": {"category": "News", "subtitle": "Top headlines in last 6h", "primary_sample": "12 headlines", "metric_labels": ["Sources", "Breaking", "Region", "Language mix"], "trend_enabled": False},
    "flight": {"category": "Transport", "subtitle": "Flight status snapshot", "primary_sample": "On time", "metric_labels": ["Gate", "Departure", "Arrival", "Terminal"], "trend_enabled": True},
    "train": {"category": "Transport", "subtitle": "Rail service status", "primary_sample": "3 min delay", "metric_labels": ["Platform", "Departure", "Arrival", "Stops"], "trend_enabled": True},
    "hotel": {"category": "Travel", "subtitle": "Hotel availability snapshot", "primary_sample": "$189 / night", "metric_labels": ["Rating", "Rooms left", "Check-in", "Cancellation policy"], "trend_enabled": True},
    "traffic": {"category": "Mobility", "subtitle": "Traffic congestion level", "primary_sample": "Moderate", "metric_labels": ["Avg speed", "Delay", "Incidents", "Affected km"], "trend_enabled": True},
    "air_quality": {"category": "Environment", "subtitle": "Air quality index", "primary_sample": "AQI 132", "metric_labels": ["PM2.5", "PM10", "O3", "Health level"], "trend_enabled": True},
    "sports": {"category": "Sports", "subtitle": "Live match snapshot", "primary_sample": "3-1", "metric_labels": ["Time", "Possession", "Shots", "Fouls"], "trend_enabled": True},
    "calendar": {"category": "Calendar", "subtitle": "Upcoming schedule", "primary_sample": "Next: 14:30", "metric_labels": ["Event count", "Priority", "Location", "Duration"], "trend_enabled": False, "sensitive": True},
    "package": {"category": "Logistics", "subtitle": "Package delivery status", "primary_sample": "In transit", "metric_labels": ["Carrier", "Last scan", "ETA", "Attempts"], "trend_enabled": True, "sensitive": True},
    "shipping": {"category": "Logistics", "subtitle": "Shipping container status", "primary_sample": "At port", "metric_labels": ["Vessel", "Departure", "Arrival", "Delay days"], "trend_enabled": True},
    "fuel_price": {"category": "Energy", "subtitle": "Fuel price snapshot", "primary_sample": "$1.89 / L", "metric_labels": ["1D %", "Region", "Tax", "Trend"], "trend_enabled": True},
    "earthquake": {"category": "Alert", "subtitle": "Seismic event", "primary_sample": "M5.6", "metric_labels": ["Depth", "Location", "Time", "Tsunami risk"], "trend_enabled": False},
    "power_outage": {"category": "Utilities", "subtitle": "Power outage status", "primary_sample": "12,400 affected", "metric_labels": ["Region", "Cause", "Start time", "ETA restore"], "trend_enabled": True},
    "weather": {"category": "Weather", "subtitle": "Current weather snapshot", "primary_sample": "24°C", "metric_labels": ["High/Low", "Wind", "Humidity", "Condition"], "trend_enabled": True},
}


@dataclass
class SchemaRecord:
    kind: str
    version: int
    schema: Dict[str, Any]
    source: str


class ExternalFactsSchemaStore:
    def __init__(self) -> None:
        self._init_tables()

    @staticmethod
    def _conn():
        return registry_db.get_db()

    def _init_tables(self) -> None:
        conn = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS external_fact_card_schemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                version INTEGER NOT NULL,
                schema_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                note TEXT,
                UNIQUE(kind, version)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS external_fact_card_schema_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                from_version INTEGER,
                to_version INTEGER,
                payload_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    def get_effective(self, kind: str) -> Dict[str, Any]:
        active = self.get_active(kind)
        if active:
            return active.schema
        return dict(DEFAULT_FACT_SCHEMAS.get(kind, {
            "category": kind.replace("_", " ").title(),
            "subtitle": f"{kind} snapshot",
            "primary_sample": "N/A",
            "metric_labels": ["M1", "M2", "M3", "M4"],
            "trend_enabled": True,
        }))

    def get_active(self, kind: str) -> Optional[SchemaRecord]:
        conn = self._conn()
        row = conn.execute(
            """
            SELECT kind, version, schema_json
            FROM external_fact_card_schemas
            WHERE kind = ? AND active = 1
            ORDER BY version DESC LIMIT 1
            """,
            (kind,),
        ).fetchone()
        if not row:
            return None
        return SchemaRecord(kind=row["kind"], version=int(row["version"]), schema=json.loads(row["schema_json"]), source="override")

    def list_effective(self) -> List[SchemaRecord]:
        kinds = sorted(DEFAULT_FACT_SCHEMAS.keys())
        results: List[SchemaRecord] = []
        for kind in kinds:
            active = self.get_active(kind)
            if active:
                results.append(active)
            else:
                results.append(SchemaRecord(kind=kind, version=0, schema=dict(DEFAULT_FACT_SCHEMAS[kind]), source="default"))
        return results

    def export_json(self) -> Dict[str, Any]:
        return {record.kind: record.schema for record in self.list_effective()}

    def apply_bulk(self, schemas: Dict[str, Dict[str, Any]], actor: str, note: str = "") -> Dict[str, Any]:
        conn = self._conn()
        cursor = conn.cursor()
        applied = []
        for kind, schema in schemas.items():
            current = self.get_active(kind)
            from_version = current.version if current else 0
            next_version = from_version + 1
            if current and current.schema == schema:
                continue
            cursor.execute("UPDATE external_fact_card_schemas SET active = 0 WHERE kind = ?", (kind,))
            cursor.execute(
                """
                INSERT INTO external_fact_card_schemas (kind, version, schema_json, active, created_at, created_by, note)
                VALUES (?, ?, ?, 1, ?, ?, ?)
                """,
                (kind, next_version, json.dumps(schema, ensure_ascii=False), _utc_now_iso(), actor, note),
            )
            cursor.execute(
                """
                INSERT INTO external_fact_card_schema_audits (kind, action, actor, from_version, to_version, payload_json, created_at)
                VALUES (?, 'apply', ?, ?, ?, ?, ?)
                """,
                (kind, actor, from_version, next_version, json.dumps(schema, ensure_ascii=False), _utc_now_iso()),
            )
            applied.append({"kind": kind, "from_version": from_version, "to_version": next_version})
        conn.commit()
        return {"applied": applied}

    def rollback(self, kind: str, target_version: int, actor: str) -> Dict[str, Any]:
        conn = self._conn()
        cursor = conn.cursor()
        target = conn.execute(
            "SELECT kind, version, schema_json FROM external_fact_card_schemas WHERE kind = ? AND version = ?",
            (kind, target_version),
        ).fetchone()
        if not target:
            raise ValueError(f"schema version not found: {kind}@{target_version}")
        current = self.get_active(kind)
        from_version = current.version if current else 0
        cursor.execute("UPDATE external_fact_card_schemas SET active = 0 WHERE kind = ?", (kind,))
        cursor.execute(
            "UPDATE external_fact_card_schemas SET active = 1 WHERE kind = ? AND version = ?",
            (kind, target_version),
        )
        cursor.execute(
            """
            INSERT INTO external_fact_card_schema_audits (kind, action, actor, from_version, to_version, payload_json, created_at)
            VALUES (?, 'rollback', ?, ?, ?, ?, ?)
            """,
            (
                kind,
                actor,
                from_version,
                target_version,
                target["schema_json"],
                _utc_now_iso(),
            ),
        )
        conn.commit()
        return {"kind": kind, "from_version": from_version, "to_version": target_version}

    def history(self, kind: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._conn()
        if kind:
            rows = conn.execute(
                """
                SELECT kind, action, actor, from_version, to_version, payload_json, created_at
                FROM external_fact_card_schema_audits
                WHERE kind = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (kind, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT kind, action, actor, from_version, to_version, payload_json, created_at
                FROM external_fact_card_schema_audits
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "kind": row["kind"],
                    "action": row["action"],
                    "actor": row["actor"],
                    "from_version": row["from_version"],
                    "to_version": row["to_version"],
                    "payload": json.loads(row["payload_json"] or "{}"),
                    "created_at": row["created_at"],
                }
            )
        return results

