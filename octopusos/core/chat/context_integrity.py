"""Context integrity gate and truncation recovery orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from octopusos.core.audit import log_audit_event
from octopusos.core.chat.service import ChatService
from octopusos.core.memory.service import MemoryService
from octopusos.core.project_kb.service import ProjectKBService
from octopusos.core.memory.budgeter import ContextBudget as MemoryContextBudget


logger = logging.getLogger(__name__)

REASON_CODE_CONTEXT_TRUNCATION_RECOVERY = "CONTEXT_TRUNCATION_RECOVERY"
EVENT_CONTEXT_INTEGRITY_DEGRADED = "CONTEXT_INTEGRITY_DEGRADED"
EVENT_CONTEXT_RECOVERY_APPLIED = "CONTEXT_RECOVERY_APPLIED"
EVENT_CONTEXT_RECOVERY_DROPPED_CROSSTALK = "CONTEXT_RECOVERY_DROPPED_CROSSTALK"


def _estimate_tokens(text: str) -> int:
    return int(len(text) * 1.3)


@dataclass
class RecoveryItem:
    source: str
    item_id: str
    content: str
    score: float
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "item_id": self.item_id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class RecoveryResult:
    recovered_items: List[RecoveryItem]
    coverage_summary: Dict[str, Any]
    dropped_due_to_budget: List[Dict[str, Any]]
    dropped_due_to_scope: List[Dict[str, Any]] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovered_items": [item.to_dict() for item in self.recovered_items],
            "coverage_summary": self.coverage_summary,
            "dropped_due_to_budget": self.dropped_due_to_budget,
            "dropped_due_to_scope": self.dropped_due_to_scope or [],
        }


class ContextRecoveryService:
    """Best-effort recovery service for truncation compensation."""

    def __init__(
        self,
        chat_service: Optional[ChatService] = None,
        memory_service: Optional[MemoryService] = None,
        kb_service: Optional[ProjectKBService] = None,
    ):
        self.chat_service = chat_service or ChatService()
        self.memory_service = memory_service or MemoryService()
        self.kb_service = kb_service or ProjectKBService()

    def recover(
        self,
        *,
        session_id: str,
        project_id: Optional[str],
        scope: str,
        missing_markers: List[str],
        budget_tokens: int,
        reason_code: str,
        query: str,
    ) -> RecoveryResult:
        if not scope:
            raise ValueError("scope is required for recovery retrieval")
        if scope != "global" and not session_id:
            raise ValueError("session_id is required when scope != global")

        recovered: List[RecoveryItem] = []
        dropped: List[Dict[str, Any]] = []
        by_source = {"memory": 0, "kb": 0, "rag": 0, "brain": 0}
        seen_hashes: set[str] = set()
        used_tokens = 0

        def try_add(item: RecoveryItem) -> None:
            nonlocal used_tokens
            digest = hashlib.sha256(item.content.encode("utf-8")).hexdigest()
            if digest in seen_hashes:
                return
            item_tokens = _estimate_tokens(item.content)
            if used_tokens + item_tokens > budget_tokens:
                dropped.append(
                    {
                        "source": item.source,
                        "item_id": item.item_id,
                        "tokens_est": item_tokens,
                        "reason": "budget_exceeded",
                    }
                )
                return
            seen_hashes.add(digest)
            used_tokens += item_tokens
            recovered.append(item)
            by_source[item.source] = by_source.get(item.source, 0) + 1

        # 1) MemoryOS session-scoped recovery
        memory_items = self._recover_from_memory(
            session_id=session_id,
            project_id=project_id,
            scope=scope,
            missing_markers=missing_markers,
            query=query,
        )
        for item in memory_items:
            try_add(item)

        # 2) KB project-scoped recovery
        kb_items = self._recover_from_kb(
            session_id=session_id,
            project_id=project_id,
            scope=scope,
            query=query,
            top_k=10,
            source_label="kb",
        )
        for item in kb_items:
            try_add(item)

        # 3) RAG recovery path (larger candidate set, same scope checks)
        rag_items = self._recover_from_kb(
            session_id=session_id,
            project_id=project_id,
            scope=scope,
            query=query,
            top_k=16,
            source_label="rag",
        )
        for item in rag_items:
            try_add(item)

        # 4) BrainOS is optional in current runtime; keep explicit empty result for auditability
        coverage_summary = {
            "reason_code": reason_code,
            "recovered_count": len(recovered),
            "used_tokens_est": used_tokens,
            "budget_tokens": budget_tokens,
            "sources_breakdown": by_source,
            "markers_requested": len(missing_markers),
            "markers": missing_markers,
        }
        return RecoveryResult(
            recovered_items=recovered,
            coverage_summary=coverage_summary,
            dropped_due_to_budget=dropped,
            dropped_due_to_scope=[],
        )

    def _recover_from_memory(
        self,
        *,
        session_id: str,
        project_id: Optional[str],
        scope: str,
        missing_markers: List[str],
        query: str,
    ) -> List[RecoveryItem]:
        items: List[RecoveryItem] = []

        # Use current memory service context first.
        try:
            context = self.memory_service.build_context(
                agent_id="webui_chat",
                project_id=project_id,
                agent_type="chat",
                confidence_threshold=0.2,
                budget=MemoryContextBudget(max_memories=20, max_tokens=1800),
            )
            for mem in context.get("memories", []) or []:
                content = json.dumps(mem.get("content", {}), ensure_ascii=False)
                items.append(
                    RecoveryItem(
                        source="memory",
                        item_id=str(mem.get("id") or ""),
                        content=content,
                        score=float(mem.get("confidence") or 0.0),
                        metadata={"scope": mem.get("scope"), "project_id": mem.get("project_id")},
                    )
                )
        except Exception as e:
            logger.warning(f"Memory build_context recovery failed: {e}")

        # If markers were dropped from recent window, scan full session history and compress marker facts.
        try:
            all_msgs = self.chat_service.get_messages(session_id=session_id)
            marker_lines: List[str] = []
            for msg in all_msgs:
                if msg.role != "user":
                    continue
                content = msg.content or ""
                for raw in re.findall(r"\bFACT_[A-Z]\d+\s*=\s*[^\s,;]+", content):
                    marker_lines.append(raw.strip())

            if marker_lines:
                compact = sorted(set(marker_lines))
                chunk_size = 24
                for idx in range(0, len(compact), chunk_size):
                    chunk = compact[idx: idx + chunk_size]
                    items.append(
                        RecoveryItem(
                            source="memory",
                            item_id=f"session_markers_{idx // chunk_size + 1}",
                            content="Session continuity markers:\n" + "\n".join(chunk),
                            score=0.9,
                            metadata={
                                "scope": scope,
                                "project_id": project_id,
                                "session_id": session_id,
                                "origin": "chat_store_session_scan_compact",
                                "marker_count": len(chunk),
                            },
                        )
                    )
        except Exception as e:
            logger.warning(f"Session scan recovery failed: {e}")

        return items

    def _recover_from_kb(
        self,
        *,
        session_id: str,
        project_id: Optional[str],
        scope: str,
        query: str,
        top_k: int,
        source_label: str,
    ) -> List[RecoveryItem]:
        if not scope:
            raise ValueError("scope is required for retrieval")
        if not session_id and scope != "global":
            raise ValueError("session_id is required for non-global retrieval")

        items: List[RecoveryItem] = []
        try:
            results, trace = self.kb_service.search_with_trace(
                query=query,
                scope="current_repo",
                top_k=top_k,
                explain=True,
            )
            for r in results:
                data = r.to_dict()
                # Cross-session protection: keep only global/project-neutral docs unless explicit global scope.
                r_session = data.get("session_id")
                if r_session and scope != "global" and r_session != session_id:
                    continue
                content = str(data.get("content") or "")
                if not content:
                    continue
                items.append(
                    RecoveryItem(
                        source=source_label,
                        item_id=str(data.get("chunk_id") or data.get("path") or ""),
                        content=content[:1000],
                        score=float(data.get("score") or 0.0),
                        metadata={
                            "scope": scope,
                            "project_id": project_id,
                            "session_id": session_id,
                            "retrieval_run_id": trace.get("retrieval_run_id"),
                            "policy_snapshot_hash": trace.get("policy_snapshot_hash"),
                            "path": data.get("path"),
                        },
                    )
                )
        except Exception as e:
            logger.warning(f"{source_label} recovery failed: {e}")
        return items


class ContextIntegrityGate:
    """Single-entry integrity gate between prompt assembly and model invocation."""

    def __init__(
        self,
        *,
        recovery_service: ContextRecoveryService,
        chat_service: Optional[ChatService] = None,
        artifact_root: Optional[Path] = None,
    ):
        self.recovery_service = recovery_service
        self.chat_service = chat_service or ChatService()
        self.artifact_root = artifact_root or Path("outputs/context_integrity_runtime")

    def enforce(
        self,
        *,
        context_pack: Any,
        session_id: str,
        project_id: Optional[str],
        scope: str,
        user_input: str,
    ) -> Any:
        metadata = dict(context_pack.metadata or {})
        trim = metadata.get("trimming") or {}
        trimmed_window = int(trim.get("trimmed_window", 0))
        trimmed_memory = int(trim.get("trimmed_memory", 0))
        trimmed_rag = int(trim.get("trimmed_rag", 0))

        truncated_blocks: List[str] = []
        if trimmed_window > 0:
            truncated_blocks.append("recent_messages")
        if trimmed_memory > 0:
            truncated_blocks.append("user_facts")
        if trimmed_rag > 0:
            truncated_blocks.append("rag_snippets")

        truncated = len(truncated_blocks) > 0
        required_fallback = "none"
        if truncated and any(block in {"recent_messages", "user_facts"} for block in truncated_blocks):
            required_fallback = "multi"

        reason_code = REASON_CODE_CONTEXT_TRUNCATION_RECOVERY
        missing_markers = trim.get("dropped_markers") or []
        integrity = {
            "truncated": truncated,
            "truncated_blocks": truncated_blocks,
            "estimated_tokens_before": int(trim.get("tokens_before", metadata.get("total_tokens", 0))),
            "estimated_tokens_after": int(trim.get("tokens_after", metadata.get("total_tokens", 0))),
            "required_fallback": required_fallback,
            "reason_code": reason_code,
        }

        recovery_result: Optional[RecoveryResult] = None
        if required_fallback != "none":
            recovery_budget = int((metadata.get("integrity_budget") or {}).get("mcc_recovery_tokens", 1200))
            recovery_result = self.recovery_service.recover(
                session_id=session_id,
                project_id=project_id,
                scope=scope,
                missing_markers=missing_markers,
                budget_tokens=recovery_budget,
                reason_code=reason_code,
                query=user_input,
            )
            recovery_result = self._filter_scope_mismatch(
                recovery_result=recovery_result,
                session_id=session_id,
                project_id=project_id,
                scope=scope,
            )
            self._inject_recovery_prompt(context_pack, recovery_result, truncated=True)
            self._rebalance_prompt_budget(context_pack=context_pack, recovery_result=recovery_result)
            self._log_recovery_audit(session_id=session_id, recovery_result=recovery_result, reason_code=reason_code)
            if not recovery_result.recovered_items:
                integrity["context_integrity_degraded"] = True
                self._log_degraded_audit(session_id=session_id, reason_code=reason_code, recovery_result=recovery_result)
        elif truncated:
            # Even if fallback is not required, emit declaration for observability.
            self._inject_recovery_prompt(context_pack, None, truncated=True)

        integrity["recovery"] = recovery_result.to_dict() if recovery_result else None
        artifact_path = self._write_artifact(
            session_id=session_id,
            context_pack=context_pack,
            integrity=integrity,
        ) if truncated else None
        integrity["artifact_path"] = str(artifact_path) if artifact_path else None

        metadata["context_integrity"] = integrity
        metadata["context_integrity_checked"] = True
        metadata["reason_code"] = reason_code if truncated else metadata.get("reason_code")
        context_pack.metadata = metadata
        context_pack.audit = dict(context_pack.audit or {})
        context_pack.audit["context_integrity"] = integrity
        return context_pack

    def _filter_scope_mismatch(
        self,
        *,
        recovery_result: RecoveryResult,
        session_id: str,
        project_id: Optional[str],
        scope: str,
    ) -> RecoveryResult:
        kept: List[RecoveryItem] = []
        dropped_scope: List[Dict[str, Any]] = []
        for item in recovery_result.recovered_items:
            meta = item.metadata or {}
            source = item.source
            source_session = meta.get("session_id")
            source_project = meta.get("project_id")
            mismatch = False
            reason = ""

            if source == "memory":
                if source_session and source_session != session_id:
                    mismatch = True
                    reason = "session_mismatch"
            elif source in {"kb", "rag"}:
                if source_project and project_id and source_project != project_id:
                    mismatch = True
                    reason = "project_mismatch"
                if source_session and scope != "global" and source_session != session_id:
                    mismatch = True
                    reason = "session_mismatch"

            if mismatch:
                dropped_scope.append(
                    {
                        "source": source,
                        "item_id": item.item_id,
                        "reason": reason,
                        "source_session_id": source_session,
                        "source_project_id": source_project,
                    }
                )
            else:
                kept.append(item)

        if dropped_scope:
            self._log_crosstalk_drop(dropped_scope=dropped_scope, session_id=session_id)

        updated = RecoveryResult(
            recovered_items=kept,
            coverage_summary=dict(recovery_result.coverage_summary),
            dropped_due_to_budget=list(recovery_result.dropped_due_to_budget),
            dropped_due_to_scope=dropped_scope,
        )
        updated.coverage_summary["recovered_count"] = len(kept)
        return updated

    def _inject_recovery_prompt(
        self,
        context_pack: Any,
        recovery_result: Optional[RecoveryResult],
        *,
        truncated: bool,
    ) -> None:
        if not truncated:
            return
        declaration = (
            "[CONTEXT_TRUNCATION_RECOVERY]\n"
            "System detected prompt truncation and injected continuity context.\n"
            "Treat recovered items as prior conversation history, not new user claims."
        )
        lines = [declaration]
        if recovery_result and recovery_result.recovered_items:
            lines.append("Recovered MCC facts:")
            for item in recovery_result.recovered_items[:12]:
                lines.append(f"- [{item.source}] {item.content[:220]}")
        elif recovery_result is not None:
            lines.append("Continuity degraded: no recoverable items were returned for this truncation.")

        patch_msg = {"role": "system", "content": "\n".join(lines)}
        messages = list(context_pack.messages or [])
        insert_idx = 1 if messages and messages[0].get("role") == "system" else 0
        messages.insert(insert_idx, patch_msg)
        context_pack.messages = messages

    def _rebalance_prompt_budget(self, *, context_pack: Any, recovery_result: Optional[RecoveryResult]) -> None:
        messages = list(context_pack.messages or [])
        if not messages:
            return
        max_tokens = int(getattr(getattr(context_pack, "usage", None), "budget_tokens", 0) or 0)
        if max_tokens <= 0:
            return
        reserved_mcc = int((context_pack.metadata.get("integrity_budget") or {}).get("mcc_recovery_tokens", 1200))

        def msg_tokens(msg: Dict[str, str]) -> int:
            return _estimate_tokens(str(msg.get("content") or ""))

        # Protected: first system + recovery declaration block + latest user and last 3 user turns.
        protected: set[int] = set()
        if messages and messages[0].get("role") == "system":
            protected.add(0)
        for idx, msg in enumerate(messages):
            if "CONTEXT_TRUNCATION_RECOVERY" in str(msg.get("content") or ""):
                protected.add(idx)
                # MCC block itself may be clipped internally, but should keep reserved floor.
                if msg_tokens(msg) > reserved_mcc:
                    clipped = self._clip_to_tokens(str(msg.get("content") or ""), reserved_mcc)
                    msg["content"] = clipped
                break
        user_indices = [i for i, m in enumerate(messages) if m.get("role") == "user"]
        for idx in user_indices[-5:]:
            protected.add(idx)

        while sum(msg_tokens(m) for m in messages) > max_tokens:
            drop_idx = None
            for idx, msg in enumerate(messages):
                if idx in protected:
                    continue
                if msg.get("role") == "system":
                    drop_idx = idx
                    break
            if drop_idx is None:
                for idx, msg in enumerate(messages):
                    if idx not in protected and msg.get("role") in {"assistant", "user"}:
                        drop_idx = idx
                        break
            if drop_idx is None:
                break
            messages.pop(drop_idx)
            protected = {i if i < drop_idx else i - 1 for i in protected if i != drop_idx}

        context_pack.messages = messages

    def _clip_to_tokens(self, text: str, max_tokens: int) -> str:
        if _estimate_tokens(text) <= max_tokens:
            return text
        # Approximate 1 token ~= 1.3 chars
        max_chars = max(int(max_tokens / 1.3), 80)
        return text[:max_chars] + "\n[truncated_mcc_block_due_to_mcc_budget]"

    def _log_recovery_audit(self, *, session_id: str, recovery_result: RecoveryResult, reason_code: str) -> None:
        try:
            session = self.chat_service.get_session(session_id)
            log_audit_event(
                event_type=EVENT_CONTEXT_RECOVERY_APPLIED,
                task_id=session.task_id,
                level="info",
                metadata={
                    "session_id": session_id,
                    "reason_code": reason_code,
                    "recovered_count": len(recovery_result.recovered_items),
                    "sources_breakdown": recovery_result.coverage_summary.get("sources_breakdown", {}),
                    "dropped_due_to_budget_count": len(recovery_result.dropped_due_to_budget),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to write context recovery audit: {e}")

    def _log_degraded_audit(self, *, session_id: str, reason_code: str, recovery_result: RecoveryResult) -> None:
        try:
            session = self.chat_service.get_session(session_id)
            log_audit_event(
                event_type=EVENT_CONTEXT_INTEGRITY_DEGRADED,
                task_id=session.task_id,
                level="warn",
                metadata={
                    "session_id": session_id,
                    "reason_code": reason_code,
                    "recovered_count": len(recovery_result.recovered_items),
                    "sources_breakdown": recovery_result.coverage_summary.get("sources_breakdown", {}),
                    "dropped_due_to_budget_count": len(recovery_result.dropped_due_to_budget),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to write context degraded audit: {e}")

    def _log_crosstalk_drop(self, *, dropped_scope: List[Dict[str, Any]], session_id: str) -> None:
        try:
            session = self.chat_service.get_session(session_id)
            log_audit_event(
                event_type=EVENT_CONTEXT_RECOVERY_DROPPED_CROSSTALK,
                task_id=session.task_id,
                level="warn",
                metadata={
                    "session_id": session_id,
                    "reason_code": "CONTEXT_RECOVERY_DROPPED_CROSSTALK",
                    "dropped_due_to_scope_count": len(dropped_scope),
                    "dropped_due_to_scope": dropped_scope[:50],
                },
            )
        except Exception as e:
            logger.warning(f"Failed to write crosstalk drop audit: {e}")

    def _write_artifact(self, *, session_id: str, context_pack: Any, integrity: Dict[str, Any]) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = self.artifact_root / ts / "evidence"
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact = {
            "session_id": session_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "integrity": integrity,
            "prompt_blocks": self._prompt_blocks(context_pack.messages or []),
            "message_count": len(context_pack.messages or []),
        }
        target = out_dir / f"context_integrity_{session_id}.json"
        target.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def _prompt_blocks(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        for idx, msg in enumerate(messages):
            content = str(msg.get("content") or "")
            blocks.append(
                {
                    "index": idx,
                    "role": msg.get("role"),
                    "chars": len(content),
                    "tokens_est": _estimate_tokens(content),
                }
            )
        return blocks
