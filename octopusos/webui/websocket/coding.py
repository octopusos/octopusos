"""WebSocket runtime for Live Coding demo."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import WebSocket

from octopusos.store import get_db
from octopusos.webui.api.preview_store import create_preview_session, update_preview_session
from octopusos.webui.websocket.coding_deliver import run_deliver_pipeline
from octopusos.webui.websocket.stream_bus import append_event, latest_run as latest_stream_run, list_events

logger = logging.getLogger(__name__)


class CodingConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            old = self.active_connections.get(session_id)
            if old is not None:
                with contextlib.suppress(Exception):
                    await old.close(code=1000)
            self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str) -> None:
        self.active_connections.pop(session_id, None)

    async def send_event(self, session_id: str, event: Dict[str, Any]) -> None:
        websocket = self.active_connections.get(session_id)
        if websocket is None:
            return
        await websocket.send_json(event)


manager = CodingConnectionManager()


@dataclass
class CodingRunContext:
    session_id: str
    run_id: str
    plan_id: str
    task_id: str
    seq: int = 0
    state: str = "running"
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task] = None
    preview_id: Optional[str] = None
    workspace_root: Optional[Path] = None
    project_root: Optional[Path] = None
    dev_server_url: Optional[str] = None
    child_processes: list[asyncio.subprocess.Process] = field(default_factory=list)

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq


_active_runs: dict[str, CodingRunContext] = {}
_run_lock = asyncio.Lock()
_schema_ready = False


KNOWN_VARIANTS = ["skeleton", "scroll", "carousel", "three", "apple_iphone17pro", "landing_saas"]
KNOWN_FRAMEWORKS = ["react", "vue"]
KNOWN_PROVIDERS = ["mui", "antd", "vuetify", "tailwind"]
KNOWN_CONTRACTS = ["brand_soft", "brand_dark", "brand_compact"]
KNOWN_PAGE_TYPES = ["landing", "product", "editorial"]


def _json_load(raw: Any, default: Any) -> Any:
    if not raw:
        return default
    try:
        value = json.loads(raw)
        return value
    except Exception:
        return default


def _ensure_command_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS coding_command_dedup (
            session_id TEXT NOT NULL,
            command_id TEXT NOT NULL,
            command_type TEXT NOT NULL,
            result_json TEXT,
            created_at INTEGER NOT NULL,
            PRIMARY KEY (session_id, command_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS coding_demo_state (
            session_id TEXT PRIMARY KEY,
            stage TEXT NOT NULL,
            requirements_json TEXT,
            plan_json TEXT,
            spec_frozen INTEGER NOT NULL DEFAULT 0,
            plan_id TEXT,
            run_id TEXT,
            last_test_status TEXT,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    _schema_ready = True


def _default_requirements() -> Dict[str, Any]:
    return {
        "goal": "Clone iPhone style storytelling landing",
        "variants": ["apple_iphone17pro"],
        "framework": "react",
        "provider": "mui",
        "contract_id": "brand_soft",
        "page_type": "landing",
        "delivery_variant": "demo",
        "constraints": ["no_chat_or_work_page_modifications"],
        "acceptance": [
            "Timeline shows role-scoped progress",
            "Preview reloads after file writes",
            "Replay survives refresh",
        ],
    }


def _normalize_variants(variants: Any) -> List[str]:
    if not isinstance(variants, list) or not variants:
        return list(KNOWN_VARIANTS)
    normalized: List[str] = []
    for item in variants:
        value = str(item).strip().lower()
        if not value:
            continue
        normalized.append(value)
    return normalized or list(KNOWN_VARIANTS)


def _default_plan(requirements: Dict[str, Any]) -> Dict[str, Any]:
    variants = _normalize_variants(requirements.get("variants"))
    if "apple_iphone17pro" in variants:
        tasks = [
            {
                "id": "T1",
                "variant": "apple_iphone17pro",
                "title": "Scaffold Apple-style layout and navigation",
                "owner": "frontend",
                "acceptance": ["global nav exists", "product subnav exists", "hero renders"],
            },
            {
                "id": "T2",
                "variant": "apple_iphone17pro",
                "title": "Build highlights carousel and controls",
                "owner": "frontend",
                "acceptance": ["highlights heading", "carousel switch", "indicator updates"],
            },
            {
                "id": "T3",
                "variant": "apple_iphone17pro",
                "title": "Add scroll-trigger story and footer",
                "owner": "frontend",
                "acceptance": ["scroll story active state", "footer columns", "legal copy"],
            },
            {
                "id": "T4",
                "variant": "apple_iphone17pro",
                "title": "Run Playwright smoke and publish completion",
                "owner": "qa",
                "acceptance": ["smoke passed", "test events emitted", "complete ready"],
            },
        ]
        return {
            "roles": [
                {"id": "frontend", "label": "Frontend"},
                {"id": "qa", "label": "QA"},
            ],
            "tasks": tasks,
            "acceptance": [
                "Template project boots with Vite dev server",
                "Highlights carousel and scroll story validated",
                "Playwright smoke test passes before completion",
            ],
        }

    tasks: List[Dict[str, Any]] = []
    for idx, variant in enumerate(variants, start=1):
        task_id = f"T{idx}"
        title = f"Implement {variant} module"
        acceptance = [
            f"{variant} markup exists in preview",
            "fs.changed emitted",
            "checklist entry marked done",
        ]
        tasks.append(
            {
                "id": task_id,
                "variant": variant,
                "title": title,
                "owner": "frontend" if variant != "qa" else "qa",
                "acceptance": acceptance,
            }
        )
    if not tasks:
        tasks.append(
            {
                "id": "T1",
                "variant": "skeleton",
                "title": "Implement skeleton module",
                "owner": "frontend",
                "acceptance": ["Section One present", "fs.changed emitted", "checklist done"],
            }
        )

    return {
        "roles": [
            {"id": "frontend", "label": "Frontend"},
            {"id": "qa", "label": "QA"},
        ],
        "tasks": tasks,
        "acceptance": [
            "All selected variants render in preview",
            "Automated smoke test passes",
            "Run completes with complete.ready",
        ],
    }


def _load_demo_state(session_id: str) -> Dict[str, Any]:
    _ensure_command_schema()
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        """
        SELECT stage, requirements_json, plan_json, spec_frozen, plan_id, run_id, last_test_status
        FROM coding_demo_state
        WHERE session_id = ?
        """,
        (session_id,),
    ).fetchone()
    if not row:
        state = {
            "session_id": session_id,
            "stage": "discussion",
            "requirements": _default_requirements(),
            "plan": {},
            "spec_frozen": False,
            "plan_id": None,
            "run_id": None,
            "last_test_status": None,
        }
        _save_demo_state(session_id, state)
        return state

    requirements = _json_load(row[1], _default_requirements())
    plan = _json_load(row[2], {})
    return {
        "session_id": session_id,
        "stage": str(row[0] or "discussion"),
        "requirements": requirements if isinstance(requirements, dict) else _default_requirements(),
        "plan": plan if isinstance(plan, dict) else {},
        "spec_frozen": bool(int(row[3] or 0)),
        "plan_id": row[4],
        "run_id": row[5],
        "last_test_status": row[6],
    }


def _save_demo_state(session_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_command_schema()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO coding_demo_state(session_id, stage, requirements_json, plan_json, spec_frozen, plan_id, run_id, last_test_status, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            stage=excluded.stage,
            requirements_json=excluded.requirements_json,
            plan_json=excluded.plan_json,
            spec_frozen=excluded.spec_frozen,
            plan_id=excluded.plan_id,
            run_id=excluded.run_id,
            last_test_status=excluded.last_test_status,
            updated_at=excluded.updated_at
        """,
        (
            session_id,
            str(state.get("stage") or "discussion"),
            json.dumps(state.get("requirements") or _default_requirements(), ensure_ascii=False),
            json.dumps(state.get("plan") or {}, ensure_ascii=False),
            1 if state.get("spec_frozen") else 0,
            state.get("plan_id"),
            state.get("run_id"),
            state.get("last_test_status"),
            int(time.time()),
        ),
    )
    conn.commit()
    return state


