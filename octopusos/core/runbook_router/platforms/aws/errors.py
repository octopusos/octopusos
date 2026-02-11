from __future__ import annotations


def normalize_aws_error(error_text: str) -> str:
    lowered = (error_text or "").lower()
    if "invalidinstanceid" in lowered:
        return "ManagedChannelNotReady"
    if "targetnotconnected" in lowered or "not connected" in lowered:
        return "ManagedChannelNotReady"
    if "nosuchentity" in lowered:
        return "InputNotFound"
    if "accessdenied" in lowered or "not authorized" in lowered:
        return "AccessDenied"
    return "UnknownError"
