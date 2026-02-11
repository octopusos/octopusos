from __future__ import annotations

from typing import Any, Dict


class GcpPlatformActions:
    """GCP adapter placeholder with stable unsupported responses."""

    @staticmethod
    def _unsupported(op: str) -> Dict[str, Any]:
        return {
            "ok": False,
            "error": f"unsupported_operation:{op}",
            "details": "GCP adapter is scaffolded but not implemented yet.",
        }

    def whoami(self) -> Dict[str, Any]:
        return self._unsupported("whoami")

    def check_permissions(self, actions) -> Dict[str, Any]:
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