async def _emit(
    *,
    session_id: str,
    run_id: str,
    task_id: Optional[str],
    event_type: str,
    payload: Dict[str, Any],
    role: Optional[str] = None,
    demo_stage: Optional[str] = None,
    plan_id: Optional[str] = None,
    seq: Optional[int] = None,
) -> Dict[str, Any]:
    event = append_event(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        event_type=event_type,
        payload=payload,
        role=role,
        demo_stage=demo_stage,
        plan_id=plan_id,
        seq=seq,
    )
    await manager.send_event(session_id, event)
    return event


async def emit_external_event(
    *,
    session_id: str,
    run_id: str,
    event_type: str,
    payload: Dict[str, Any],
    task_id: Optional[str] = None,
    role: Optional[str] = None,
    demo_stage: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> Dict[str, Any]:
    return await _emit(
        session_id=session_id,
        run_id=run_id,
        task_id=task_id,
        event_type=event_type,
        payload=payload,
        role=role,
        demo_stage=demo_stage,
        plan_id=plan_id,
    )


def get_demo_state(session_id: str) -> Dict[str, Any]:
    return _load_demo_state(session_id)


async def save_discussion_requirements(session_id: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
    state = _load_demo_state(session_id)
    framework = str(requirements.get("framework") or state["requirements"].get("framework") or "react").strip().lower()
    provider = str(requirements.get("provider") or state["requirements"].get("provider") or "mui").strip().lower()
    contract_id = str(requirements.get("contract_id") or state["requirements"].get("contract_id") or "brand_soft").strip().lower()
    page_type = str(requirements.get("page_type") or state["requirements"].get("page_type") or "landing").strip().lower()
    delivery_variant = str(requirements.get("delivery_variant") or state["requirements"].get("delivery_variant") or "demo").strip().lower()
    state["requirements"] = {
        "goal": str(requirements.get("goal") or state["requirements"].get("goal") or ""),
        "variants": _normalize_variants(requirements.get("variants")),
        "framework": framework if framework in KNOWN_FRAMEWORKS else "react",
        "provider": provider if provider in KNOWN_PROVIDERS else "mui",
        "contract_id": contract_id or "brand_soft",
        "page_type": page_type if page_type in KNOWN_PAGE_TYPES else "landing",
        "delivery_variant": delivery_variant if delivery_variant in {"demo", "deliver_page_spec"} else "demo",
        "constraints": [str(item) for item in requirements.get("constraints", []) if str(item).strip()],
        "acceptance": [str(item) for item in requirements.get("acceptance", []) if str(item).strip()],
    }
    if not state["requirements"]["constraints"]:
        state["requirements"]["constraints"] = ["no_chat_or_work_page_modifications"]
    if not state["requirements"]["acceptance"]:
        state["requirements"]["acceptance"] = [
            "Timeline replay survives refresh",
            "Preview updates after fs changes",
            "Stop/Cancel path remains functional",
        ]

    state["stage"] = "discussion"
    state["spec_frozen"] = False
    state["plan"] = {}
    state["plan_id"] = None
    state["run_id"] = str(state.get("run_id") or f"demo_run_{uuid.uuid4().hex}")
    state["last_test_status"] = None
    _save_demo_state(session_id, state)
    return state


async def generate_plan(session_id: str) -> Dict[str, Any]:
    state = _load_demo_state(session_id)
    requirements = state.get("requirements") or _default_requirements()
    plan = _default_plan(requirements)
    plan_id = f"plan_{uuid.uuid4().hex[:10]}"
    run_id = f"demo_run_{uuid.uuid4().hex}"
    plan["plan_id"] = plan_id
    plan["run_id"] = run_id
    state["stage"] = "planning"
    state["spec_frozen"] = False
    state["plan"] = plan
    state["plan_id"] = plan_id
    state["run_id"] = run_id
    _save_demo_state(session_id, state)

    await _emit(
        session_id=session_id,
        run_id=run_id,
        task_id=None,
        role="planner",
        demo_stage="planning",
        plan_id=plan_id,
        event_type="plan.created",
        payload={"plan": plan, "requirements": requirements},
    )
    return state


async def freeze_plan(session_id: str) -> Dict[str, Any]:
    state = _load_demo_state(session_id)
    if not state.get("plan"):
        state = await generate_plan(session_id)
    state["spec_frozen"] = True
    state["stage"] = "planning"
    _save_demo_state(session_id, state)

    run_id = str(state.get("run_id") or f"demo_run_{uuid.uuid4().hex}")
    if not state.get("run_id"):
        state["run_id"] = run_id
        _save_demo_state(session_id, state)

    await _emit(
        session_id=session_id,
        run_id=run_id,
        task_id=None,
        role="planner",
        demo_stage="planning",
        plan_id=state.get("plan_id"),
        event_type="plan.frozen",
        payload={"spec_frozen": True, "plan_id": state.get("plan_id")},
    )
    await _emit(
        session_id=session_id,
        run_id=run_id,
        task_id=None,
        role="planner",
        demo_stage="planning",
        plan_id=state.get("plan_id"),
        event_type="pagespec.frozen",
        payload={
            "spec_hash": f"pending:{state.get('plan_id')}",
            "framework": str(state.get("requirements", {}).get("framework") or "react"),
            "provider": str(state.get("requirements", {}).get("provider") or "mui"),
            "contract_id": str(state.get("requirements", {}).get("contract_id") or "brand_soft"),
        },
    )
    return state


async def _create_or_reload_preview(
    run: CodingRunContext,
    html: str,
    *,
    create_if_missing: bool,
    role: str,
    demo_stage: str,
) -> None:
    if create_if_missing or not run.preview_id:
        created = create_preview_session(
            preset="html-basic",
            html=html,
            session_id=run.session_id,
            run_id=run.run_id,
            meta={"source": "coding_demo", "plan_id": run.plan_id},
        )
        run.preview_id = str(created["preview_id"])
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role=role,
            demo_stage=demo_stage,
            plan_id=run.plan_id,
            event_type="preview.ready",
            payload={
                "preview_id": run.preview_id,
                "url": created["url"],
                "status": created["status"],
            },
            seq=run.next_seq(),
        )
        return

    updated = update_preview_session(run.preview_id, html=html, bump_version=True)
    if not updated:
        return
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id=run.task_id,
        role=role,
        demo_stage=demo_stage,
        plan_id=run.plan_id,
        event_type="preview.reload",
        payload={
            "preview_id": run.preview_id,
            "url": updated["url"],
            "status": updated["status"],
        },
        seq=run.next_seq(),
    )


