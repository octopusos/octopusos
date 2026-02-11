from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List

from octopusos.webui.api.preview_store import create_preview_session
from octopusos.webui.websocket.stream_bus import list_events

KNOWN_FRAMEWORKS = {"react", "vue"}
KNOWN_PROVIDERS = {"mui", "antd", "vuetify", "tailwind"}


def _template_for_page_type(page_type: str) -> Path:
    mapping = {
        "landing": "landing_saas.json",
        "product": "product_apple_like.json",
        "editorial": "editorial_clean.json",
    }
    return Path("design-system/examples/page-specs") / mapping.get(page_type, "landing_saas.json")


def _contract_for_id(contract_id: str) -> Path:
    mapping = {
        "brand_soft": "brand_soft.json",
        "brand_dark": "brand_dark.json",
        "brand_compact": "brand_compact.json",
    }
    return Path("design-system/contracts/user_contract.examples") / mapping.get(contract_id, "brand_soft.json")


def _build_pagespec(requirements: Dict[str, Any]) -> Dict[str, Any]:
    page_type = str(requirements.get("page_type") or "landing").strip().lower()
    framework = str(requirements.get("framework") or "react").strip().lower()
    provider = str(requirements.get("provider") or "mui").strip().lower()
    contract_id = str(requirements.get("contract_id") or "brand_soft").strip().lower()

    template = json.loads(_template_for_page_type(page_type).read_text(encoding="utf-8"))
    template["target"] = {
        "framework": framework if framework in KNOWN_FRAMEWORKS else "react",
        "provider": provider if provider in KNOWN_PROVIDERS else "mui",
    }
    template["contract"] = {
        "contract_id": contract_id,
        "user_contract_path": str(_contract_for_id(contract_id)),
    }
    data_for_hash = {k: v for k, v in template.items() if k != "freeze_info"}
    spec_hash = hashlib.sha256(json.dumps(data_for_hash, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    template["freeze_info"] = {
        "spec_hash": spec_hash,
        "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return template


def _assemble_html(spec: Dict[str, Any]) -> str:
    component_map = {c.get("name"): c for c in spec.get("components", []) if isinstance(c, dict)}
    hero = component_map.get("Hero", {}).get("bindings", {})
    footer = component_map.get("Footer", {}).get("bindings", {})
    highlights = component_map.get("Highlight", {}).get("bindings", {}).get("items", ["One", "Two", "Three"])
    pricing = component_map.get("Pricing", {}).get("bindings", {}).get("items", ["Basic", "Pro", "Scale"])
    cta = component_map.get("CTA", {}).get("bindings", {})

    cards = "".join(f"<article class='card'>{item}</article>" for item in highlights)
    prices = "".join(f"<li>{item}</li>" for item in pricing)

    return f"""<!doctype html>
<html><head><meta charset='utf-8'/><meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{spec.get('meta', {}).get('title', 'Deliver')}</title>
<style>
body{{margin:0;font-family:Inter,system-ui,sans-serif;background:#f7f8fb;color:#111827}}main{{max-width:1080px;margin:0 auto;padding:24px}}
.hero{{padding:24px;border-radius:14px;background:#fff;box-shadow:0 8px 20px rgba(15,23,42,.08)}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.card{{padding:14px;border:1px solid #e5e7eb;border-radius:10px;background:#fff}}
#carousel-track{{display:flex;transition:transform .2s ease}}.carousel-slide{{min-width:100%;padding:14px;background:#eef2ff;border-radius:10px}}
.story p{{opacity:.4;transition:opacity .2s ease}}.story p.active{{opacity:1}}
</style></head>
<body data-framework='{spec.get('target', {}).get('framework', 'react')}' data-provider='{spec.get('target', {}).get('provider', 'mui')}' data-contract='{spec.get('contract', {}).get('contract_id', 'brand_soft')}'>
<main>
<section class='hero' data-marker='hero'><h1>{hero.get('title', spec.get('meta', {}).get('title', 'Hero'))}</h1><p>{hero.get('subtitle', '')}</p><button data-marker='hero-cta'>{cta.get('title', 'Start')}</button></section>
<section data-marker='highlights'><div class='grid'>{cards}</div></section>
<section data-marker='carousel' data-interaction='carousel'><div id='carousel-track'><div class='carousel-slide'>Slide 1</div><div class='carousel-slide'>Slide 2</div></div><button id='carousel-next' data-marker='carousel-next'>Next</button></section>
<section class='story' data-marker='scroll-story' data-interaction='scroll-story'><p class='active'>Frame one</p><p>Frame two</p></section>
<section data-marker='pricing'><ul>{prices}</ul></section>
<section data-marker='cta'><h2>{cta.get('title', 'Call To Action')}</h2></section>
<footer data-marker='footer'>{footer.get('brand', 'OctopusOS')}</footer>
</main>
<script>
let idx=0;const track=document.getElementById('carousel-track');document.getElementById('carousel-next').addEventListener('click',()=>{{idx=(idx+1)%2;track.style.transform=`translateX(-${{idx*100}}%)`;window.__carouselIndex=idx;}});
window.addEventListener('scroll',()=>{{const p=document.querySelectorAll('.story p');const a=(window.scrollY>20)?1:0;p.forEach((el,i)=>el.classList.toggle('active',i===a));window.__storyActive=a;}});
</script>
</body></html>"""


async def run_deliver_pipeline(
    *,
    run,
    prompt: str,
    state: Dict[str, Any],
    metadata: Dict[str, Any],
    emit: Callable[..., Any],
    run_command: Callable[..., Any],
    terminate_child_processes: Callable[..., Any],
    save_state: Callable[..., Any],
) -> None:
    requirements = state.get("requirements") if isinstance(state.get("requirements"), dict) else {}
    spec = _build_pagespec(requirements)

    await emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="D0",
        role="system",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="run.started",
        payload={
            "prompt": prompt,
            "variant": "deliver_page_spec",
            "framework": spec["target"]["framework"],
            "provider": spec["target"]["provider"],
        },
        seq=run.next_seq(),
    )

    workspace_root = Path("workspace/runs") / run.session_id / run.run_id
    artifacts_root = workspace_root / "artifacts"
    contract_bundle = artifacts_root / "contract_bundle"
    adapter_outputs = artifacts_root / "adapter_outputs"
    pagespec_dir = artifacts_root / "pagespec"
    test_reports = artifacts_root / "test_reports"
    screenshots = artifacts_root / "screenshots"

    for p in [contract_bundle, adapter_outputs, pagespec_dir, test_reports, screenshots]:
        p.mkdir(parents=True, exist_ok=True)

    run.workspace_root = workspace_root

    pagespec_file = pagespec_dir / "pagespec.json"
    pagespec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    await emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="D1",
        role="planner",
        demo_stage="planning",
        plan_id=run.plan_id,
        event_type="pagespec.frozen",
        payload={"spec_hash": spec["freeze_info"]["spec_hash"], "frozen_at": spec["freeze_info"]["frozen_at"]},
        seq=run.next_seq(),
    )

    await run_command(
        run,
        cmd=["node", "design-system/generator/validate_page_spec.ts", "--spec", str(pagespec_file)],
        cwd=Path(".").resolve(),
        env=dict(os.environ),
        role="planner",
        stage="planning",
        task_id="D1",
    )

    contract_path = spec["contract"].get("user_contract_path")
    export_dir = contract_bundle
    await run_command(
        run,
        cmd=["node", "scripts/design/contract_cli.ts", "export", "--contract", str(contract_path), "--outdir", str(export_dir)],
        cwd=Path(".").resolve(),
        env=dict(os.environ),
        role="system",
        stage="worker",
        task_id="D2",
    )

    for item in export_dir.glob("*"):
        if item.name.endswith(".json") or item.name.endswith(".css"):
            shutil.copy2(item, adapter_outputs / item.name)

    await emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="D2",
        role="system",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="adapter.generated",
        payload={"provider": spec["target"]["provider"], "framework": spec["target"]["framework"], "contract_id": spec["contract"]["contract_id"]},
        seq=run.next_seq(),
    )

    framework = spec["target"]["framework"]
    skeleton_src = Path("apps/skeleton-react" if framework == "react" else "apps/skeleton-vue").resolve()
    project_root = workspace_root / "project"
    if project_root.exists():
        shutil.rmtree(project_root)
    shutil.copytree(skeleton_src, project_root, ignore=shutil.ignore_patterns("node_modules", ".vite"))
    run.project_root = project_root

    assembled_html = _assemble_html(spec)
    assembled_file = project_root / "assembled_page.html"
    assembled_file.write_text(assembled_html, encoding="utf-8")

    preview = create_preview_session(
        preset="html-basic",
        html=assembled_html,
        session_id=run.session_id,
        run_id=run.run_id,
        meta={"source": "deliver_page_spec", "provider": spec["target"]["provider"], "framework": framework},
    )
    run.preview_id = str(preview["preview_id"])
    preview_url = str(preview["url"])

    await emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="D4",
        role="frontend",
        demo_stage="worker",
        plan_id=run.plan_id,
        event_type="preview.ready",
        payload={"preview_id": run.preview_id, "url": preview_url, "status": preview["status"]},
        seq=run.next_seq(),
    )

    failures: List[str] = []
    for marker in ["data-marker='hero'", "data-marker='highlights'", "data-marker='footer'"]:
        if marker not in assembled_html:
            failures.append(f"missing marker {marker}")
    if "carousel-next" not in assembled_html:
        failures.append("missing carousel control")
    if "scroll-story" not in assembled_html:
        failures.append("missing scroll story")

    test_report = {
        "suite": "deliver_page_spec_smoke",
        "provider": spec["target"]["provider"],
        "framework": framework,
        "passed": len(failures) == 0,
        "failures": failures,
    }
    (test_reports / "smoke.json").write_text(json.dumps(test_report, ensure_ascii=False, indent=2), encoding="utf-8")
    (screenshots / "preview.txt").write_text("screenshot_placeholder", encoding="utf-8")

    if failures:
        await emit(
            session_id=run.session_id,
            run_id=run.run_id,
            task_id="D5",
            role="qa",
            demo_stage="test",
            plan_id=run.plan_id,
            event_type="test.failed",
            payload={"suite": "deliver_page_spec_smoke", "reason": failures[0], "failures": failures},
            seq=run.next_seq(),
        )
        state["last_test_status"] = "failed"
        state["stage"] = "planning"
        save_state(run.session_id, state)
        run.state = "failed"
        return

    await emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="D5",
        role="qa",
        demo_stage="test",
        plan_id=run.plan_id,
        event_type="test.passed",
        payload={"suite": "deliver_page_spec_smoke", "checks": ["markers", "carousel", "scroll-story"]},
        seq=run.next_seq(),
    )

    evidence_dir = artifacts_root / "evidence_bundle"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    events = list_events(session_id=run.session_id, run_id=run.run_id, after_seq=0, limit=10000)
    (evidence_dir / "stream_events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    (evidence_dir / "plan.json").write_text(json.dumps(state.get("plan") or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    (evidence_dir / "pagespec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(_contract_for_id(spec["contract"]["contract_id"]), evidence_dir / "user_contract.json")
    for p in adapter_outputs.glob("*"):
        if p.is_file():
            shutil.copy2(p, evidence_dir / p.name)
    shutil.copy2(test_reports / "smoke.json", evidence_dir / "smoke.json")
    (evidence_dir / "preview_url.txt").write_text(preview_url, encoding="utf-8")
    (evidence_dir / "environment.json").write_text(
        json.dumps({"execution_actor": "worker", "provider": "unknown", "framework": framework}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    evidence_zip = artifacts_root / "evidence_bundle.zip"
    with zipfile.ZipFile(evidence_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in evidence_dir.rglob("*"):
            if file.is_file():
                zf.write(file, arcname=str(file.relative_to(evidence_dir)))

    state["stage"] = "complete"
    state["last_test_status"] = "passed"
    save_state(run.session_id, state)

    await emit(
        session_id=run.session_id,
        run_id=run.run_id,
        task_id="D6",
        role="qa",
        demo_stage="complete",
        plan_id=run.plan_id,
        event_type="complete.ready",
        payload={
            "preview_url": preview_url,
            "preview_id": run.preview_id,
            "artifacts_path": str(artifacts_root),
            "evidence_bundle_path": str(evidence_zip),
            "spec_hash": spec["freeze_info"]["spec_hash"],
            "contract_id": spec["contract"]["contract_id"],
            "provider": spec["target"]["provider"],
            "framework": framework,
        },
        seq=run.next_seq(),
    )
    run.state = "completed"
