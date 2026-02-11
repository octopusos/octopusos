from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from octopusos.core.capabilities.external_facts.mapping_assistant import (
    MappingProposal,
    infer_mapping_proposal,
    normalize_mapping,
    validate_mapping_against_sample,
)

from .store import ConnectorStore


class ConnectorService:
    def __init__(self, store: Optional[ConnectorStore] = None) -> None:
        self.store = store or ConnectorStore()

    def infer_profile(
        self,
        *,
        connector_id: str,
        endpoint_id: str,
        endpoint_key: str,
        capability_id: str,
        item_id: str,
        sample_json: Dict[str, Any],
        request_sample_json: Optional[Dict[str, Any]] = None,
        api_doc_text: str = "",
        actor: str,
        endpoint_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        endpoint_meta = endpoint_meta or {}
        combined_sample = {
            "request": request_sample_json or {},
            "response": sample_json,
            "api_doc_text": api_doc_text or "",
        }
        sample = self.store.save_sample(
            connector_id=connector_id,
            endpoint_id=endpoint_id,
            endpoint_key=endpoint_key,
            sample_json=combined_sample,
            created_by=actor,
        )
        proposal, llm_model, prompt_hash = infer_mapping_proposal(
            capability_id=capability_id,
            item_id=item_id,
            sample_json=sample_json,
            request_json=request_sample_json or {},
            api_doc_text=api_doc_text,
        )
        validation_report = validate_mapping_against_sample(proposal, sample_json)
        proposal_row = self.store.save_proposal(
            connector_id=connector_id,
            endpoint_id=endpoint_id,
            endpoint_key=endpoint_key,
            proposal_json=proposal.model_dump(),
            confidence=float(proposal.confidence),
            llm_model=llm_model,
            prompt_hash=prompt_hash,
            sample_id=sample["id"],
        )
        can_apply = bool(validation_report.get("ok")) and float(proposal.confidence) >= 0.6
        return {
            "sample_id": sample["id"],
            "proposal_id": proposal_row["id"],
            "proposal": proposal.model_dump(),
            "confidence": float(proposal.confidence),
            "validation_report": validation_report,
            "can_apply": can_apply,
            "endpoint": {
                "url": str(endpoint_meta.get("url") or ""),
                "method": str(endpoint_meta.get("method") or "GET").upper(),
            },
        }

    def apply_profile(
        self,
        *,
        connector_id: str,
        endpoint_id: str,
        endpoint_key: str,
        endpoint_url: str,
        endpoint_method: str,
        payload: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        proposal_id = str(payload.get("proposal_id") or "").strip()
        profile_json = payload.get("mapping_json") if isinstance(payload.get("mapping_json"), dict) else None
        sample_id = str(payload.get("sample_id") or "").strip()

        sample_json: Dict[str, Any] = {}
        if sample_id:
            bundle = self.store.list_profiles(connector_id, endpoint_key, limit=200)
            for row in bundle.get("samples") or []:
                if str(row.get("id")) == sample_id and isinstance(row.get("sample"), dict):
                    row_sample = row["sample"]
                    if isinstance(row_sample.get("response"), dict):
                        sample_json = row_sample["response"]
                    else:
                        sample_json = row_sample
                    break
        if not sample_json:
            latest = self.store.latest_sample(connector_id, endpoint_key)
            if latest and isinstance(latest.get("sample"), dict):
                latest_sample = latest["sample"]
                if isinstance(latest_sample.get("response"), dict):
                    sample_json = latest_sample["response"]
                else:
                    sample_json = latest_sample
        if not sample_json:
            raise ValueError("NO_SAMPLE_AVAILABLE_FOR_VALIDATION")

        proposal_obj: Optional[MappingProposal] = None
        if proposal_id:
            proposal_row = self.store.get_proposal(proposal_id)
            if not proposal_row:
                raise ValueError("proposal not found")
            proposal_obj = MappingProposal.model_validate(proposal_row.get("proposal") or {})
        elif profile_json is not None:
            response = profile_json.get("response") if isinstance(profile_json.get("response"), dict) else {}
            proposal_obj = MappingProposal.model_validate(
                {
                    "response_kind": response.get("kind", "point"),
                    "time_path": response.get("time_path", ""),
                    "value_path": response.get("value_path", ""),
                    "points_path": response.get("points_path"),
                    "summary_path": response.get("summary_path"),
                    "method": profile_json.get("method", endpoint_method or "GET"),
                    "reasoning": "manual_profile",
                    "confidence": 0.7,
                }
            )
        else:
            raise ValueError("proposal_id or mapping_json is required")

        if profile_json is None:
            profile_json = normalize_mapping(
                endpoint_url=endpoint_url,
                method=endpoint_method or "GET",
                proposal=proposal_obj,
                headers=None,
                query=None,
            )

        validation_report = validate_mapping_against_sample(proposal_obj, sample_json)
        status = "active" if bool(validation_report.get("ok")) and float(proposal_obj.confidence) >= 0.6 else "draft"
        version = self.store.create_profile_version(
            connector_id=connector_id,
            endpoint_id=endpoint_id,
            endpoint_key=endpoint_key,
            profile_json=profile_json,
            validation_report=validation_report,
            status=status,
            approved_by=actor,
        )
        usage = self.generate_usage_card(
            connector_id=connector_id,
            endpoint_id=endpoint_id,
            endpoint_key=endpoint_key,
            profile_version_id=str(version.get("id") or ""),
            profile_json=profile_json,
        )
        return {"version": version, "status": status, "usage_card": usage}

    def generate_usage_card(
        self,
        *,
        connector_id: str,
        endpoint_id: str,
        endpoint_key: str,
        profile_version_id: str,
        profile_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        connector = self.store.get_connector(connector_id, mask_secret=True) or {}
        endpoint = self.store.get_endpoint(connector_id, endpoint_id) or {}
        method = str(profile_json.get("method") or endpoint.get("method") or "GET")
        url = str(profile_json.get("url") or endpoint.get("path") or "")
        response = profile_json.get("response") if isinstance(profile_json.get("response"), dict) else {}
        content = (
            f"# UsageCard: {connector.get('name','Connector')} / {endpoint.get('name','Endpoint')}\n\n"
            f"- Endpoint Key: `{endpoint_key}`\n"
            f"- Method: `{method}`\n"
            f"- URL: `{url}`\n"
            f"- Response Kind: `{response.get('kind','point')}`\n"
            f"- Time Path: `{response.get('time_path','')}`\n"
            f"- Value Path: `{response.get('value_path','')}`\n"
            f"- Points Path: `{response.get('points_path','')}`\n"
            f"- Profile Version: `{profile_version_id}`\n"
        )
        card = self.store.save_usage_card(
            connector_id=connector_id,
            endpoint_id=endpoint_id,
            endpoint_key=endpoint_key,
            profile_version_id=profile_version_id,
            content_md=content,
        )
        # Lightweight RAG feed export: versioned markdown artifacts for KB ingestion.
        try:
            root = Path("outputs") / "connectoros" / "usage_cards"
            root.mkdir(parents=True, exist_ok=True)
            filename = f"{connector_id}__{endpoint_id}__{profile_version_id or 'latest'}.md"
            (root / filename).write_text(content, encoding="utf-8")
        except Exception:
            pass
        return card
