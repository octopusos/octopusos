from __future__ import annotations

AWS_CAPABILITY_MAP = {
    "managed_channel": "ssm",
    "compute_identity": "instance_profile",
    "monitor.ensure_agent": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation",
    ],
    "monitor.get_metrics": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
    ],
}
