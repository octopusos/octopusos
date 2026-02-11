from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from octopusos.core.mcp.client import MCPClient
from octopusos.core.mcp.config import MCPServerConfig
from octopusos.core.runbook_router.platforms.base import PlatformActions


class AwsPlatformActions(PlatformActions):
    """Adapter contract for AWS MCP-backed actions.

    Note: full action implementations remain in aws_mcp_dispatch for now and are being migrated incrementally.
    """

    def __init__(self, server_config: MCPServerConfig, region: str) -> None:
        self._server = server_config.model_copy(deep=True)
        env = dict(self._server.env or {})
        env["AWS_REGION"] = region
        self._server.env = env

    async def _call_aws_body_or_error(self, cli_command: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        client = MCPClient(self._server)
        await client.connect()
        try:
            res = await client.call_tool("call_aws", {"cli_command": cli_command, "max_results": 50})
        finally:
            await client.disconnect()
        # Local parsing to keep adapter self-contained.
        content = res.get("content")
        if isinstance(content, list):
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                text = str(chunk.get("text") or "").strip()
                if not text:
                    continue
                if "Error calling tool 'call_aws':" in text:
                    return None, text.split("Error calling tool 'call_aws':", 1)[-1].strip()
                try:
                    import json
                    outer = json.loads(text)
                except Exception:
                    continue
                if not isinstance(outer, dict):
                    continue
                response = outer.get("response") if isinstance(outer.get("response"), dict) else {}
                if response.get("error"):
                    return None, str(response.get("error"))
                json_str = response.get("json")
                if isinstance(json_str, str) and json_str.strip():
                    try:
                        body = json.loads(json_str)
                    except Exception:
                        body = None
                    if isinstance(body, dict):
                        return body, None
        return None, "Unable to parse call_aws response."

    async def recheck_instance_profile_binding(self, instance_id: str) -> Dict[str, Any]:
        body, err = await self._call_aws_body_or_error(f"aws ec2 describe-instances --instance-ids {instance_id}")
        if err:
            return {"ok": False, "error": err}
        reservations = (body or {}).get("Reservations")
        if not isinstance(reservations, list) or not reservations:
            return {"ok": False, "error": "Instance not found."}
        instance = {}
        for r in reservations:
            if isinstance(r, dict):
                instances = r.get("Instances")
                if isinstance(instances, list) and instances:
                    instance = instances[0] if isinstance(instances[0], dict) else {}
                    break
        iam_profile = instance.get("IamInstanceProfile") if isinstance(instance, dict) else {}
        profile_arn = str((iam_profile or {}).get("Arn") or "")
        profile_name = profile_arn.split("/")[-1].strip() if profile_arn else ""
        if not profile_name:
            return {"ok": False, "error": "Instance profile still missing.", "profile_name": ""}
        return {"ok": True, "profile_name": profile_name}

    async def permission_probe_for_resume(self, instance_id: str, resume_action: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        action_type = str(resume_action.get("type") or "")
        if action_type != "bind_instance_profile":
            return {"ok": True}, None
        choice = resume_action.get("choice") if isinstance(resume_action.get("choice"), dict) else {}
        kind = str(choice.get("kind") or "")
        if kind == "create_minimal":
            cmd = f"aws iam get-role --role-name OctopusOS-SSM-CWAgent-{instance_id[-6:]}"
            return await self._call_aws_body_or_error(cmd)
        if kind == "role":
            role = str(choice.get("name") or "").strip()
            if role:
                return await self._call_aws_body_or_error(f"aws iam get-role --role-name {role}")
        if kind == "profile":
            profile = str(choice.get("name") or "").strip()
            if profile:
                return await self._call_aws_body_or_error(f"aws iam get-instance-profile --instance-profile-name {profile}")
        return {"ok": True}, None

    @staticmethod
    def _unsupported(op: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": f"unsupported_operation:{op}",
            "details": "This AWS adapter method is not migrated yet; dispatch should use legacy MCP flow for this operation.",
        }

    def whoami(self) -> Dict[str, Any]:
        return self._unsupported("whoami")

    def check_permissions(self, actions):
        return self._unsupported("check_permissions")

    def resolve_resource(self, kind, resource_id, region):
        return self._unsupported("resolve_resource")

    def list_metrics(self, query):
        return self._unsupported("list_metrics")

    def get_metric_data(self, req):
        return self._unsupported("get_metric_data")

    def managed_node_status(self, resource):
        return self._unsupported("managed_node_status")

    def run_managed_command(self, resource, command):
        return self._unsupported("run_managed_command")

    def get_compute_identity_binding(self, resource):
        return self._unsupported("get_compute_identity_binding")

    def bind_compute_identity(self, resource, binding):
        return self._unsupported("bind_compute_identity")

    def create_minimal_compute_identity(self, spec):
        return self._unsupported("create_minimal_compute_identity")

    def list_inventory(self, scope):
        return self._unsupported("list_inventory")

    def get_billing_summary(self, window):
        return self._unsupported("get_billing_summary")

    def get_org_structure(self):
        return self._unsupported("get_org_structure")
