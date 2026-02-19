"""NetworkOS capability registry (M2).

This registry defines which network capabilities exist and their default governance.
"""

from __future__ import annotations

from octopusos.networkos.capabilities.types import CapabilitySpec, GateDecision, RiskLevel


def get_registry() -> dict[str, CapabilitySpec]:
    # Hard constraints for M2:
    # - HIGH risk by default
    # - explain_confirm gate by default
    # - scope must be restricted to whitelisted prefixes
    allowed_scopes = ["/personal/", "/h5/"]
    return {
        "network.tunnel.enable": CapabilitySpec(
            capability="network.tunnel.enable",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.tunnel.disable": CapabilitySpec(
            capability="network.tunnel.disable",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.access.attach": CapabilitySpec(
            capability="network.access.attach",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.access.revoke": CapabilitySpec(
            capability="network.access.revoke",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.status.get": CapabilitySpec(
            capability="network.status.get",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.SILENT_ALLOW,
            allowed_scopes=allowed_scopes,
        ),
        # Cloudflare Access provisioning (no tunnel/DNS management here; governance-only + auditable).
        "network.cloudflare.access.provision": CapabilitySpec(
            capability="network.cloudflare.access.provision",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.access.revoke": CapabilitySpec(
            capability="network.cloudflare.access.revoke",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.access.status": CapabilitySpec(
            capability="network.cloudflare.access.status",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.SILENT_ALLOW,
            allowed_scopes=allowed_scopes,
        ),
        # cloudflared daemon management (execution only; no Cloudflare API writes here)
        "network.cloudflare.daemon.install": CapabilitySpec(
            capability="network.cloudflare.daemon.install",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.uninstall": CapabilitySpec(
            capability="network.cloudflare.daemon.uninstall",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.start": CapabilitySpec(
            capability="network.cloudflare.daemon.start",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.stop": CapabilitySpec(
            capability="network.cloudflare.daemon.stop",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.restart": CapabilitySpec(
            capability="network.cloudflare.daemon.restart",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.enable_autostart": CapabilitySpec(
            capability="network.cloudflare.daemon.enable_autostart",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.disable_autostart": CapabilitySpec(
            capability="network.cloudflare.daemon.disable_autostart",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.EXPLAIN_CONFIRM,
            allowed_scopes=allowed_scopes,
        ),
        "network.cloudflare.daemon.status": CapabilitySpec(
            capability="network.cloudflare.daemon.status",
            risk=RiskLevel.HIGH,
            default_gate=GateDecision.SILENT_ALLOW,
            allowed_scopes=allowed_scopes,
        ),
    }


def get_capability_spec(capability: str) -> CapabilitySpec | None:
    return get_registry().get(str(capability or "").strip())
