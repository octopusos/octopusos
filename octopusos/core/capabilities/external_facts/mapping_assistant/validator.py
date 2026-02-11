"""Dry-run validator for mapping proposal against sample JSON."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .proposal_schema import MappingProposal


def _extract(payload: Any, path: str) -> Any:
    if not path:
        return None
    cursor = payload
    for part in path.split("."):
        key = str(part).strip()
        if not key:
            continue
        if isinstance(cursor, list):
            try:
                cursor = cursor[int(key)]
            except Exception:
                return None
        elif isinstance(cursor, dict):
            if key not in cursor:
                return None
            cursor = cursor[key]
        else:
            return None
    return cursor


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _normalize_time(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1_000_000_000_000:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        text = str(value).strip()
        if text.isdigit():
            ts = float(text)
            if ts > 1_000_000_000_000:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
    except Exception:
        return str(value) if value is not None else None


def validate_mapping_against_sample(proposal: MappingProposal, sample_json: Dict[str, Any]) -> Dict[str, Any]:
    def pick_path(primary: str, role: str, default: str = "") -> str:
        if primary:
            return primary
        candidates = proposal.path_candidates.get(role) if isinstance(proposal.path_candidates, dict) else None
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            path = getattr(first, "path", None) if hasattr(first, "path") else (first.get("path") if isinstance(first, dict) else None)
            if isinstance(path, str) and path:
                return path
        return default

    errors: List[str] = []
    if proposal.response_kind == "series":
        points_path = str(pick_path(str(proposal.points_path or ""), "points"))
        raw_points = _extract(sample_json, points_path) if points_path else None
        if isinstance(raw_points, dict):
            raw_points = [{**v, "key": k} for k, v in raw_points.items() if isinstance(v, dict)]
        if not isinstance(raw_points, list):
            return {"ok": False, "kind": "series", "extracted": {}, "errors": ["points_path not found or not a list/object"]}
        series = []
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            t = _normalize_time(_extract(point, pick_path(proposal.time_path, "time")) or point.get("key"))
            v = _to_float(_extract(point, pick_path(proposal.value_path, "value")))
            if t and v is not None:
                series.append({"t": t, "v": v})
        if not series:
            errors.append("no valid series points extracted")
            return {"ok": False, "kind": "series", "extracted": {"count": 0}, "errors": errors}
        return {
            "ok": True,
            "kind": "series",
            "extracted": {
                "count": len(series),
                "first": series[0],
                "last": series[-1],
            },
            "errors": [],
        }

    if proposal.response_kind == "table":
        rows_path = pick_path(str(proposal.points_path or ""), "points", "rows")
        rows = _extract(sample_json, rows_path)
        row_count = 0
        if isinstance(rows, list):
            row_count = len(rows)
        elif isinstance(rows, dict):
            row_count = len(rows.keys())
        else:
            # allow object snapshot root fallback
            row_count = len(sample_json.keys()) if isinstance(sample_json, dict) else 0
        return {
            "ok": row_count > 0,
            "kind": "table",
            "extracted": {"row_count": row_count, "rows_path": rows_path},
            "errors": [] if row_count > 0 else ["table/object data not found"],
        }

    t = _normalize_time(_extract(sample_json, pick_path(proposal.time_path, "time")))
    v = _to_float(_extract(sample_json, pick_path(proposal.value_path, "value")))
    if v is None:
        errors.append("value_path not found or not numeric")
    if t is None:
        errors.append("time_path not found")
    return {
        "ok": not errors,
        "kind": "point",
        "extracted": {"t": t, "v": v},
        "errors": errors,
    }
