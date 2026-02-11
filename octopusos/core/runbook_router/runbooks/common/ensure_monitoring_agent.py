from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

RUNBOOK_ID = "common.ensure_monitoring_agent"


async def execute_bind_install_probe_flow(
    *,
    bind_fn: Callable[[], Awaitable[Dict[str, Any]]],
    install_fn: Callable[[], Awaitable[Dict[str, Any]]],
    probe_fn: Callable[[], Awaitable[Dict[str, Any]]],
) -> Dict[str, Any]:
    bind_res = await bind_fn()
    if not bind_res.get("ok"):
        return {
            "ok": False,
            "stage": bind_res.get("stage"),
            "error": bind_res.get("error"),
            "bind": bind_res,
        }

    install_res = await install_fn()
    if not install_res.get("ok"):
        return {
            "ok": False,
            "stage": install_res.get("stage"),
            "error": install_res.get("error"),
            "bind": bind_res,
        }

    probe_payload = await probe_fn()
    return {"ok": True, "probe": probe_payload, "bind": bind_res}


async def execute_remediate_install_probe_flow(
    *,
    remediate_fn: Callable[[], Awaitable[Dict[str, Any]]],
    install_fn: Callable[[], Awaitable[Dict[str, Any]]],
    probe_fn: Callable[[], Awaitable[Dict[str, Any]]],
) -> Dict[str, Any]:
    remediation = await remediate_fn()
    if not remediation.get("ok"):
        return {
            "ok": False,
            "stage": remediation.get("stage"),
            "error": remediation.get("error"),
            "remediation": remediation,
        }

    install_res = await install_fn()
    if not install_res.get("ok"):
        return {
            "ok": False,
            "stage": install_res.get("stage"),
            "error": install_res.get("error"),
            "remediation": remediation,
        }

    probe_payload = await probe_fn()
    return {"ok": True, "probe": probe_payload, "remediation": remediation}


async def execute_install_probe_flow(
    *,
    install_fn: Callable[[], Awaitable[Dict[str, Any]]],
    probe_fn: Callable[[], Awaitable[Dict[str, Any]]],
) -> Dict[str, Any]:
    install_res = await install_fn()
    if not install_res.get("ok"):
        return {
            "ok": False,
            "stage": install_res.get("stage"),
            "error": install_res.get("error"),
        }

    probe_payload = await probe_fn()
    return {"ok": True, "probe": probe_payload}
