from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse


router = APIRouter(tags=["changelog"])
SUPPORTED_LANGS = {"en", "zh"}


def _repo_root() -> Path:
    # os/octopusos/webui/api/changelog.py -> api -> webui -> octopusos -> os -> repo_root
    here = Path(__file__).resolve()
    return here.parents[4]


def _changelog_dir() -> Path:
    return _repo_root() / "docs" / "changelog"


def _lang_dir(lang: str) -> Path:
    return _changelog_dir() / "lang" / lang


def _index_path_legacy() -> Path:
    return _changelog_dir() / "index.json"


def _index_path_for_lang(lang: str) -> Path:
    p = _lang_dir(lang) / "index.json"
    if p.exists():
        return p
    return _index_path_legacy()


def _load_index(lang: str) -> dict:
    p = _index_path_for_lang(lang)
    if not p.exists():
        return {"ok": True, "versions": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="CHANGELOG_INDEX_INVALID_JSON")
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="CHANGELOG_INDEX_INVALID")
    versions = data.get("versions")
    if versions is None:
        versions = []
    if not isinstance(versions, list):
        raise HTTPException(status_code=500, detail="CHANGELOG_INDEX_INVALID_VERSIONS")
    return {"ok": True, "versions": versions}


def _entry_path_for_key(*, key: str, lang: str) -> Path | None:
    # Only allow keys present in index.json; prevents path traversal and arbitrary reads.
    idx = _load_index(lang)
    for v in idx.get("versions") or []:
        if not isinstance(v, dict):
            continue
        if str(v.get("key") or "") != key:
            continue
        md_path = str(v.get("md_path") or "").strip()
        if not md_path:
            return None
        # Must be under docs/changelog/lang/<lang> (preferred) and must be a .md file.
        p = (_repo_root() / md_path).resolve()
        lang_base = _lang_dir(lang).resolve()
        base = lang_base if lang_base.exists() else _changelog_dir().resolve()
        try:
            p.relative_to(base)
        except Exception:
            return None
        if p.suffix.lower() != ".md":
            return None
        return p
    return None


@router.get("/api/changelog/index")
def changelog_index(lang: str = Query("en", min_length=2, max_length=8)):
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="CHANGELOG_LANG_UNSUPPORTED")
    return JSONResponse(status_code=200, content=_load_index(lang))


@router.get("/api/changelog/entry")
def changelog_entry(
    key: str = Query(..., min_length=1, max_length=128),
    lang: str = Query("en", min_length=2, max_length=8),
) -> PlainTextResponse:
    if lang not in SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="CHANGELOG_LANG_UNSUPPORTED")
    p = _entry_path_for_key(key=key, lang=lang)
    if p is None:
        raise HTTPException(status_code=404, detail="CHANGELOG_ENTRY_NOT_FOUND")
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="CHANGELOG_ENTRY_MISSING")
    return PlainTextResponse(status_code=200, content=p.read_text(encoding="utf-8"), media_type="text/markdown")