def _build_variant_html(prompt: str, variants: List[str]) -> Dict[str, str]:
    hero_copy = prompt.strip() or "Live coding preview"
    css = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #111827; }
main { max-width: 1080px; margin: 0 auto; padding: 48px 24px 80px; }
.hero { background: linear-gradient(135deg, #0f172a, #1d4ed8); color: #fff; border-radius: 20px; padding: 56px 32px; margin-bottom: 24px; }
.hero h1 { margin: 0 0 12px; font-size: clamp(30px, 6vw, 56px); }
.hero p { margin: 0; opacity: 0.9; max-width: 70ch; }
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-top: 24px; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 16px; padding: 20px; min-height: 160px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06); }
.sticky-stage { position: relative; height: 180vh; margin-top: 24px; }
.sticky-panel { position: sticky; top: 16px; background: #0f172a; color: #e2e8f0; border-radius: 20px; min-height: 68vh; padding: 24px; overflow: hidden; }
.sticky-panel .copy { opacity: 0.45; transform: scale(0.94); transition: opacity .22s ease, transform .22s ease; margin: 12px 0; }
.sticky-panel .copy.active { opacity: 1; transform: scale(1); }
.carousel { margin-top: 24px; background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; }
.track { display: flex; transition: transform .25s ease; }
.slide { min-width: 100%; padding: 36px; background: linear-gradient(160deg, #111827, #1d4ed8); color: #fff; min-height: 220px; }
.controls { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; }
.dots { display: inline-flex; gap: 8px; }
.dot { width: 8px; height: 8px; border-radius: 999px; background: #cbd5e1; }
.dot.active { background: #2563eb; }
#canvasWrap { margin-top: 24px; background: #020617; border-radius: 16px; padding: 16px; }
canvas { width: 100%; height: 300px; display: block; border-radius: 12px; background: radial-gradient(circle at 20% 20%, #1d4ed8, #020617 65%); }
footer { margin-top: 24px; color: #475569; text-align: center; }
@media (max-width: 860px) { .grid { grid-template-columns: 1fr; } main { padding: 24px 16px 56px; } }
""".strip()

    sections = [
        """
<section class="hero" data-marker="hero">
  <h1>iPhone Style Landing</h1>
  <p>{hero}</p>
</section>
<section class="grid" data-marker="skeleton">
  <article class="card"><h3>Section One</h3><p>Feature framing and value props.</p></article>
  <article class="card"><h3>Section Two</h3><p>Motion-forward storytelling content.</p></article>
  <article class="card"><h3>Section Three</h3><p>Final call to action and retention hooks.</p></article>
</section>
        """.strip().format(hero=hero_copy)
    ]

    js_parts = ["/* baseline script */"]

    if "scroll" in variants:
        sections.append(
            """
<section class="sticky-stage" data-marker="sticky-stage">
  <div class="sticky-panel" id="storyPanel">
    <h2>Scroll Storytelling</h2>
    <p class="copy active">Frame the product promise.</p>
    <p class="copy">Zoom into hardware craftsmanship.</p>
    <p class="copy">Land with conversion message.</p>
  </div>
</section>
            """.strip()
        )
        js_parts.append(
            """
const copies = Array.from(document.querySelectorAll('#storyPanel .copy'));
window.addEventListener('scroll', () => {
  const progress = Math.min(0.999, Math.max(0, window.scrollY / Math.max(1, document.body.scrollHeight - window.innerHeight)));
  const idx = Math.min(copies.length - 1, Math.floor(progress * copies.length));
  copies.forEach((el, i) => el.classList.toggle('active', i === idx));
}, { passive: true });
            """.strip()
        )

    if "carousel" in variants:
        sections.append(
            """
<section class="carousel" data-marker="carousel" aria-label="video-carousel">
  <div class="track" id="carouselTrack">
    <article class="slide"><h2>Video One</h2><p>Product hero reveal.</p></article>
    <article class="slide"><h2>Video Two</h2><p>Camera system highlight.</p></article>
    <article class="slide"><h2>Video Three</h2><p>Chip performance story.</p></article>
  </div>
  <div class="controls">
    <button id="prevBtn" type="button">Prev</button>
    <div class="dots" id="dotRow"><span class="dot active"></span><span class="dot"></span><span class="dot"></span></div>
    <button id="nextBtn" type="button">Next</button>
  </div>
</section>
            """.strip()
        )
        js_parts.append(
            """
let carouselIndex = 0;
const track = document.getElementById('carouselTrack');
const dots = Array.from(document.querySelectorAll('#dotRow .dot'));
const renderCarousel = () => {
  if (!track) return;
  track.style.transform = `translateX(-${carouselIndex * 100}%)`;
  dots.forEach((dot, i) => dot.classList.toggle('active', i === carouselIndex));
};
const nextBtn = document.getElementById('nextBtn');
const prevBtn = document.getElementById('prevBtn');
if (nextBtn) nextBtn.addEventListener('click', () => { carouselIndex = (carouselIndex + 1) % dots.length; renderCarousel(); });
if (prevBtn) prevBtn.addEventListener('click', () => { carouselIndex = (carouselIndex - 1 + dots.length) % dots.length; renderCarousel(); });
renderCarousel();
            """.strip()
        )

    if "three" in variants:
        sections.append(
            """
<section id="canvasWrap" data-marker="three">
  <h2 style="color:#e2e8f0;margin:0 0 12px;">3D Placeholder Stage</h2>
  <canvas id="heroCanvas" width="900" height="360" aria-label="3d-placeholder"></canvas>
</section>
            """.strip()
        )
        js_parts.append(
            """
const canvas = document.getElementById('heroCanvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let frame = 0;
  const draw = () => {
    frame += 0.02;
    const w = canvas.width, h = canvas.height;
    if (!ctx) return;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0ea5e9';
    ctx.save();
    ctx.translate(w / 2, h / 2);
    ctx.rotate(frame);
    ctx.fillRect(-70, -70, 140, 140);
    ctx.restore();
    requestAnimationFrame(draw);
  };
  draw();
}
            """.strip()
        )

    if "landing_saas" in variants:
        sections.append(
            """
<section data-marker="landing_saas" style="margin-top:24px;background:#111827;border-radius:16px;padding:24px;color:#fff;">
  <h2>Landing hero</h2>
  <p>Reusable SaaS variant with pricing and conversion sections.</p>
</section>
            """.strip()
        )

    if "apple_iphone17pro" in variants:
        sections.append(
            """
<section data-marker="apple_iphone17pro" style="margin-top:24px;background:#f5f5f7;border-radius:20px;padding:28px;">
  <meta name="octopusos-marker" content="marker::apple_iphone17pro" />
  <div data-octopus-marker="marker::apple_iphone17pro" style="display:none;">marker::apple_iphone17pro</div>
  <h2 style="font-size:40px;line-height:1.05;margin:0;">Get the highlights.</h2>
  <p style="color:#4b5563;margin-top:10px;">Apple-style storytelling scaffold generated by coding worker.</p>
</section>
            """.strip()
        )

    sections.append('<footer data-marker="footer">OctopusOS Live Coding Demo Footer</footer>')
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<title>Live Coding Demo</title><style>"
        + css
        + "</style></head><body><main>"
        + "\n".join(sections)
        + "</main><script>"
        + "\n".join(js_parts)
        + "</script></body></html>"
    )

    return {
        "index_html": html,
        "styles_css": css,
        "app_js": "\n".join(js_parts),
    }


def _required_marker_for_variant(variant: str) -> str:
    mapping = {
        "skeleton": "Section One",
        "scroll": "sticky-stage",
        "carousel": 'class="carousel"',
        "three": "heroCanvas",
        "apple_iphone17pro": "marker::apple_iphone17pro",
        "landing_saas": "Landing hero",
    }
    return mapping.get(variant, f"marker::{variant}")


async def _emit_log(run: CodingRunContext, role: str, stage: str, task_id: str, text: str, level: str = "info") -> None:
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id=task_id,
        role=role,
        demo_stage=stage,
        plan_id=run.plan_id,
        event_type="log.append",
        payload={"level": level, "text": text},
        seq=run.next_seq(),
    )


async def _terminate_child_processes(run: CodingRunContext) -> None:
    for proc in run.child_processes:
        if proc.returncode is not None:
            continue
        with contextlib.suppress(ProcessLookupError):
            proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=4)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            with contextlib.suppress(Exception):
                await proc.wait()


async def _stream_command_output(
    run: CodingRunContext,
    process: asyncio.subprocess.Process,
    *,
    role: str,
    stage: str,
    task_id: str,
) -> None:
    async def _consume(stream: asyncio.StreamReader, level: str) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            await _emit_log(run, role, stage, task_id, line.decode("utf-8", errors="ignore").rstrip(), level=level)

    await asyncio.gather(
        _consume(process.stdout, "info") if process.stdout else asyncio.sleep(0),
        _consume(process.stderr, "warning") if process.stderr else asyncio.sleep(0),
    )


async def _run_command(
    run: CodingRunContext,
    *,
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    role: str,
    stage: str,
    task_id: str,
    allow_failure: bool = False,
) -> int:
    await _emit_log(run, role, stage, task_id, f"$ {' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    run.child_processes.append(process)
    await _stream_command_output(run, process, role=role, stage=stage, task_id=task_id)
    return_code = await process.wait()
    if return_code != 0 and not allow_failure:
        raise RuntimeError(f"Command failed ({return_code}): {' '.join(cmd)}")
    return return_code


async def _wait_for_http_ready(url: str, timeout_s: float = 40.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", int(url.rsplit(":", 1)[-1]))
            writer.write(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            await writer.drain()
            data = await reader.read(256)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            if b"200" in data or b"302" in data:
                return True
        except Exception:
            await asyncio.sleep(0.8)
    return False


async def _run_apple_project_pipeline(run: CodingRunContext, prompt: str, state: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    template_root = Path("apps/apple-iphone-clone-template").resolve()
    workspace_root = Path("tmp/live_coding_workspace") / run.session_id / run.run_id
    project_root = workspace_root / "project"
    run.workspace_root = workspace_root
    run.project_root = project_root
    workspace_root.mkdir(parents=True, exist_ok=True)
    if project_root.exists():
        shutil.rmtree(project_root)
    shutil.copytree(
        template_root,
        project_root,
        ignore=shutil.ignore_patterns("node_modules", "test-results", "playwright-report", ".vite"),
    )
    run_config_file = project_root / ".octopusos-run.json"
    run_config_file.write_text(
        json.dumps(
            {
                "session_id": run.session_id,
                "run_id": run.run_id,
                "plan_id": run.plan_id,
                "prompt": prompt,
                "created_at": int(time.time()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T1",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="fs.changed",
        payload={
            "changes": [
                {"path": str(project_root), "op": "create"},
                {"path": str(run_config_file), "op": "write"},
            ]
        },
        seq=run.next_seq(),
    )

    env = dict(os.environ)
    npm_cache_dir = (workspace_root / ".npm-cache").resolve()
    npm_cache_dir.mkdir(parents=True, exist_ok=True)
    env["npm_config_cache"] = str(npm_cache_dir)
    env["CI"] = "1"

    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T1",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="step.changed",
        payload={"step": "setup", "detail": "Template copied into workspace project"},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T1",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="run.started",
        payload={"prompt": prompt, "mode": "apple_iphone17pro", "project_root": str(project_root)},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T1",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="checklist.upsert",
        payload={
            "items": [
                {"id": "setup", "label": "Template scaffolded", "status": "done"},
                {"id": "install", "label": "Dependencies installed", "status": "pending"},
                {"id": "dev", "label": "Dev server ready", "status": "pending"},
                {"id": "qa", "label": "Smoke tests passed", "status": "pending"},
            ]
        },
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T1",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="progress",
        payload={"percent": 10, "label": "Template copied"},
        seq=run.next_seq(),
    )

    if bool(metadata.get("fast_mode")):
        preview = create_preview_session(
            preset="html-basic",
            html="<!doctype html><html><body><h1>Apple clone fast-mode preview</h1><p>Get the highlights.</p></body></html>",
            session_id=run.session_id,
            run_id=run.run_id,
            meta={"source": "apple_fast_mode"},
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T3",
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="preview.ready",
            payload={"preview_id": preview["preview_id"], "url": preview["url"], "status": preview["status"]},
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T4",
            role="qa",
            demo_stage="test",
            plan_id=run.plan_id,
            event_type="test.started",
            payload={"suite": "apple_template_smoke", "url": preview["url"], "fast_mode": True},
            seq=run.next_seq(),
        )
        if bool(metadata.get("force_test_fail")):
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id="T4",
                role="qa",
                demo_stage="test",
                plan_id=run.plan_id,
                event_type="test.failed",
                payload={"suite": "apple_template_smoke", "reason": "forced failure"},
                seq=run.next_seq(),
            )
            state["stage"] = "planning"
            state["last_test_status"] = "failed"
            _save_demo_state(run.session_id, state)
            run.state = "failed"
            return

        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T4",
            role="qa",
            demo_stage="test",
            plan_id=run.plan_id,
            event_type="test.passed",
            payload={"suite": "apple_template_smoke", "assertions": ["nav", "highlights", "carousel", "scroll", "footer"], "fast_mode": True},
            seq=run.next_seq(),
        )
        state["stage"] = "complete"
        state["last_test_status"] = "passed"
        _save_demo_state(run.session_id, state)
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T4",
            role="qa",
            demo_stage="complete",
            plan_id=run.plan_id,
            event_type="run.completed",
            payload={"status": "ok", "preview_url": preview["url"]},
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T4",
            role="qa",
            demo_stage="complete",
            plan_id=run.plan_id,
            event_type="complete.ready",
            payload={"preview_url": preview["url"], "preview_id": preview["preview_id"]},
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T4",
            role="qa",
            demo_stage="complete",
            plan_id=run.plan_id,
            event_type="message.end",
            payload={"content": "Apple template run completed (fast mode)."},
            seq=run.next_seq(),
        )
        run.state = "completed"
        return

    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T2",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="step.changed",
        payload={"step": "install", "detail": "Installing npm dependencies with cache"},
        seq=run.next_seq(),
    )
    await _run_command(
        run,
        cmd=["npm", "install", "--no-fund", "--no-audit"],
        cwd=project_root,
        env=env,
        role="frontend",
        stage="worker",
        task_id="T2",
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T2",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="checklist.checked",
        payload={"id": "install", "evidence": "npm install completed"},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T2",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="progress",
        payload={"percent": 45, "label": "Dependencies ready"},
        seq=run.next_seq(),
    )

    if not bool(metadata.get("skip_browser_install")):
        await _run_command(
            run,
            cmd=["npx", "playwright", "install", "chromium"],
            cwd=project_root,
            env=env,
            role="qa",
            stage="worker",
            task_id="T2",
            allow_failure=True,
        )

    dev_port = int(metadata.get("dev_port") or 4173)
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T3",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="step.changed",
        payload={"step": "devserver", "detail": f"Starting Vite server on port {dev_port}"},
        seq=run.next_seq(),
    )
    dev_process = await asyncio.create_subprocess_exec(
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(dev_port),
        cwd=str(project_root),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    run.child_processes.append(dev_process)
    await asyncio.sleep(1.2)
    ready_url = f"http://127.0.0.1:{dev_port}"
    ready = await _wait_for_http_ready(ready_url)
    if not ready:
        raise RuntimeError(f"Dev server failed to become ready at {ready_url}")
    run.dev_server_url = ready_url
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T3",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="preview.ready",
        payload={"preview_id": None, "url": ready_url, "status": "ready"},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T3",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="checklist.checked",
        payload={"id": "dev", "evidence": ready_url},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T3",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="progress",
        payload={"percent": 70, "label": "Preview server ready"},
        seq=run.next_seq(),
    )

    state["stage"] = "test"
    _save_demo_state(run.session_id, state)
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="test.started",
        payload={"suite": "apple_template_smoke", "url": ready_url},
        seq=run.next_seq(),
    )
    test_env = dict(env)
    test_env["PLAYWRIGHT_BASE_URL"] = ready_url
    test_result = await _run_command(
        run,
        cmd=["npm", "run", "test:smoke", "--", "--reporter=line"],
        cwd=project_root,
        env=test_env,
        role="qa",
        stage="test",
        task_id="T4",
        allow_failure=True,
    )
    inject_failure = bool(metadata.get("force_test_fail"))
    if test_result != 0 or inject_failure:
        reason = "forced failure" if inject_failure else f"Playwright smoke failed ({test_result})"
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T4",
            role="qa",
            demo_stage="test",
            plan_id=run.plan_id,
            event_type="test.failed",
            payload={"suite": "apple_template_smoke", "reason": reason},
            seq=run.next_seq(),
        )
        state["last_test_status"] = "failed"
        state["stage"] = "planning"
        _save_demo_state(run.session_id, state)
        run.state = "failed"
        return

    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="test.passed",
        payload={"suite": "apple_template_smoke", "assertions": ["nav", "highlights", "carousel", "scroll", "footer"]},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="checklist.checked",
        payload={"id": "qa", "evidence": "Playwright smoke passed"},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="progress",
        payload={"percent": 92, "label": "QA smoke passed"},
        seq=run.next_seq(),
    )

    state["stage"] = "complete"
    state["last_test_status"] = "passed"
    _save_demo_state(run.session_id, state)
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="complete",
        plan_id=run.plan_id,
        event_type="run.completed",
        payload={"status": "ok", "preview_url": ready_url},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="complete",
        plan_id=run.plan_id,
        event_type="complete.ready",
        payload={"preview_url": ready_url, "preview_id": None},
        seq=run.next_seq(),
    )
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="T4",
        role="qa",
        demo_stage="complete",
        plan_id=run.plan_id,
        event_type="message.end",
        payload={"content": "Apple template run completed."},
        seq=run.next_seq(),
    )
    run.state = "completed"


async def _run_demo_smoke_tests(run: CodingRunContext, html: str, variants: List[str], *, inject_failure: bool) -> Tuple[bool, Dict[str, Any]]:
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="QA",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="test.started",
        payload={"suite": "demo_smoke", "variants": variants},
        seq=run.next_seq(),
    )

    assertions: List[Dict[str, Any]] = []
    failures: List[str] = []
    for variant in variants:
        marker = _required_marker_for_variant(variant)
        passed = marker in html and not inject_failure
        assertions.append({"variant": variant, "marker": marker, "passed": passed})
        if not passed:
            failures.append(f"Missing marker for {variant}: {marker}")

    if failures:
        payload = {"suite": "demo_smoke", "reason": failures[0], "failures": failures, "assertions": assertions}
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="QA",
            role="qa",
            demo_stage="test",
            plan_id=run.plan_id,
            event_type="test.failed",
            payload=payload,
            seq=run.next_seq(),
        )
        return False, payload

    payload = {"suite": "demo_smoke", "assertions": assertions}
    await _emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="QA",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="test.passed",
        payload=payload,
        seq=run.next_seq(),
    )
    return True, payload


async def _run_demo_pipeline(run: CodingRunContext, prompt: str, long_mode: bool, state: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    plan = state.get("plan") if isinstance(state.get("plan"), dict) else {}
    tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
    variants = [str(task.get("variant") or "").strip().lower() for task in tasks if isinstance(task, dict)]
    variants = [variant for variant in variants if variant]
    if not variants:
        variants = ["skeleton"]
    if "apple_iphone17pro" in variants:
        try:
            await _run_apple_project_pipeline(run, prompt=prompt, state=state, metadata=metadata)
        except asyncio.CancelledError:
            run.state = "cancelled"
            state["stage"] = "planning"
            _save_demo_state(run.session_id, state)
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=run.task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="message.cancelled",
                payload={"reason": "user_cancelled"},
                seq=run.next_seq(),
            )
        except Exception as exc:
            run.state = "failed"
            state["stage"] = "planning"
            _save_demo_state(run.session_id, state)
            logger.exception("Apple template pipeline failed: %s", exc)
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=run.task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="message.error",
                payload={"message": str(exc)},
                seq=run.next_seq(),
            )
        finally:
            await _terminate_child_processes(run)
            async with _run_lock:
                active = _active_runs.get(run.session_id)
                if active and active.run_id == run.run_id:
                    _active_runs.pop(run.session_id, None)
        return

    workspace_root = Path("tmp/live_coding_workspace") / run.session_id / run.run_id
    workspace_root.mkdir(parents=True, exist_ok=True)
    index_file = workspace_root / "index.html"
    styles_file = workspace_root / "styles.css"
    script_file = workspace_root / "app.js"

    checklist = [
        {"id": "prep", "label": "Freeze plan before execution", "status": "done"},
        {"id": "fe", "label": "Frontend generation finished", "status": "pending"},
        {"id": "qa", "label": "QA smoke test passed", "status": "pending"},
    ]

    async def emit_progress(percent: int, label: str, role: str, task_id: Optional[str], stage: str) -> None:
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=task_id,
            role=role,
            demo_stage=stage,
            plan_id=run.plan_id,
            event_type="progress",
            payload={"percent": percent, "label": label},
            seq=run.next_seq(),
        )

    try:
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="run.started",
            payload={
                "prompt": prompt,
                "mode": "coding-demo",
                "variants": variants,
                "plan_id": run.plan_id,
            },
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="checklist.upsert",
            payload={"items": checklist},
            seq=run.next_seq(),
        )

        bootstrap_html = (
            "<!doctype html><html><body><h1>Live Coding Demo</h1><p data-marker='boot'>Bootstrapping...</p></body></html>"
        )
        index_file.write_text(bootstrap_html, encoding="utf-8")
        styles_file.write_text("/* bootstrapping */", encoding="utf-8")
        script_file.write_text("/* bootstrapping */", encoding="utf-8")
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T0",
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="step.changed",
            payload={"step": "bootstrap", "detail": "Preparing workspace files"},
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="T0",
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="fs.changed",
            payload={
                "changes": [
                    {"path": str(index_file), "op": "write"},
                    {"path": str(styles_file), "op": "write"},
                    {"path": str(script_file), "op": "write"},
                ]
            },
            seq=run.next_seq(),
        )
        await emit_progress(8, "Workspace initialized", "frontend", "T0", "worker")
        await _create_or_reload_preview(run, bootstrap_html, create_if_missing=True, role="frontend", demo_stage="worker")

        emitted_variants: List[str] = []
        for index, task in enumerate(tasks if tasks else [{"id": "T1", "variant": "skeleton", "title": "Skeleton"}], start=1):
            if run.cancel_event.is_set():
                raise asyncio.CancelledError

            task_id = str(task.get("id") or f"T{index}")
            variant = str(task.get("variant") or "skeleton").strip().lower()
            emitted_variants.append(variant)
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="step.changed",
                payload={"step": f"build_{variant}", "detail": str(task.get("title") or variant)},
                seq=run.next_seq(),
            )
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="log.append",
                payload={"level": "info", "text": f"[frontend/{task_id}] Rendering {variant}"},
                seq=run.next_seq(),
            )
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="message.delta",
                payload={"delta": f"Applying {variant} module\n"},
                seq=run.next_seq(),
            )

            html_artifacts = _build_variant_html(prompt, emitted_variants)
            index_file.write_text(str(html_artifacts["index_html"]), encoding="utf-8")
            styles_file.write_text(str(html_artifacts["styles_css"]), encoding="utf-8")
            script_file.write_text(str(html_artifacts["app_js"]), encoding="utf-8")
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="fs.changed",
                payload={
                    "changes": [
                        {"path": str(index_file), "op": "write"},
                        {"path": str(styles_file), "op": "write"},
                        {"path": str(script_file), "op": "write"},
                    ]
                },
                seq=run.next_seq(),
            )
            await _create_or_reload_preview(
                run,
                str(html_artifacts["index_html"]),
                create_if_missing=False,
                role="frontend",
                demo_stage="worker",
            )
            await emit_progress(min(82, 15 + index * 14), f"Task {task_id} done", "frontend", task_id, "worker")
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id=task_id,
                role="frontend",
                demo_stage="worker",
                plan_id=run.plan_id,
                event_type="checklist.checked",
                payload={"id": task_id, "evidence": str(index_file)},
                seq=run.next_seq(),
            )
            await asyncio.sleep(0.2 if not long_mode else 0.45)

        checklist[1]["status"] = "done"
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="FE",
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="checklist.checked",
            payload={"id": "fe", "evidence": "frontend tasks completed"},
            seq=run.next_seq(),
        )

        state["stage"] = "test"
        _save_demo_state(run.session_id, state)
        await emit_progress(88, "Frontend completed, handoff to QA", "qa", "QA", "test")

        final_html = index_file.read_text(encoding="utf-8")
        inject_failure = bool(metadata.get("force_test_fail"))
        success, test_payload = await _run_demo_smoke_tests(
            run,
            final_html,
            variants,
            inject_failure=inject_failure,
        )

        if not success:
            state["last_test_status"] = "failed"
            state["stage"] = "planning"
            _save_demo_state(run.session_id, state)
            await _emit(
                session_id=run.session_id,
                run_id=run.run_id,
                task_id="QA",
                role="qa",
                demo_stage="test",
                plan_id=run.plan_id,
                event_type="message.error",
                payload={"message": str(test_payload.get("reason") or "test failed")},
                seq=run.next_seq(),
            )
            run.state = "failed"
            return

        state["last_test_status"] = "passed"
        checklist[2]["status"] = "done"
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="QA",
            role="qa",
            demo_stage="test",
            plan_id=run.plan_id,
            event_type="checklist.checked",
            payload={"id": "qa", "evidence": "demo_smoke passed"},
            seq=run.next_seq(),
        )

        state["stage"] = "complete"
        _save_demo_state(run.session_id, state)

        await emit_progress(100, "Demo complete", "qa", "QA", "complete")
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="QA",
            role="qa",
            demo_stage="complete",
            plan_id=run.plan_id,
            event_type="run.completed",
            payload={"status": "ok", "preview_id": run.preview_id},
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="QA",
            role="qa",
            demo_stage="complete",
            plan_id=run.plan_id,
            event_type="complete.ready",
            payload={
                "preview_url": f"/api/preview/{run.preview_id}/content" if run.preview_id else "",
                "preview_id": run.preview_id,
            },
            seq=run.next_seq(),
        )
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="QA",
            role="qa",
            demo_stage="complete",
            plan_id=run.plan_id,
            event_type="message.end",
            payload={"content": "Live coding run completed."},
            seq=run.next_seq(),
        )
        run.state = "completed"
    except asyncio.CancelledError:
        run.state = "cancelled"
        state["stage"] = "planning"
        _save_demo_state(run.session_id, state)
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="message.cancelled",
            payload={"reason": "user_cancelled"},
            seq=run.next_seq(),
        )
    except Exception as exc:
        run.state = "failed"
        state["stage"] = "planning"
        _save_demo_state(run.session_id, state)
        logger.exception("Coding demo run failed: %s", exc)
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role="frontend",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="message.error",
            payload={"message": str(exc)},
            seq=run.next_seq(),
        )
    finally:
        await _terminate_child_processes(run)
        async with _run_lock:
            active = _active_runs.get(run.session_id)
            if active and active.run_id == run.run_id:
                _active_runs.pop(run.session_id, None)


async def _run_deliver_pipeline_wrapper(run: CodingRunContext, prompt: str, state: Dict[str, Any], metadata: Dict[str, Any]) -> None:
    try:
        await run_deliver_pipeline(
            run=run,
            prompt=prompt,
            state=state,
            metadata=metadata,
            emit=_emit,
            run_command=_run_command,
            terminate_child_processes=_terminate_child_processes,
            save_state=_save_demo_state,
        )
    except asyncio.CancelledError:
        run.state = "cancelled"
        state["stage"] = "planning"
        _save_demo_state(run.session_id, state)
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role="system",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="message.cancelled",
            payload={"reason": "user_cancelled"},
            seq=run.next_seq(),
        )
    except Exception as exc:
        run.state = "failed"
        state["stage"] = "planning"
        _save_demo_state(run.session_id, state)
        logger.exception("Deliver page spec pipeline failed: %s", exc)
        await _emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id=run.task_id,
            role="system",
            demo_stage="worker",
            plan_id=run.plan_id,
            event_type="message.error",
            payload={"message": str(exc)},
            seq=run.next_seq(),
        )
    finally:
        await _terminate_child_processes(run)
        async with _run_lock:
            active = _active_runs.get(run.session_id)
            if active and active.run_id == run.run_id:
                _active_runs.pop(run.session_id, None)


async def start_run(session_id: str, prompt: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta = metadata if isinstance(metadata, dict) else {}
    state = _load_demo_state(session_id)
    forced_variant = str(meta.get("variant") or "").strip().lower()
    if forced_variant and forced_variant in KNOWN_VARIANTS:
        requirements = state.get("requirements") if isinstance(state.get("requirements"), dict) else _default_requirements()
        requirements["variants"] = [forced_variant]
        state["requirements"] = requirements
        state["plan"] = _default_plan(requirements)
        if not state.get("plan_id"):
            state["plan_id"] = f"plan_{uuid.uuid4().hex[:10]}"
        if not state.get("run_id"):
            state["run_id"] = f"demo_run_{uuid.uuid4().hex}"
        _save_demo_state(session_id, state)

    if state.get("stage") == "discussion" or not state.get("spec_frozen"):
        return {
            "ok": False,
            "reason": "planning_not_frozen",
            "stage": state.get("stage") or "discussion",
            "spec_frozen": bool(state.get("spec_frozen")),
        }

    long_mode = bool(meta.get("long_mode") or meta.get("longMode"))
    req = state.get("requirements") if isinstance(state.get("requirements"), dict) else {}
    delivery_variant = str(meta.get("delivery_variant") or req.get("delivery_variant") or "").strip().lower()
    if delivery_variant == "deliver_page_spec":
        contract_id = str(meta.get("contract_id") or req.get("contract_id") or "").strip().lower()
        if contract_id not in KNOWN_CONTRACTS:
            return {
                "ok": False,
                "reason": "invalid_contract",
                "stage": "planning",
                "spec_frozen": bool(state.get("spec_frozen")),
            }

    run_id = str(state.get("run_id") or meta.get("run_id") or f"demo_run_{uuid.uuid4().hex}")
    plan_id = str(state.get("plan_id") or f"plan_{uuid.uuid4().hex[:10]}")
    first_task = "T1"
    plan = state.get("plan") if isinstance(state.get("plan"), dict) else {}
    tasks = plan.get("tasks") if isinstance(plan.get("tasks"), list) else []
    if tasks and isinstance(tasks[0], dict):
        first_task = str(tasks[0].get("id") or "T1")

    async with _run_lock:
        active = _active_runs.get(session_id)
        if active and active.state in {"running", "cancelling"}:
            return {
                "ok": False,
                "reason": "concurrent_run",
                "run_id": active.run_id,
            }

        run = CodingRunContext(
            session_id=session_id,
            run_id=run_id,
            plan_id=plan_id,
            task_id=first_task,
        )
        latest = latest_stream_run(session_id)
        if latest and latest.get("run_id") == run_id:
            run.seq = int(latest.get("last_seq") or 0)
        _active_runs[session_id] = run

    state["stage"] = "worker"
    state["run_id"] = run_id
    state["plan_id"] = plan_id
    state["last_test_status"] = None
    _save_demo_state(session_id, state)

    delivery_variant = str(meta.get("delivery_variant") or req.get("delivery_variant") or "").strip().lower()
    if delivery_variant == "deliver_page_spec":
        run.task = asyncio.create_task(_run_deliver_pipeline_wrapper(run, prompt=prompt, state=state, metadata=meta))
    else:
        run.task = asyncio.create_task(_run_demo_pipeline(run, prompt=prompt, long_mode=long_mode, state=state, metadata=meta))
    return {"ok": True, "run_id": run.run_id, "task_id": run.task_id, "plan_id": plan_id}


async def handle_ask_query(session_id: str, run_id: str, scope: str, key: str) -> Dict[str, Any]:
    state = _load_demo_state(session_id)
    target_run = run_id or str(state.get("run_id") or "")
    if not target_run:
        return {
            "ok": False,
            "reason": "run_id_required",
        }

    events = list_events(session_id=session_id, run_id=target_run, after_seq=0, limit=5000)
    recent_events = events[-150:]

    files: List[Dict[str, str]] = []
    by_role_progress: Dict[str, int] = {}
    task_status: Dict[str, str] = {}
    blockers: List[str] = []
    for event in recent_events:
        event_role = str(event.get("role") or "unknown")
        event_type = str(event.get("type") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event_type == "progress":
            by_role_progress[event_role] = int(payload.get("percent") or 0)
        if event_type == "fs.changed":
            for change in payload.get("changes", []):
                if isinstance(change, dict) and change.get("path"):
                    files.append(
                        {
                            "path": str(change["path"]),
                            "role": event_role,
                            "task_id": str(event.get("task_id") or ""),
                            "op": str(change.get("op") or "write"),
                        }
                    )
        if event_type == "step.changed":
            task_id = str(event.get("task_id") or "unknown")
            task_status[task_id] = str(payload.get("step") or "working")
        if event_type == "test.failed":
            blockers.append(str(payload.get("reason") or "test_failed"))

    unique_files: List[Dict[str, str]] = []
    seen_paths: set[str] = set()
    for item in reversed(files):
        path = item["path"]
        if path in seen_paths:
            continue
        seen_paths.add(path)
        unique_files.append(item)
        if len(unique_files) >= 6:
            break
    unique_files.reverse()

    if scope == "role":
        summary = f"Role {key} progress {by_role_progress.get(key, 0)}%"
    elif scope == "task":
        summary = f"Task {key} status {task_status.get(key, 'pending')}"
    elif scope == "file":
        summary = f"File scope {key}, recent file writes {len(unique_files)}"
    else:
        summary = f"Stage {state.get('stage')} with {len(recent_events)} recent events"

    reply = {
        "summary": summary,
        "artifacts_path": str(Path("workspace/runs") / session_id / target_run / "artifacts"),
        "spec_hash": str(state.get("plan", {}).get("spec_hash") or ""),
        "contract_id": str(state.get("requirements", {}).get("contract_id") or ""),
        "provider": str(state.get("requirements", {}).get("provider") or ""),
        "framework": str(state.get("requirements", {}).get("framework") or ""),
        "blockers": blockers,
        "next_steps": [
            "Continue frontend implementation" if state.get("stage") in {"worker", "planning"} else "Ready for completion review",
            "Run stop command if output diverges",
        ],
        "recent_files": unique_files,
        "percent_by_role": by_role_progress,
        "task_status": task_status,
    }

    await _emit(
        session_id=session_id,
        run_id=target_run,
        task_id=None,
        role="system",
        demo_stage=str(state.get("stage") or "worker"),
        plan_id=state.get("plan_id"),
        event_type="ask.reply",
        payload=reply,
    )
    return {"ok": True, "reply": reply, "run_id": target_run}


def _get_command_result(session_id: str, command_id: str) -> Optional[Dict[str, Any]]:
    _ensure_command_schema()
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT result_json FROM coding_command_dedup WHERE session_id = ? AND command_id = ?",
        (session_id, command_id),
    ).fetchone()
    if not row or not row[0]:
        return None
    try:
        payload = json.loads(row[0])
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _save_command_result(session_id: str, command_id: str, command_type: str, result: Dict[str, Any]) -> None:
    _ensure_command_schema()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO coding_command_dedup(session_id, command_id, command_type, result_json, created_at)
        VALUES (?, ?, ?, ?, strftime('%s','now'))
        ON CONFLICT(session_id, command_id) DO UPDATE SET result_json=excluded.result_json
        """,
        (session_id, command_id, command_type, json.dumps(result, ensure_ascii=False)),
    )
    conn.commit()


async def request_stop(session_id: str, run_id: str, command_id: str, reason: str) -> Dict[str, Any]:
    existing = _get_command_result(session_id, command_id)
    if existing:
        return existing

    async with _run_lock:
        active = _active_runs.get(session_id)

    if not active or active.run_id != run_id:
        ack = {
            "status": "rejected",
            "reason": "run_not_found",
            "command_id": command_id,
            "run_id": run_id,
            "session_id": session_id,
        }
        _save_command_result(session_id, command_id, "stop", ack)
        await _emit(
            session_id=session_id,
            run_id=run_id,
            task_id=None,
            role="system",
            demo_stage="worker",
            plan_id=None,
            event_type="control.ack",
            payload=ack,
        )
        return ack

    active.state = "cancelling"
    active.cancel_event.set()
    if active.task and not active.task.done():
        active.task.cancel()

    ack = {
        "status": "accepted",
        "reason": reason,
        "command_id": command_id,
        "run_id": run_id,
        "session_id": session_id,
    }
    _save_command_result(session_id, command_id, "stop", ack)
    await _emit(
        session_id=session_id,
        run_id=run_id,
        task_id=active.task_id,
        role="system",
        demo_stage="worker",
        plan_id=active.plan_id,
        event_type="control.ack",
        payload=ack,
        seq=active.next_seq(),
    )
    return ack


def get_active_run(session_id: str) -> Optional[Dict[str, Any]]:
    active = _active_runs.get(session_id)
    if not active:
        return None
    return {
        "session_id": active.session_id,
        "run_id": active.run_id,
        "task_id": active.task_id,
        "state": active.state,
        "seq": active.seq,
        "preview_id": active.preview_id,
        "plan_id": active.plan_id,
    }
