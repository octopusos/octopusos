"""Minimal AWS MCP dispatch for chat queries."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from octopusos.core.chat.tool_dispatch.guardrails import is_high_risk_aws_intent
from octopusos.core.chat.ops_report import (
    build_ops_report_from_monitoring,
    render_ops_report_markdown,
)
from octopusos.core.mcp.client import MCPClient
from octopusos.core.mcp.config import MCPConfigManager, MCPServerConfig
from octopusos.core.runbook_router import RunbookRouter, parse_intent
from octopusos.core.runbook_router.platforms.aws.adapter import AwsPlatformActions
from octopusos.core.runbook_router.runbooks.common.ensure_monitoring_agent import (
    execute_bind_install_probe_flow,
    execute_install_probe_flow,
    execute_remediate_install_probe_flow,
)

AWS_KEYWORDS = (
    "aws",
    "s3",
    "ec2",
    "iam",
    "sts",
    "lambda",
    "cloudwatch",
    "vpc",
    "instance",
    "instances",
    "实例",
    "成本",
    "费用",
    "账单",
    "cost",
    "billing",
    "usage",
    "用量",
)
REGION_CODE_RE = re.compile(r"\b[a-z]{2}-[a-z]+-\d\b", re.IGNORECASE)
SPACED_REGION_RE = re.compile(r"\b([a-z]{2})[\s_]+([a-z]+(?:[\s_]+[a-z]+)*)[\s_]+(\d)\b", re.IGNORECASE)
AWS_REGION_PREFIXES = {"us", "eu", "ap", "sa", "ca", "me", "af", "cn", "il"}

# Common NL aliases -> AWS region code.
# Keep this table focused on practical user phrasing (city / market / locale names),
# while still accepting strict region code expressions.
REGION_ALIASES: Dict[str, str] = {
    # APAC
    "sydney": "ap-southeast-2",
    "australia sydney": "ap-southeast-2",
    "australia": "ap-southeast-2",
    "悉尼": "ap-southeast-2",
    "澳大利亚": "ap-southeast-2",
    "新南威尔士": "ap-southeast-2",
    "singapore": "ap-southeast-1",
    "新加坡": "ap-southeast-1",
    "tokyo": "ap-northeast-1",
    "东京": "ap-northeast-1",
    "japan": "ap-northeast-1",
    "日本": "ap-northeast-1",
    "seoul": "ap-northeast-2",
    "首尔": "ap-northeast-2",
    "korea": "ap-northeast-2",
    "韩国": "ap-northeast-2",
    "mumbai": "ap-south-1",
    "india": "ap-south-1",
    "印度": "ap-south-1",
    "hong kong": "ap-east-1",
    "hongkong": "ap-east-1",
    "香港": "ap-east-1",
    "jakarta": "ap-southeast-3",
    "雅加达": "ap-southeast-3",
    # North America
    "virginia": "us-east-1",
    "n. virginia": "us-east-1",
    "north virginia": "us-east-1",
    "us east 1": "us-east-1",
    "俄亥俄": "us-east-2",
    "ohio": "us-east-2",
    "us east 2": "us-east-2",
    "oregon": "us-west-2",
    "us west 2": "us-west-2",
    "northern california": "us-west-1",
    "california": "us-west-1",
    "us west 1": "us-west-1",
    # Europe
    "ireland": "eu-west-1",
    "爱尔兰": "eu-west-1",
    "london": "eu-west-2",
    "伦敦": "eu-west-2",
    "frankfurt": "eu-central-1",
    "法兰克福": "eu-central-1",
    "paris": "eu-west-3",
    "巴黎": "eu-west-3",
    "stockholm": "eu-north-1",
    "斯德哥尔摩": "eu-north-1",
    "milan": "eu-south-1",
    "米兰": "eu-south-1",
    "spain": "eu-south-2",
    "马德里": "eu-south-2",
    "madrid": "eu-south-2",
    # Middle East / Africa / South America / Canada
    "bahrain": "me-south-1",
    "巴林": "me-south-1",
    "uae": "me-central-1",
    "dubai": "me-central-1",
    "阿联酋": "me-central-1",
    "cape town": "af-south-1",
    "capetown": "af-south-1",
    "开普敦": "af-south-1",
    "sao paulo": "sa-east-1",
    "saopaulo": "sa-east-1",
    "圣保罗": "sa-east-1",
    "canada central": "ca-central-1",
    "montreal": "ca-central-1",
    "蒙特利尔": "ca-central-1",
}

EXPLAIN_OR_RECOMMEND_KEYWORDS = (
    "explain",
    "why",
    "breakdown",
    "recommend",
    "suggest",
    "optimization",
    "optimize",
    "解释",
    "原因",
    "构成",
    "建议",
    "优化",
)

INTENT_TOOL_CANDIDATES: Dict[str, List[str]] = {
    "identity": [
        "aws_sts_get_caller_identity",
        "get_caller_identity",
        "sts_get_caller_identity",
    ],
    "s3_buckets": [
        "aws_s3_list_buckets",
        "s3_list_buckets",
        "list_buckets",
    ],
    "ec2_instances": [
        "aws_ec2_describe_instances",
        "ec2_describe_instances",
        "describe_instances",
        "ec2_list_instances",
    ],
    "ec2_status_health": [
        "aws_ec2_describe_instance_status",
        "ec2_describe_instance_status",
        "describe_instance_status",
        "aws_ec2_describe_instances",
        "ec2_describe_instances",
        "describe_instances",
    ],
    "ec2_load": [
        "aws_cloudwatch_get_metric_data",
        "cloudwatch_get_metric_data",
        "get_metric_data",
        "aws_cloudwatch_get_metric_statistics",
        "cloudwatch_get_metric_statistics",
    ],
    "cost_usage": [
        "aws_ce_get_cost_and_usage",
        "ce_get_cost_and_usage",
        "cost_explorer_get_cost_and_usage",
    ],
    "cost_explain": [
        "aws_ce_get_cost_breakdown",
        "ce_get_cost_breakdown",
        "aws_ce_get_cost_and_usage",
        "ce_get_cost_and_usage",
    ],
    "usage": [
        "aws_ce_get_cost_and_usage",
        "ce_get_cost_and_usage",
        "aws_servicequotas_list_service_quotas",
        "servicequotas_list_service_quotas",
    ],
    "service_enablement": [
        "aws_servicequotas_list_services",
        "servicequotas_list_services",
        "aws_account_list_regions",
        "account_list_regions",
    ],
}

GENERIC_QUERY_TOOLS = ("query", "ask", "natural_language_query", "prompt", "chat", "aws_query")
RUNBOOK_ROUTER = RunbookRouter()


def _is_english_query(text: str) -> bool:
    source = text or ""
    latin = len(re.findall(r"[A-Za-z]", source))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", source))
    if cjk > 0:
        return False
    return latin >= 6


def _t(is_en: bool, zh: str, en: str) -> str:
    return en if is_en else zh


MONITORING_KEYWORDS = (
    "monitor",
    "metrics",
    "metric",
    "cpu",
    "memory",
    "disk",
    "health",
    "监控",
    "指标",
    "内存",
    "磁盘",
    "负载",
    "utilization",
)


def _is_monitoring_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(k in lowered for k in MONITORING_KEYWORDS)


def _extract_instance_id(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"\bi-[0-9a-f]{8,17}\b", text, re.IGNORECASE)
    return m.group(0).lower() if m else None


def _extract_window_minutes(text: str) -> int:
    source = (text or "").lower()
    # Chinese
    m = re.search(r"(\d+)\s*分(?:钟)?", source)
    if m:
        return max(5, min(24 * 60, int(m.group(1))))
    m = re.search(r"(\d+)\s*小(?:时)?", source)
    if m:
        return max(5, min(24 * 60, int(m.group(1)) * 60))
    # English
    m = re.search(r"(\d+)\s*(?:min|mins|minute|minutes)\b", source)
    if m:
        return max(5, min(24 * 60, int(m.group(1))))
    m = re.search(r"(\d+)\s*(?:h|hr|hrs|hour|hours)\b", source)
    if m:
        return max(5, min(24 * 60, int(m.group(1)) * 60))
    return 30


def _extract_metric_dimensions(metric: Dict[str, Any]) -> List[Tuple[str, str]]:
    dims = metric.get("Dimensions")
    out: List[Tuple[str, str]] = []
    if not isinstance(dims, list):
        return out
    for d in dims:
        if not isinstance(d, dict):
            continue
        n = str(d.get("Name") or "").strip()
        v = str(d.get("Value") or "").strip()
        if n and v:
            out.append((n, v))
    return out


def _dimensions_cli_arg(dimensions: List[Tuple[str, str]]) -> str:
    if not dimensions:
        return ""
    return " ".join([f"Name={n},Value={v}" for n, v in dimensions])


def _build_server_config_with_region(server_config: MCPServerConfig, region: str) -> MCPServerConfig:
    request_config = server_config.model_copy(deep=True)
    request_env = dict(request_config.env or {})
    request_env["AWS_REGION"] = region
    request_config.env = request_env
    return request_config


def _is_install_confirmation(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        token in lowered
        for token in (
            "安装",
            "启用",
            "继续",
            "确认",
            "yes",
            "ok",
            "proceed",
            "install",
            "enable",
            "go ahead",
        )
    )


def _is_install_reject(text: str) -> bool:
    lowered = (text or "").lower()
    return any(token in lowered for token in ("不", "取消", "不用", "no", "cancel", "stop"))


def _parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _get_valid_pending_action(session_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    ctx = session_context or {}
    pending = ctx.get("pending_action")
    if not isinstance(pending, dict):
        return None
    expires_at = _parse_iso_datetime(str(pending.get("expires_at") or ""))
    if expires_at and datetime.now(timezone.utc) > expires_at:
        return None
    return pending


def _resolve_language_is_en(user_text: str, pending_action: Optional[Dict[str, Any]]) -> bool:
    if isinstance(pending_action, dict):
        lang = str(pending_action.get("lang") or "").lower().strip()
        if lang == "zh":
            return False
        if lang == "en":
            return True
    return _is_english_query(user_text)


def _is_aws_query(text: str) -> bool:
    lowered = (text or "").lower()
    return any(keyword in lowered for keyword in AWS_KEYWORDS)


def _find_enabled_aws_server(manager: MCPConfigManager) -> Optional[MCPServerConfig]:
    for server in manager.get_enabled_servers():
        if (server.env or {}).get("OCTOPUSOS_MCP_PACKAGE_ID") == "aws.mcp":
            return server
    return None


def _extract_region(user_text: str) -> Optional[str]:
    text = user_text or ""
    match = REGION_CODE_RE.search(text)
    if match:
        return match.group(0).lower()

    for spaced_match in SPACED_REGION_RE.finditer(text):
        prefix = spaced_match.group(1).lower()
        if prefix not in AWS_REGION_PREFIXES:
            continue
        middle = spaced_match.group(2).lower().replace("_", " ").strip().replace(" ", "-")
        suffix = spaced_match.group(3)
        return f"{prefix}-{middle}-{suffix}"

    lowered = text.lower()
    tokenized = re.findall(r"[a-z0-9]+", lowered)
    for idx, token in enumerate(tokenized):
        if token not in AWS_REGION_PREFIXES:
            continue
        # Accept forms like: "ap southeast 2", "us east 1", "eu west 3"
        for end in range(idx + 2, min(idx + 5, len(tokenized))):
            suffix = tokenized[end]
            if not suffix.isdigit():
                continue
            middle_tokens = tokenized[idx + 1:end]
            if not middle_tokens:
                continue
            middle = "-".join(middle_tokens)
            return f"{token}-{middle}-{suffix}"
    normalized = re.sub(r"[\(\)\[\]{}，,。\.]+", " ", lowered)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized_compact = normalized.replace(" ", "")
    lowered_compact = lowered.replace(" ", "")

    # Longest alias first to avoid accidental short-match overrides.
    for alias in sorted(REGION_ALIASES.keys(), key=len, reverse=True):
        region = REGION_ALIASES[alias]
        alias_norm = alias.lower().strip()
        alias_compact = alias_norm.replace(" ", "")
        if alias_norm in normalized or alias_compact in normalized_compact or alias_compact in lowered_compact:
            return region
    return None


def _build_request_server_config(
    server_config: MCPServerConfig,
    user_text: str,
) -> Tuple[MCPServerConfig, Optional[str]]:
    inferred_region = _extract_region(user_text)
    if not inferred_region:
        return server_config, None

    request_config = server_config.model_copy(deep=True)
    request_env = dict(request_config.env or {})
    request_env["AWS_REGION"] = inferred_region
    request_config.env = request_env
    return request_config, inferred_region


def _pick_tool_and_args(user_text: str, tools: List[Dict[str, Any]]) -> Tuple[Optional[str], Dict[str, Any]]:
    lowered = user_text.lower()
    names = {str(tool.get("name")): tool for tool in tools if tool.get("name")}

    def _first(candidates: List[str]) -> Optional[str]:
        for candidate in candidates:
            if candidate in names:
                return candidate
        return None

    def _query_tool() -> Optional[str]:
        return _first([*GENERIC_QUERY_TOOLS, "suggest_aws_commands"])

    def _intent_or_query(candidates: List[str], default_args: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        picked = _first(candidates)
        if picked:
            return picked, (default_args or {})
        query_tool = _query_tool()
        if query_tool:
            return query_tool, {"query": user_text}
        return None, {}

    if any(token in lowered for token in EXPLAIN_OR_RECOMMEND_KEYWORDS):
        query_tool = _query_tool()
        if query_tool:
            return query_tool, {"query": user_text}

    if any(token in lowered for token in ("identity", "caller", "account", "who am i", "当前账号", "账号信息")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["identity"])
    if any(token in lowered for token in ("bucket", "buckets", "s3", "存储桶")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["s3_buckets"])
    if any(token in lowered for token in ("monthly cost", "month cost", "月成本", "每月成本", "成本", "费用", "账单", "billing")):
        if any(token in lowered for token in ("explain", "why", "breakdown", "解释", "构成", "原因")):
            return _intent_or_query(INTENT_TOOL_CANDIDATES["cost_explain"])
        else:
            return _intent_or_query(INTENT_TOOL_CANDIDATES["cost_usage"])
    if any(token in lowered for token in ("usage", "utilization", "用量", "利用率", "quota", "配额")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["usage"])
    if any(token in lowered for token in ("service enabled", "services enabled", "service status", "服务开通", "开通情况")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["service_enablement"])
    if any(token in lowered for token in ("health", "status", "健康", "状态检查", "status check")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["ec2_status_health"])
    if any(token in lowered for token in ("load", "cpu", "network", "iops", "负载", "流量", "吞吐")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["ec2_load"])
    if any(token in lowered for token in ("spec", "type", "instance type", "规格", "机型")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["ec2_instances"])
    if any(token in lowered for token in ("ec2", "instance", "instances", "实例")):
        return _intent_or_query(INTENT_TOOL_CANDIDATES["ec2_instances"])

    query_tool = _query_tool()
    if query_tool:
        return query_tool, {"query": user_text}

    return None, {}


def _extract_cli_command_from_suggest_result(result: Dict[str, Any]) -> Optional[str]:
    """Extract first usable `aws ...` command from suggest_aws_commands response."""
    content = result.get("content")
    if not isinstance(content, list):
        return None

    for chunk in content:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        # 1) JSON payload path: {"suggestions":[{"command":"aws ..."}]}
        try:
            payload = __import__("json").loads(text)
            suggestions = payload.get("suggestions") if isinstance(payload, dict) else None
            if isinstance(suggestions, list):
                for item in suggestions:
                    if not isinstance(item, dict):
                        continue
                    cmd = str(item.get("command") or "").strip()
                    if cmd.startswith("aws "):
                        return cmd
        except Exception:
            pass

        # 2) Fallback regex extraction from plain text response
        match = re.search(r"\baws\s+[^\n\r`\"]+", text, re.IGNORECASE)
        if match:
            cmd = match.group(0).strip()
            if cmd.startswith("aws "):
                return cmd
    return None


def _extract_suggested_commands(result: Dict[str, Any]) -> List[str]:
    commands: List[str] = []
    content = result.get("content")
    if not isinstance(content, list):
        return commands
    for chunk in content:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        try:
            payload = __import__("json").loads(text)
            suggestions = payload.get("suggestions") if isinstance(payload, dict) else None
            if isinstance(suggestions, list):
                for item in suggestions:
                    if not isinstance(item, dict):
                        continue
                    cmd = str(item.get("command") or "").strip()
                    if cmd.startswith("aws "):
                        commands.append(cmd)
                if commands:
                    return commands
        except Exception:
            pass
        for m in re.finditer(r"\baws\s+[^\n\r`\"]+", text, re.IGNORECASE):
            cmd = m.group(0).strip()
            if cmd.startswith("aws "):
                commands.append(cmd)
    # de-duplicate preserving order
    dedup: List[str] = []
    seen = set()
    for c in commands:
        if c in seen:
            continue
        seen.add(c)
        dedup.append(c)
    return dedup


def _select_best_cli_command(commands: List[str], user_text: str) -> Optional[str]:
    if not commands:
        return None
    lowered = user_text.lower()

    blocked_fragments = (
        "get-spot-placement-scores",
        "run-instances",
        "terminate-instances",
        "delete-",
        "put-",
        "update-",
        "create-",
    )

    safe = [c for c in commands if not any(frag in c for frag in blocked_fragments)]
    pool = safe or commands

    preferred_patterns: List[str] = []
    if any(k in lowered for k in ("ec2", "instance", "instances", "实例", "规格", "health", "状态")):
        preferred_patterns = [
            "aws ec2 describe-instances",
            "aws ec2 describe-instance-status",
        ]
    elif any(k in lowered for k in ("s3", "bucket", "buckets", "存储桶")):
        preferred_patterns = ["aws s3api list-buckets", "aws s3 ls"]
    elif any(k in lowered for k in ("cost", "billing", "费用", "成本", "账单")):
        preferred_patterns = ["aws ce get-cost-and-usage"]
    elif any(k in lowered for k in ("identity", "caller", "account", "账号")):
        preferred_patterns = ["aws sts get-caller-identity"]

    for pattern in preferred_patterns:
        for cmd in pool:
            if cmd.startswith(pattern):
                return cmd

    for cmd in pool:
        if " describe-" in cmd or " list-" in cmd or cmd.startswith("aws s3 ls"):
            return cmd

    return pool[0]


def _build_direct_cli_commands(user_text: str) -> List[str]:
    """Construct safe read-only AWS CLI commands for common intents."""
    lowered = user_text.lower()
    commands: List[str] = []

    if any(k in lowered for k in ("identity", "caller", "account", "当前账号", "账号")):
        commands.append("aws sts get-caller-identity")
        return commands
    if any(k in lowered for k in ("bucket", "buckets", "s3", "存储桶")):
        commands.append("aws s3api list-buckets")
        return commands

    wants_ec2 = any(k in lowered for k in ("ec2", "instance", "instances", "实例", "规格", "机型"))
    wants_health = any(k in lowered for k in ("health", "status", "健康", "状态检查", "status check"))
    if wants_ec2:
        commands.append("aws ec2 describe-instances")
    if wants_health:
        commands.append("aws ec2 describe-instance-status --include-all-instances")
    if commands:
        return commands

    if any(k in lowered for k in ("service enabled", "services enabled", "service status", "服务开通", "开通情况")):
        commands.append("aws service-quotas list-services")
        return commands
    if any(k in lowered for k in ("monthly cost", "month cost", "月成本", "每月成本", "成本", "费用", "账单", "billing", "usage", "用量")):
        now = datetime.now(timezone.utc).date()
        month_start = now.replace(day=1).isoformat()
        tomorrow = (now + timedelta(days=1)).isoformat()
        metric = "UsageQuantity" if any(k in lowered for k in ("usage", "用量")) else "UnblendedCost"
        commands.append(
            "aws ce get-cost-and-usage "
            f"--time-period Start={month_start},End={tomorrow} "
            "--granularity MONTHLY "
            f"--metrics {metric} "
            "--group-by Type=DIMENSION,Key=SERVICE"
        )
        return commands
    return commands


def _run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()


def _is_unsupported_operation_error(reason: str) -> bool:
    return "unsupported_operation:" in (reason or "").lower()


def _pending_status_probe_message(pending_action: Dict[str, Any], is_en: bool) -> str:
    ptype = str((pending_action or {}).get("type") or "")
    if ptype == "install_cwagent":
        return _t(
            is_en,
            "当前待处理步骤是安装并启用 CloudWatch Agent。回复“安装并启用 CloudWatch Agent”继续，或回复“取消”终止。",
            "Current pending step is CloudWatch Agent installation. Reply 'install and enable CloudWatch Agent' to continue, or 'cancel' to stop.",
        )
    if ptype == "remediate_ssm_prereq":
        return _t(
            is_en,
            "当前待处理步骤是修复 SSM 前置条件。回复“继续修复”推进，或回复“取消”终止。",
            "Current pending step is SSM prerequisite remediation. Reply 'continue remediation' to proceed, or 'cancel' to stop.",
        )
    if ptype == "await_instance_profile_choice":
        return _t(
            is_en,
            "当前卡在 IAM Role/Profile 选择。请回复 Role 名称、Profile 名称，或“创建最小权限并绑定”。",
            "Currently blocked on IAM role/profile choice. Reply with a role name, profile name, or 'create minimal and bind'.",
        )
    if ptype == "bind_instance_profile":
        return _t(
            is_en,
            "当前待处理步骤是绑定实例 IAM 身份并继续安装 Agent。回复“继续”执行，或回复“取消”。",
            "Current pending step is binding instance IAM identity then continuing agent install. Reply 'continue' to execute, or 'cancel'.",
        )
    if ptype == "await_iam_permission_grant":
        return _t(
            is_en,
            "当前待处理步骤是等待 IAM 权限补齐。权限就绪后回复“继续”，我会自动续跑。",
            "Current pending step is waiting for IAM permission grant. Reply 'continue' once permissions are ready and I will auto-resume.",
        )
    if ptype == "await_cwagent_metrics":
        return _t(
            is_en,
            "当前待处理步骤是等待 CloudWatch Agent 首报。回复“继续”触发下一次拉取。",
            "Current pending step is waiting for CloudWatch Agent first metrics. Reply 'continue' to poll again.",
        )
    return _t(
        is_en,
        f"当前仍有待处理步骤：`{ptype}`。请回复“继续”推进，或回复“取消”终止。",
        f"There is still a pending step: `{ptype}`. Reply 'continue' to proceed, or 'cancel' to stop.",
    )


def _build_unsupported_operation_response(
    *,
    reason: str,
    is_en: bool,
    pending_action: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    op = "unknown"
    m = re.search(r"unsupported_operation:([a-zA-Z0-9_]+)", reason or "", re.IGNORECASE)
    if m:
        op = m.group(1)
    suggestions = [
        _t(
            is_en,
            "这是当前平台适配器的能力边界，不是你的输入错误。",
            "This is a current platform adapter capability boundary, not an input error.",
        ),
        _t(
            is_en,
            "可先执行只读查询（实例/监控/成本/资产清单），写操作待该能力实现后再自动续跑。",
            "You can proceed with read-only queries first (instances/monitoring/cost/inventory), and resume write operations after this capability is implemented.",
        ),
    ]
    if isinstance(pending_action, dict) and pending_action.get("type"):
        suggestions.append(_pending_status_probe_message(pending_action, is_en))
    return {
        "handled": True,
        "blocked": False,
        "pending_action_set": pending_action if isinstance(pending_action, dict) else None,
        "message": _format_error_with_suggestions(
            title=_t(is_en, "当前能力暂未实现", "Capability not implemented yet"),
            reason=f"unsupported_operation:{op}",
            suggestions=suggestions,
            is_en=is_en,
        ),
    }


async def _call_server_async(server_config: MCPServerConfig, user_text: str) -> Dict[str, Any]:
    client = MCPClient(server_config)
    await client.connect()
    try:
        tools = await client.list_tools()
        selected_name, args = _pick_tool_and_args(user_text, tools)
        if not selected_name:
            return {
                "ok": False,
                "error": "NO_MATCHED_TOOL",
                "tools": [str(tool.get("name", "")) for tool in tools][:20],
            }

        # Generic AWS MCP mode: suggest command then execute via call_aws.
        has_call_aws = any(str(tool.get("name")) == "call_aws" for tool in tools)
        if selected_name == "suggest_aws_commands" and has_call_aws:
            if _is_monitoring_query(user_text):
                return await _execute_monitoring_probe(client, user_text)

            direct_commands = _build_direct_cli_commands(user_text)
            if direct_commands:
                if len(direct_commands) == 1:
                    exec_result = await client.call_tool("call_aws", {"cli_command": direct_commands[0], "max_results": 50})
                    return {
                        "ok": True,
                        "tool": "call_aws",
                        "mode": "direct_template",
                        "suggested_cli_command": direct_commands[0],
                        "result": exec_result,
                    }

                combined = []
                for cmd in direct_commands[:2]:
                    exec_result = await client.call_tool("call_aws", {"cli_command": cmd, "max_results": 50})
                    combined.append({"cli_command": cmd, "result": exec_result})
                return {
                    "ok": True,
                    "tool": "call_aws",
                    "mode": "direct_template_combined",
                    "suggested_cli_command": " ; ".join(direct_commands[:2]),
                    "result": {"combined": combined},
                }

            suggest_result = await client.call_tool("suggest_aws_commands", {"query": user_text})
            suggested_commands = _extract_suggested_commands(suggest_result)
            cli_command = _select_best_cli_command(suggested_commands, user_text)
            if not cli_command:
                cli_command = _extract_cli_command_from_suggest_result(suggest_result)
            if not cli_command:
                return {
                    "ok": False,
                    "error": "SUGGEST_NO_CLI_COMMAND",
                    "tool": "suggest_aws_commands",
                    "result": suggest_result,
                    "tools": [str(tool.get("name", "")) for tool in tools][:20],
                }
            exec_result = await client.call_tool("call_aws", {"cli_command": cli_command, "max_results": 50})
            return {
                "ok": True,
                "tool": "call_aws",
                "mode": "suggest_then_call",
                "suggested_cli_command": cli_command,
                "result": exec_result,
            }

        result = await client.call_tool(selected_name, args)
        return {"ok": True, "tool": selected_name, "result": result}
    finally:
        await client.disconnect()


def _summarize_result(payload: Dict[str, Any], user_text: str = "", is_en: Optional[bool] = None) -> str:
    if is_en is None:
        is_en = _is_english_query(user_text)
    if not payload.get("ok"):
        error_code = str(payload.get("error") or "")
        if _is_unsupported_operation_error(error_code):
            return _format_error_with_suggestions(
                title=_t(is_en, "当前能力暂未实现", "Capability not implemented yet"),
                reason=error_code,
                suggestions=[
                    _t(is_en, "这是平台适配器当前能力边界，不是输入错误。", "This is a platform adapter capability boundary, not an input error."),
                    _t(is_en, "可先执行只读查询（实例/监控/成本/资产清单）。", "You can continue with read-only queries first (instances/monitoring/cost/inventory)."),
                ],
                is_en=is_en,
            )
        if error_code == "MONITORING_INSTANCE_REQUIRED":
            return _format_error_with_suggestions(
                title=_t(is_en, "需要实例 ID", "Instance ID is required"),
                reason=_t(
                    is_en,
                    "你要查询的是实例监控，但消息里没有识别到 EC2 instance id（例如 i-0abc...）。",
                    "This is an instance monitoring query, but no EC2 instance id was detected (for example: i-0abc...).",
                ),
                suggestions=[
                    _t(is_en, "请重试：看下 i-xxxxxxxx 在 ap-southeast-2 最近 30 分钟 CPU/内存/磁盘。", "Retry like: check CPU/memory/disk for i-xxxxxxxx in ap-southeast-2 for last 30 minutes."),
                    _t(is_en, "或者先问：ap-southeast-2 有哪些 EC2 实例。", "Or ask first: which EC2 instances are in ap-southeast-2."),
                ],
                is_en=is_en,
            )
        if error_code == "SUGGEST_NO_CLI_COMMAND":
            return _format_error_with_suggestions(
                title=_t(is_en, "AWS 查询暂时无法执行", "Unable to run AWS query right now"),
                reason=_t(
                    is_en,
                    "MCP 没有为当前问题生成可执行的 AWS CLI 命令。",
                    "MCP did not generate an executable AWS CLI command for this request.",
                ),
                suggestions=[
                    _t(is_en, "换成更明确的只读问题，例如“列出 ap-southeast-2 的 EC2 实例”。", "Ask a more specific read-only question, for example: “List EC2 instances in ap-southeast-2”."),
                    _t(is_en, "明确你要查的维度：实例/健康/成本/用量/服务开通情况。", "Specify what you want: instances/health/cost/usage/service enablement."),
                    _t(is_en, "确认 AWS MCP 已启用且 region 已说明（例如 ap-southeast-2 或 Sydney）。", "Confirm AWS MCP is enabled and region is provided (for example: ap-southeast-2 or Sydney)."),
                ],
                is_en=is_en,
            )
        if error_code == "NO_MATCHED_TOOL":
            tools = payload.get("tools") or []
            tools_text = ", ".join(tools) if tools else "none"
            return _format_error_with_suggestions(
                title=_t(is_en, "AWS 工具匹配失败", "AWS tool matching failed"),
                reason=_t(
                    is_en,
                    f"当前请求没有匹配到可用工具。可用工具: {tools_text}",
                    f"No available tool matches this request. Available tools: {tools_text}",
                ),
                suggestions=[
                    _t(is_en, "改成只读查询并说明资源类型，例如 EC2、S3、成本或服务开通。", "Use a read-only query and specify resource type, for example EC2, S3, cost, or service enablement."),
                    _t(is_en, "如果是写操作（create/update/delete），请改走治理审批流程。", "If this is a write action (create/update/delete), use the governance approval flow."),
                ],
                is_en=is_en,
            )
        tools = payload.get("tools") or []
        return _format_error_with_suggestions(
            title=_t(is_en, "AWS 查询失败", "AWS query failed"),
            reason=_t(
                is_en,
                "AWS MCP 已启用，但当前请求无法匹配到可执行工具。"
                f"可用工具: {', '.join(tools) if tools else 'none'}",
                "AWS MCP is enabled but this request cannot be matched to an executable tool. "
                f"Available tools: {', '.join(tools) if tools else 'none'}",
            ),
            suggestions=[
                _t(is_en, "换成明确的只读问题并带上 region（例如 ap-southeast-2）。", "Use a clear read-only query and include region (for example: ap-southeast-2)."),
                _t(is_en, "如果问题涉及写删改操作，系统会默认拦截，请改为查询诉求。", "If your request includes write/delete operations, it will be blocked by policy. Rephrase as a query."),
            ],
            is_en=is_en,
        )

    tool = payload.get("tool")
    result = payload.get("result")
    region = payload.get("region")
    region_hint = f" (region={region})" if region else ""
    if payload.get("mode") == "monitor_probe":
        summary = _summarize_monitoring_probe(payload, user_text if is_en else "")
        source = _t(is_en, "数据来源", "Data source")
        return f"{summary}\n\n_{source}: AWS MCP{region_hint}_"
    if tool == "call_aws":
        pretty = _summarize_call_aws_result(result, user_text if is_en else "")
        if pretty:
            source = _t(is_en, "数据来源", "Data source")
            return f"{pretty}\n\n_{source}: AWS MCP{region_hint}_"
    return f"AWS MCP `{tool}` result{region_hint}:\n{result}"


def _extract_call_aws_payload(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    content = result.get("content")
    if not isinstance(content, list):
        return None
    for chunk in content:
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        try:
            outer = json.loads(text)
        except Exception:
            continue
        if not isinstance(outer, dict):
            continue
        response = outer.get("response")
        if isinstance(response, dict):
            json_str = response.get("json")
            if isinstance(json_str, str) and json_str.strip():
                try:
                    body = json.loads(json_str)
                except Exception:
                    body = None
            else:
                body = None
            return {
                "outer": outer,
                "response": response,
                "body": body if isinstance(body, dict) else None,
            }
    return None


def _extract_call_aws_error(result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(result, dict):
        return None
    content = result.get("content")
    if isinstance(content, list):
        for chunk in content:
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text") or "").strip()
            if not text:
                continue
            if "Error calling tool 'call_aws':" in text:
                return text.split("Error calling tool 'call_aws':", 1)[-1].strip()
            try:
                outer = json.loads(text)
            except Exception:
                continue
            if not isinstance(outer, dict):
                continue
            response = outer.get("response")
            if isinstance(response, dict):
                err = response.get("error")
                if err:
                    return str(err)
    return None


def _extract_missing_action(error_text: str) -> Optional[str]:
    if not error_text:
        return None
    m = re.search(r"not authorized to perform:\s*([A-Za-z0-9:*]+)", error_text, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"AccessDenied[^:]*:\s*User.*?perform:\s*([A-Za-z0-9:*]+)", error_text, re.IGNORECASE)
    return m.group(1) if m else None


def _policy_hint_for_action(action: str) -> str:
    lowered = (action or "").lower()
    if lowered.startswith("cloudwatch:"):
        return "CloudWatchReadOnlyAccess"
    if lowered.startswith("ec2:describe"):
        return "AmazonEC2ReadOnlyAccess"
    if lowered.startswith("ssm:"):
        return "AmazonSSMFullAccess (or least-privilege SSM command actions)"
    if lowered.startswith("ce:"):
        return "Billing/Cost Explorer read permissions (ce:GetCostAndUsage)"
    return "least-privilege policy including the missing action"


def _build_permission_guidance(error_text: str, user_text: str) -> Optional[str]:
    action = _extract_missing_action(error_text or "")
    if not action:
        return None
    is_en = _is_english_query(user_text)
    policy_hint = _policy_hint_for_action(action)
    user_arn = None
    m = re.search(r"User:\s*(arn:[^\s]+)", error_text)
    if m:
        user_arn = m.group(1)
    identity_line = _t(
        is_en,
        f"当前调用身份: `{user_arn}`\n" if user_arn else "",
        f"Current caller identity: `{user_arn}`\n" if user_arn else "",
    )
    return "\n".join(
        [
            _t(
                is_en,
                f"缺失权限: `{action}`",
                f"Missing permission: `{action}`",
            ),
            identity_line.rstrip(),
            _t(
                is_en,
                f"建议策略: `{policy_hint}`",
                f"Suggested policy: `{policy_hint}`",
            ),
            _t(
                is_en,
                "操作位置: AWS Console -> IAM -> Users/Roles -> 选择当前身份 -> Add permissions。",
                "Where to configure: AWS Console -> IAM -> Users/Roles -> select current identity -> Add permissions.",
            ),
        ]
    ).strip()


def _extract_principal_arn(error_text: str) -> Optional[str]:
    m = re.search(r"User:\s*(arn:[^\s]+)", error_text or "")
    return m.group(1) if m else None


def _extract_account_id_from_arn(arn: str) -> Optional[str]:
    m = re.match(r"^arn:aws:iam::(\d{12}):", arn or "")
    return m.group(1) if m else None


def _build_minimal_bind_policy_json(account_id: Optional[str]) -> str:
    account = account_id or "123456789012"
    payload = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "OctopusOSCreateMinimalRoleAndProfile",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:AttachRolePolicy",
                    "iam:CreateInstanceProfile",
                    "iam:AddRoleToInstanceProfile",
                    "iam:GetRole",
                    "iam:GetInstanceProfile",
                    "iam:PassRole",
                ],
                "Resource": [
                    f"arn:aws:iam::{account}:role/OctopusOS-SSM-CWAgent-*",
                    f"arn:aws:iam::{account}:instance-profile/OctopusOS-SSM-CWAgent-*",
                ],
            },
            {
                "Sid": "OctopusOSAssociateProfileToEC2",
                "Effect": "Allow",
                "Action": [
                    "ec2:AssociateIamInstanceProfile",
                    "ec2:DisassociateIamInstanceProfile",
                    "ec2:DescribeIamInstanceProfileAssociations",
                    "ec2:DescribeInstances",
                ],
                "Resource": "*",
            },
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _is_bind_permission_denied(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    if "accessdenied" not in lowered and "not authorized to perform" not in lowered:
        return False
    action = (_extract_missing_action(error_text) or "").lower()
    if not action:
        return False
    return action.startswith("iam:") or action.startswith("ec2:associateiaminstanceprofile")


async def _execute_monitoring_probe(client: MCPClient, user_text: str) -> Dict[str, Any]:
    instance_id = _extract_instance_id(user_text)
    window_minutes = _extract_window_minutes(user_text)
    if not instance_id:
        return {
            "ok": False,
            "error": "MONITORING_INSTANCE_REQUIRED",
            "window_minutes": window_minutes,
        }

    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=window_minutes)
    end = now
    start_iso = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_iso = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    describe_cmd = f"aws ec2 describe-instances --instance-ids {instance_id}"
    cpu_cmd = (
        "aws cloudwatch get-metric-statistics "
        "--namespace AWS/EC2 "
        "--metric-name CPUUtilization "
        f"--dimensions Name=InstanceId,Value={instance_id} "
        "--statistics Average Maximum "
        "--period 300 "
        f"--start-time {start_iso} --end-time {end_iso}"
    )
    mem_list_cmd = (
        "aws cloudwatch list-metrics "
        "--namespace CWAgent "
        "--metric-name mem_used_percent "
        f"--dimensions Name=InstanceId,Value={instance_id}"
    )
    disk_list_cmd = (
        "aws cloudwatch list-metrics "
        "--namespace CWAgent "
        "--metric-name disk_used_percent "
        f"--dimensions Name=InstanceId,Value={instance_id}"
    )

    describe_res = await client.call_tool("call_aws", {"cli_command": describe_cmd, "max_results": 50})
    cpu_res = await client.call_tool("call_aws", {"cli_command": cpu_cmd, "max_results": 50})
    mem_list_res = await client.call_tool("call_aws", {"cli_command": mem_list_cmd, "max_results": 50})
    disk_list_res = await client.call_tool("call_aws", {"cli_command": disk_list_cmd, "max_results": 50})

    mem_metrics: List[Dict[str, Any]] = []
    disk_metrics: List[Dict[str, Any]] = []
    parsed = _extract_call_aws_payload(mem_list_res)
    if parsed and isinstance(parsed.get("body"), dict):
        mem_metrics = (parsed["body"].get("Metrics") or []) if isinstance(parsed["body"].get("Metrics"), list) else []
    parsed = _extract_call_aws_payload(disk_list_res)
    if parsed and isinstance(parsed.get("body"), dict):
        disk_metrics = (parsed["body"].get("Metrics") or []) if isinstance(parsed["body"].get("Metrics"), list) else []

    mem_res = None
    disk_res = None
    if mem_metrics:
        dims_arg = _dimensions_cli_arg(_extract_metric_dimensions(mem_metrics[0]))
        mem_cmd = (
            "aws cloudwatch get-metric-statistics "
            "--namespace CWAgent "
            "--metric-name mem_used_percent "
            f"--dimensions {dims_arg} "
            "--statistics Average Maximum "
            "--period 300 "
            f"--start-time {start_iso} --end-time {end_iso}"
        )
        mem_res = await client.call_tool("call_aws", {"cli_command": mem_cmd, "max_results": 50})
    if disk_metrics:
        dims_arg = _dimensions_cli_arg(_extract_metric_dimensions(disk_metrics[0]))
        disk_cmd = (
            "aws cloudwatch get-metric-statistics "
            "--namespace CWAgent "
            "--metric-name disk_used_percent "
            f"--dimensions {dims_arg} "
            "--statistics Average Maximum "
            "--period 300 "
            f"--start-time {start_iso} --end-time {end_iso}"
        )
        disk_res = await client.call_tool("call_aws", {"cli_command": disk_cmd, "max_results": 50})

    return {
        "ok": True,
        "tool": "call_aws",
        "mode": "monitor_probe",
        "instance_id": instance_id,
        "window_minutes": window_minutes,
        "monitoring": {
            "describe": describe_res,
            "cpu": cpu_res,
            "memory_list": mem_list_res,
            "disk_list": disk_list_res,
            "memory": mem_res,
            "disk": disk_res,
            "has_cwagent_memory": bool(mem_metrics),
            "has_cwagent_disk": bool(disk_metrics),
        },
    }


def _extract_ssm_command_id(result: Dict[str, Any]) -> Optional[str]:
    parsed = _extract_call_aws_payload(result)
    if not parsed:
        return None
    body = parsed.get("body")
    if not isinstance(body, dict):
        return None
    command = body.get("Command")
    if not isinstance(command, dict):
        return None
    command_id = command.get("CommandId")
    return str(command_id) if command_id else None


async def _wait_ssm_command(client: MCPClient, command_id: str, instance_id: str, retries: int = 24) -> Dict[str, Any]:
    last: Dict[str, Any] = {}
    for _ in range(retries):
        cmd = f"aws ssm get-command-invocation --command-id {command_id} --instance-id {instance_id}"
        res = await client.call_tool("call_aws", {"cli_command": cmd, "max_results": 50})
        parsed = _extract_call_aws_payload(res)
        if parsed and isinstance(parsed.get("body"), dict):
            body = parsed["body"]
            status = str(body.get("Status") or "")
            last = body
            if status in {"Success", "Failed", "Cancelled", "TimedOut", "Undeliverable", "Terminated"}:
                return body
        await asyncio.sleep(5)
    return last


async def _execute_cwagent_install(client: MCPClient, instance_id: str) -> Dict[str, Any]:
    install_cmd = (
        "aws ssm send-command "
        "--document-name AWS-ConfigureAWSPackage "
        f"--targets Key=instanceids,Values={instance_id} "
        "--parameters action=Install,name=AmazonCloudWatchAgent "
        "--comment octopusos-install-cwagent"
    )
    install_res = await client.call_tool("call_aws", {"cli_command": install_cmd, "max_results": 50})
    install_err = _extract_call_aws_error(install_res)
    if install_err:
        return {"ok": False, "stage": "install_package", "error": install_err}
    install_command_id = _extract_ssm_command_id(install_res)
    if not install_command_id:
        return {"ok": False, "stage": "install_package", "error": "Unable to parse SSM install command id."}
    install_status = await _wait_ssm_command(client, install_command_id, instance_id)
    if str(install_status.get("Status") or "") != "Success":
        return {"ok": False, "stage": "install_package", "error": str(install_status)}

    manage_cmd = (
        "aws ssm send-command "
        "--document-name AmazonCloudWatch-ManageAgent "
        f"--targets Key=instanceids,Values={instance_id} "
        "--parameters action=configure,mode=ec2,optionalConfigurationSource=default,optionalRestart=yes "
        "--comment octopusos-configure-cwagent"
    )
    manage_res = await client.call_tool("call_aws", {"cli_command": manage_cmd, "max_results": 50})
    manage_err = _extract_call_aws_error(manage_res)
    if manage_err:
        return {"ok": False, "stage": "configure_agent", "error": manage_err}
    manage_command_id = _extract_ssm_command_id(manage_res)
    if not manage_command_id:
        return {"ok": False, "stage": "configure_agent", "error": "Unable to parse SSM configure command id."}
    manage_status = await _wait_ssm_command(client, manage_command_id, instance_id)
    if str(manage_status.get("Status") or "") != "Success":
        return {"ok": False, "stage": "configure_agent", "error": str(manage_status)}

    return {
        "ok": True,
        "install_command_id": install_command_id,
        "configure_command_id": manage_command_id,
    }


def _extract_response_body(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    parsed = _extract_call_aws_payload(result)
    if not parsed:
        return None
    body = parsed.get("body")
    return body if isinstance(body, dict) else None


def _ssm_error_category(error_text: str) -> str:
    lowered = (error_text or "").lower()
    if "invalidinstanceid" in lowered and "sendcommand".lower() in lowered:
        return "ssm_target_not_managed"
    if "targetnotconnected" in lowered or "not connected" in lowered:
        return "ssm_target_not_connected"
    if "not authorized to perform: ssm:" in lowered or "accessdenied" in lowered:
        return "ssm_permission_denied"
    return "unknown"


async def _call_aws_body_or_error(client: MCPClient, cli_command: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    res = await client.call_tool("call_aws", {"cli_command": cli_command, "max_results": 50})
    err = _extract_call_aws_error(res)
    if err:
        return None, err
    return _extract_response_body(res), None


def _instance_profile_name_from_arn(profile_arn: str) -> Optional[str]:
    if not profile_arn:
        return None
    tail = profile_arn.split("/")[-1].strip()
    return tail or None


async def _wait_ssm_managed_online(client: MCPClient, instance_id: str, retries: int = 8) -> bool:
    for _ in range(retries):
        body, err = await _call_aws_body_or_error(
            client,
            f"aws ssm describe-instance-information --filters Key=InstanceIds,Values={instance_id}",
        )
        if err:
            return False
        infos = (body or {}).get("InstanceInformationList")
        if isinstance(infos, list) and infos:
            first = infos[0] if isinstance(infos[0], dict) else {}
            ping = str(first.get("PingStatus") or "").lower()
            if ping == "online":
                return True
        await asyncio.sleep(10)
    return False


async def _execute_ssm_prereq_remediation(client: MCPClient, instance_id: str) -> Dict[str, Any]:
    outcome: Dict[str, Any] = {"ok": False, "steps": []}

    # 1) Resolve instance profile and role
    body, err = await _call_aws_body_or_error(
        client, f"aws ec2 describe-instances --instance-ids {instance_id}"
    )
    if err:
        return {"ok": False, "stage": "describe_instance", "error": err, "steps": outcome["steps"]}
    reservations = (body or {}).get("Reservations")
    if not isinstance(reservations, list) or not reservations:
        return {"ok": False, "stage": "describe_instance", "error": "Instance not found.", "steps": outcome["steps"]}
    instance = {}
    for r in reservations:
        if isinstance(r, dict):
            instances = r.get("Instances")
            if isinstance(instances, list) and instances:
                instance = instances[0] if isinstance(instances[0], dict) else {}
                break
    iam_profile = instance.get("IamInstanceProfile") if isinstance(instance, dict) else {}
    profile_arn = str((iam_profile or {}).get("Arn") or "")
    profile_name = _instance_profile_name_from_arn(profile_arn)
    if not profile_name:
        return {
            "ok": False,
            "stage": "instance_profile_missing",
            "error": "Instance has no IAM Instance Profile. Auto-remediation cannot attach a role without explicit profile input.",
            "steps": outcome["steps"],
        }
    outcome["steps"].append({"name": "instance_profile_detected", "ok": True, "profile_name": profile_name})

    body, err = await _call_aws_body_or_error(
        client, f"aws iam get-instance-profile --instance-profile-name {profile_name}"
    )
    if err:
        return {"ok": False, "stage": "get_instance_profile", "error": err, "steps": outcome["steps"]}
    roles = ((body or {}).get("InstanceProfile") or {}).get("Roles")
    if not isinstance(roles, list) or not roles:
        return {"ok": False, "stage": "instance_profile_role_missing", "error": "Instance profile has no role.", "steps": outcome["steps"]}
    role_name = str((roles[0] or {}).get("RoleName") or "")
    if not role_name:
        return {"ok": False, "stage": "instance_profile_role_missing", "error": "Unable to resolve role name.", "steps": outcome["steps"]}
    outcome["steps"].append({"name": "instance_role_detected", "ok": True, "role_name": role_name})

    # 2) Ensure required policy on instance role
    body, err = await _call_aws_body_or_error(
        client, f"aws iam list-attached-role-policies --role-name {role_name}"
    )
    if err:
        return {"ok": False, "stage": "list_role_policies", "error": err, "steps": outcome["steps"]}
    attached = (body or {}).get("AttachedPolicies")
    attached_arns = set()
    if isinstance(attached, list):
        for p in attached:
            if isinstance(p, dict):
                arn = str(p.get("PolicyArn") or "").strip()
                if arn:
                    attached_arns.add(arn)
    ssm_core_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    if ssm_core_arn not in attached_arns:
        _, attach_err = await _call_aws_body_or_error(
            client,
            f"aws iam attach-role-policy --role-name {role_name} --policy-arn {ssm_core_arn}",
        )
        if attach_err:
            return {"ok": False, "stage": "attach_ssm_core_policy", "error": attach_err, "steps": outcome["steps"]}
        outcome["steps"].append({"name": "attach_ssm_core_policy", "ok": True, "policy_arn": ssm_core_arn})
    else:
        outcome["steps"].append({"name": "attach_ssm_core_policy", "ok": True, "already_present": True})

    # 3) Wait until SSM managed node is online
    online = await _wait_ssm_managed_online(client, instance_id)
    outcome["steps"].append({"name": "wait_ssm_online", "ok": online})
    if not online:
        return {
            "ok": False,
            "stage": "wait_ssm_online",
            "error": "Instance is still not online in SSM Managed Nodes.",
            "steps": outcome["steps"],
        }

    outcome["ok"] = True
    return outcome


def _extract_iam_choice(user_text: str) -> Optional[Dict[str, str]]:
    text = (user_text or "").strip()
    lowered = text.lower()
    if not text:
        return None
    if any(token in lowered for token in ("创建最小权限", "create minimal", "recommended role", "new role")):
        return {"kind": "create_minimal"}

    # Explicit key-value hints
    m = re.search(r"(?:profile|instance profile)\s*[:=]\s*([A-Za-z0-9+=,.@_-]{1,128})", text, re.IGNORECASE)
    if m:
        return {"kind": "profile", "name": m.group(1)}
    m = re.search(r"(?:role)\s*[:=]\s*([A-Za-z0-9+=,.@_-]{1,128})", text, re.IGNORECASE)
    if m:
        return {"kind": "role", "name": m.group(1)}

    # Plain single token fallback
    token_match = re.fullmatch(r"[A-Za-z0-9+=,.@_-]{3,128}", text)
    if token_match:
        name = token_match.group(0)
        if "profile" in lowered or lowered.startswith("ip-"):
            return {"kind": "profile", "name": name}
        return {"kind": "role", "name": name}
    return None



async def _ensure_role_policy(client: MCPClient, role_name: str, policy_arn: str) -> Optional[str]:
    body, err = await _call_aws_body_or_error(
        client, f"aws iam list-attached-role-policies --role-name {role_name}"
    )
    if err:
        return err
    attached = (body or {}).get("AttachedPolicies")
    attached_arns = set()
    if isinstance(attached, list):
        for p in attached:
            if isinstance(p, dict):
                arn = str(p.get("PolicyArn") or "").strip()
                if arn:
                    attached_arns.add(arn)
    if policy_arn in attached_arns:
        return None
    _, attach_err = await _call_aws_body_or_error(
        client, f"aws iam attach-role-policy --role-name {role_name} --policy-arn {policy_arn}"
    )
    return attach_err


async def _ensure_instance_profile_for_role(
    client: MCPClient, role_name: str, preferred_profile: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    profile_name = preferred_profile or f"ip-{role_name}"
    body, err = await _call_aws_body_or_error(
        client, f"aws iam get-instance-profile --instance-profile-name {profile_name}"
    )
    if err and "NoSuchEntity" in err:
        _, create_err = await _call_aws_body_or_error(
            client, f"aws iam create-instance-profile --instance-profile-name {profile_name}"
        )
        if create_err:
            return None, create_err
        body, err = await _call_aws_body_or_error(
            client, f"aws iam get-instance-profile --instance-profile-name {profile_name}"
        )
    if err:
        return None, err

    roles = ((body or {}).get("InstanceProfile") or {}).get("Roles")
    role_names = set()
    if isinstance(roles, list):
        for r in roles:
            if isinstance(r, dict):
                rn = str(r.get("RoleName") or "").strip()
                if rn:
                    role_names.add(rn)
    if role_name not in role_names:
        _, add_err = await _call_aws_body_or_error(
            client, f"aws iam add-role-to-instance-profile --instance-profile-name {profile_name} --role-name {role_name}"
        )
        if add_err and "LimitExceeded" not in add_err and "EntityAlreadyExists" not in add_err:
            return None, add_err
    return profile_name, None


async def _associate_instance_profile(client: MCPClient, instance_id: str, profile_name: str) -> Optional[str]:
    body, err = await _call_aws_body_or_error(
        client,
        f"aws ec2 describe-iam-instance-profile-associations --filters Name=instance-id,Values={instance_id}",
    )
    if err:
        return err
    associations = (body or {}).get("IamInstanceProfileAssociations")
    active_assoc = None
    if isinstance(associations, list):
        for a in associations:
            if isinstance(a, dict):
                state = str(a.get("State") or "").lower()
                if state in {"associating", "associated"}:
                    active_assoc = a
                    break
    if active_assoc:
        current_arn = str(((active_assoc.get("IamInstanceProfile") or {}).get("Arn")) or "")
        current_name = _instance_profile_name_from_arn(current_arn)
        if current_name == profile_name:
            return None
        assoc_id = str(active_assoc.get("AssociationId") or "")
        if assoc_id:
            _, dis_err = await _call_aws_body_or_error(
                client, f"aws ec2 disassociate-iam-instance-profile --association-id {assoc_id}"
            )
            if dis_err:
                return dis_err
            await asyncio.sleep(2)

    _, assoc_err = await _call_aws_body_or_error(
        client,
        f"aws ec2 associate-iam-instance-profile --instance-id {instance_id} --iam-instance-profile Name={profile_name}",
    )
    return assoc_err


def _monitor_has_cwagent_metrics(payload: Dict[str, Any]) -> bool:
    monitoring = payload.get("monitoring") if isinstance(payload.get("monitoring"), dict) else {}
    return bool(monitoring.get("has_cwagent_memory")) or bool(monitoring.get("has_cwagent_disk"))


def _extract_bind_change_summary(bind: Dict[str, Any], is_en: bool) -> str:
    role_name = str(bind.get("role_name") or "-")
    profile_name = str(bind.get("profile_name") or "-")
    steps = bind.get("steps") if isinstance(bind.get("steps"), list) else []
    online = any(isinstance(s, dict) and s.get("name") == "wait_ssm_online" and s.get("ok") for s in steps)
    lines = [
        _t(is_en, "**本次变更清单**", "**Change Summary**"),
        _t(is_en, f"- IAM Role: `{role_name}`", f"- IAM Role: `{role_name}`"),
        _t(is_en, f"- Instance Profile: `{profile_name}`", f"- Instance Profile: `{profile_name}`"),
        _t(
            is_en,
            f"- 绑定与接管: 已绑定到实例并等待 SSM Online（{'成功' if online else '未就绪'}）",
            f"- Binding and takeover: profile associated and waited for SSM Online ({'ready' if online else 'not ready'})",
        ),
    ]
    return "\n".join(lines)



async def _execute_bind_instance_profile_flow(
    client: MCPClient,
    instance_id: str,
    choice: Dict[str, str],
) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    ssm_policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    cw_policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"

    role_name: Optional[str] = None
    profile_name: Optional[str] = None
    kind = choice.get("kind")
    if kind == "create_minimal":
        suffix = instance_id[-6:]
        role_name = f"OctopusOS-SSM-CWAgent-{suffix}"
        trust = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        _, role_err = await _call_aws_body_or_error(
            client,
            f"aws iam create-role --role-name {role_name} --assume-role-policy-document '{trust}'",
        )
        if role_err and "EntityAlreadyExists" not in role_err:
            return {"ok": False, "stage": "create_role", "error": role_err, "steps": steps}
        steps.append({"name": "create_role", "ok": True, "role_name": role_name})
        e = await _ensure_role_policy(client, role_name, ssm_policy_arn)
        if e:
            return {"ok": False, "stage": "attach_ssm_policy", "error": e, "steps": steps}
        e = await _ensure_role_policy(client, role_name, cw_policy_arn)
        if e:
            return {"ok": False, "stage": "attach_cw_policy", "error": e, "steps": steps}
        profile_name, pe = await _ensure_instance_profile_for_role(client, role_name)
        if pe:
            return {"ok": False, "stage": "ensure_profile", "error": pe, "steps": steps}
    elif kind == "role":
        role_name = str(choice.get("name") or "").strip()
        if not role_name:
            return {"ok": False, "stage": "parse_choice", "error": "Role name is empty.", "steps": steps}
        _, role_err = await _call_aws_body_or_error(client, f"aws iam get-role --role-name {role_name}")
        if role_err:
            return {"ok": False, "stage": "get_role", "error": role_err, "steps": steps}
        e = await _ensure_role_policy(client, role_name, ssm_policy_arn)
        if e:
            return {"ok": False, "stage": "attach_ssm_policy", "error": e, "steps": steps}
        e = await _ensure_role_policy(client, role_name, cw_policy_arn)
        if e:
            return {"ok": False, "stage": "attach_cw_policy", "error": e, "steps": steps}
        profile_name, pe = await _ensure_instance_profile_for_role(client, role_name)
        if pe:
            return {"ok": False, "stage": "ensure_profile", "error": pe, "steps": steps}
    elif kind == "profile":
        profile_name = str(choice.get("name") or "").strip()
        if not profile_name:
            return {"ok": False, "stage": "parse_choice", "error": "Instance profile name is empty.", "steps": steps}
        body, pe = await _call_aws_body_or_error(
            client, f"aws iam get-instance-profile --instance-profile-name {profile_name}"
        )
        if pe:
            return {"ok": False, "stage": "get_instance_profile", "error": pe, "steps": steps}
        roles = ((body or {}).get("InstanceProfile") or {}).get("Roles")
        if not isinstance(roles, list) or not roles:
            return {"ok": False, "stage": "instance_profile_role_missing", "error": "Instance profile has no role.", "steps": steps}
        role_name = str((roles[0] or {}).get("RoleName") or "").strip()
        if not role_name:
            return {"ok": False, "stage": "instance_profile_role_missing", "error": "Unable to resolve role from profile.", "steps": steps}
        e = await _ensure_role_policy(client, role_name, ssm_policy_arn)
        if e:
            return {"ok": False, "stage": "attach_ssm_policy", "error": e, "steps": steps}
        e = await _ensure_role_policy(client, role_name, cw_policy_arn)
        if e:
            return {"ok": False, "stage": "attach_cw_policy", "error": e, "steps": steps}
    else:
        return {"ok": False, "stage": "parse_choice", "error": "Unsupported IAM choice.", "steps": steps}

    steps.append({"name": "resolved_binding_choice", "ok": True, "role_name": role_name, "profile_name": profile_name})
    assoc_err = await _associate_instance_profile(client, instance_id, str(profile_name))
    if assoc_err:
        return {"ok": False, "stage": "associate_instance_profile", "error": assoc_err, "steps": steps}
    steps.append({"name": "associate_instance_profile", "ok": True, "profile_name": profile_name})

    online = await _wait_ssm_managed_online(client, instance_id)
    steps.append({"name": "wait_ssm_online", "ok": online})
    if not online:
        return {"ok": False, "stage": "wait_ssm_online", "error": "Instance is still not online in SSM Managed Nodes.", "steps": steps}

    return {"ok": True, "steps": steps, "role_name": role_name or "", "profile_name": profile_name or ""}


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def _metric_stats_from_call_aws_result(result: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    if not isinstance(result, dict):
        return None
    parsed = _extract_call_aws_payload(result)
    if not parsed:
        return None
    body = parsed.get("body")
    if not isinstance(body, dict):
        return None
    points = body.get("Datapoints")
    if not isinstance(points, list) or not points:
        return None
    avgs = [_safe_float(p.get("Average")) for p in points if isinstance(p, dict) and p.get("Average") is not None]
    maxs = [_safe_float(p.get("Maximum")) for p in points if isinstance(p, dict) and p.get("Maximum") is not None]
    out: Dict[str, float] = {}
    if avgs:
        out["avg"] = sum(avgs) / len(avgs)
    if maxs:
        out["max"] = max(maxs)
    out["points"] = float(len(points))
    return out if out else None


def _summarize_monitoring_probe(payload: Dict[str, Any], user_text: str) -> str:
    is_en = _is_english_query(user_text)
    instance_id = str(payload.get("instance_id") or "-")
    window_minutes = int(payload.get("window_minutes") or 30)
    monitoring = payload.get("monitoring") if isinstance(payload.get("monitoring"), dict) else {}

    if not monitoring:
        return _format_error_with_suggestions(
            title=_t(is_en, "监控查询失败", "Monitoring query failed"),
            reason=_t(is_en, "监控执行结果为空。", "Monitoring execution result is empty."),
            suggestions=[
                _t(is_en, "请稍后重试。", "Please retry in a moment."),
            ],
            is_en=is_en,
        )

    errors: List[str] = []
    for key in ("describe", "cpu", "memory_list", "disk_list", "memory", "disk"):
        err = _extract_call_aws_error(monitoring.get(key))
        if err:
            errors.append(err)
    if errors:
        guidance = _build_permission_guidance(errors[0], user_text)
        if guidance:
            return _format_error_with_suggestions(
                title=_t(is_en, "监控读取失败（权限不足）", "Monitoring read failed (insufficient permissions)"),
                reason=errors[0][:500],
                suggestions=[
                    guidance,
                    _t(is_en, "权限添加完成后，重发同一句查询即可自动继续。", "After adding permissions, resend the same query and I will continue automatically."),
                ],
                is_en=is_en,
            )
        return _format_error_with_suggestions(
            title=_t(is_en, "监控读取失败", "Monitoring read failed"),
            reason=errors[0][:500],
            suggestions=[
                _t(is_en, "检查当前 AWS Profile 权限。", "Check IAM permissions for the current AWS profile."),
                _t(is_en, "确认实例和 region 正确。", "Confirm instance ID and region are correct."),
            ],
            is_en=is_en,
        )

    has_mem = bool(monitoring.get("has_cwagent_memory"))
    has_disk = bool(monitoring.get("has_cwagent_disk"))
    has_agent = has_mem or has_disk
    payload_for_report = dict(payload)
    payload_for_report.setdefault("instance_id", instance_id)
    payload_for_report.setdefault("window_minutes", window_minutes)
    report = build_ops_report_from_monitoring(payload=payload_for_report, is_en=is_en)
    lines = [render_ops_report_markdown(report, is_en=is_en)]
    if not has_agent:
        lines.extend(
            [
                "",
                _t(
                    is_en,
                    "我能读取 CPU，但没有发现 CloudWatch Agent 指标，因此无法给出内存/磁盘占用率。",
                    "CPU is available, but CloudWatch Agent metrics are missing, so memory/disk utilization cannot be read.",
                ),
                _t(
                    is_en,
                    "这通常表示实例未安装或未启动 AWS 官方 CloudWatch Agent。",
                    "This usually means AWS CloudWatch Agent is not installed or not running on the instance.",
                ),
                _t(
                    is_en,
                    "要不要我帮你通过 SSM 安装并启用 CloudWatch Agent（无需 SSH）？",
                    "Do you want me to install and enable CloudWatch Agent via SSM (no SSH required)?",
                ),
                _t(
                    is_en,
                    "如果执行安装，你需要的权限是: ssm:SendCommand, ssm:GetCommandInvocation；实例角色建议附加 CloudWatchAgentServerPolicy。",
                    "If we proceed with installation, required permissions are: ssm:SendCommand, ssm:GetCommandInvocation; instance role should include CloudWatchAgentServerPolicy.",
                ),
                _t(
                    is_en,
                    "操作位置: AWS Console -> IAM(用户/角色权限) 与 EC2 -> Instance -> Security -> IAM Role。",
                    "Where to configure: AWS Console -> IAM (caller permissions) and EC2 -> Instance -> Security -> IAM Role.",
                ),
            ]
        )

    return "\n".join(lines)


def _summarize_cost_or_usage(body: Dict[str, Any], user_text: str) -> Optional[str]:
    results = body.get("ResultsByTime")
    if not isinstance(results, list) or not results:
        return None

    lowered = user_text.lower()
    is_en = _is_english_query(user_text)
    metric_order = ["UnblendedCost", "AmortizedCost", "BlendedCost", "NetAmortizedCost", "UsageQuantity"]
    looks_like_usage = any(k in lowered for k in ("usage", "用量", "utilization", "利用率"))

    per_period: List[Tuple[str, float, str, str]] = []
    group_totals: Counter = Counter()
    metric_name = ""
    unit = ""

    for item in results:
        if not isinstance(item, dict):
            continue
        time_period = item.get("TimePeriod") if isinstance(item.get("TimePeriod"), dict) else {}
        period = str(time_period.get("Start") or "")
        totals = item.get("Total") if isinstance(item.get("Total"), dict) else {}
        groups = item.get("Groups") if isinstance(item.get("Groups"), list) else []

        chosen_metric = ""
        if looks_like_usage and "UsageQuantity" in totals:
            chosen_metric = "UsageQuantity"
        else:
            for m in metric_order:
                if m in totals:
                    chosen_metric = m
                    break
        if not chosen_metric and groups:
            # CE group-by queries may return empty `Total` and put values only in `Groups`.
            for g in groups:
                if not isinstance(g, dict):
                    continue
                metrics = g.get("Metrics") if isinstance(g.get("Metrics"), dict) else {}
                for m in metric_order:
                    if m in metrics:
                        chosen_metric = m
                        break
                if chosen_metric:
                    break
        if not chosen_metric:
            continue
        metric_name = metric_name or chosen_metric
        metric_obj = totals.get(chosen_metric) if isinstance(totals.get(chosen_metric), dict) else {}
        amount = _safe_float(metric_obj.get("Amount"))
        metric_unit = str(metric_obj.get("Unit") or "")
        use_group_amount_for_period = chosen_metric not in totals

        for g in groups:
            if not isinstance(g, dict):
                continue
            keys = g.get("Keys") if isinstance(g.get("Keys"), list) else []
            k = str(keys[0] if keys else "Unknown")
            metrics = g.get("Metrics") if isinstance(g.get("Metrics"), dict) else {}
            mobj = metrics.get(chosen_metric) if isinstance(metrics.get(chosen_metric), dict) else {}
            group_amount = _safe_float(mobj.get("Amount"))
            group_totals[k] += group_amount
            if use_group_amount_for_period:
                amount += group_amount
            if not metric_unit:
                metric_unit = str(mobj.get("Unit") or "")

        unit = unit or metric_unit
        per_period.append((period, amount, unit, chosen_metric))

    if not per_period:
        return None

    total_amount = sum(v for _, v, _, _ in per_period)
    period_start = per_period[0][0]
    period_end = per_period[-1][0]
    is_cost = ("Cost" in metric_name) and not looks_like_usage
    title = _t(is_en, "成本总览" if is_cost else "用量总览", "Cost Summary" if is_cost else "Usage Summary")
    unit_label = unit or ("USD" if is_cost else "")
    amount_str = f"{total_amount:,.2f} {unit_label}".strip()

    lines = [
        f"**{title}**",
        _t(is_en, f"统计区间: {period_start} ~ {period_end}", f"Period: {period_start} ~ {period_end}"),
        _t(is_en, f"合计: **{amount_str}** ({metric_name})", f"Total: **{amount_str}** ({metric_name})"),
        "",
        _t(is_en, "| 时间 | 数值 |", "| Time | Value |"),
        "| --- | ---: |",
    ]
    for period, amount, _, _ in per_period[-6:]:
        lines.append(f"| {period} | {amount:,.2f} |")

    if group_totals:
        lines.extend(["", _t(is_en, "| 维度 | 数值 | 占比 |", "| Dimension | Value | Ratio |"), "| --- | ---: | ---: |"])
        denom = sum(group_totals.values()) or 1.0
        for name, amount in group_totals.most_common(6):
            ratio = amount / denom * 100.0
            lines.append(f"| {name} | {amount:,.2f} | {ratio:.1f}% |")

    if is_cost:
        lines.extend(["", _t(is_en, "建议关注:", "Recommendations:")])
        for idx, suggestion in enumerate(_build_cost_optimization_suggestions(group_totals, is_en), start=1):
            lines.append(f"{idx}. {suggestion}")
    return "\n".join(lines)


def _build_cost_optimization_suggestions(group_totals: Counter, is_en: bool = False) -> List[str]:
    default_zh = [
        "Top 维度占比高的项目是否可降配/按需切换。",
        "长时间低负载实例是否可关停或改用 Savings Plans。",
    ]
    default_en = [
        "Review top cost dimensions and consider rightsizing or usage model changes.",
        "For long-running low-utilization workloads, consider shutdown scheduling or Savings Plans.",
    ]
    default = default_en if is_en else default_zh
    if not group_totals:
        return default

    suggestions: List[str] = []
    top_positive = [(name, amount) for name, amount in group_totals.most_common(3) if amount > 0]
    for name, _ in top_positive:
        service = name.lower()
        if "ec2" in service or "elastic compute cloud" in service:
            suggestions.append(_t(is_en, "EC2 成本较高：检查实例规格与利用率，优先处理低负载实例并评估 Savings Plans/RI。", "EC2 cost is high: review instance sizing/utilization, and evaluate Savings Plans/RI for steady workloads."))
        elif "rds" in service:
            suggestions.append(_t(is_en, "RDS 成本较高：检查实例代际与存储类型，评估自动暂停、读写分离和预留实例。", "RDS cost is high: review instance generation/storage class, and evaluate auto-pause/read-replica/RI options."))
        elif "nat" in service:
            suggestions.append(_t(is_en, "NAT Gateway 成本较高：排查跨 AZ/跨公网流量，考虑 VPC Endpoint 旁路公网流量。", "NAT Gateway cost is high: check cross-AZ/public egress and use VPC Endpoints where possible."))
        elif "s3" in service:
            suggestions.append(_t(is_en, "S3 成本较高：启用生命周期策略，将冷数据转入 IA/Glacier，并清理历史版本。", "S3 cost is high: apply lifecycle policies, move cold data to IA/Glacier, and clean up old versions."))
        elif "cloudwatch" in service:
            suggestions.append(_t(is_en, "CloudWatch 成本较高：收敛高频自定义指标与日志保留天数。", "CloudWatch cost is high: reduce high-frequency custom metrics and shorten log retention where acceptable."))
        elif "lambda" in service:
            suggestions.append(_t(is_en, "Lambda 成本较高：优化内存与超时配置，减少空转调用。", "Lambda cost is high: optimize memory/timeout settings and reduce idle invocations."))

    if not suggestions:
        return default
    if len(suggestions) < 2:
        suggestions.extend(default[: 2 - len(suggestions)])
    return suggestions


def _summarize_instance_status(body: Dict[str, Any], user_text: str = "") -> Optional[str]:
    is_en = _is_english_query(user_text)
    statuses = body.get("InstanceStatuses")
    if not isinstance(statuses, list):
        return None
    if not statuses:
        return _t(
            is_en,
            "未发现实例状态记录（可能实例未运行或无权限）。",
            "No instance status records found (instances may be stopped, or permissions are insufficient).",
        )

    rows = []
    ok_system = 0
    ok_instance = 0
    for st in statuses[:20]:
        if not isinstance(st, dict):
            continue
        iid = str(st.get("InstanceId") or "-")
        state = str((st.get("InstanceState") or {}).get("Name") or "-")
        sys_status = str((st.get("SystemStatus") or {}).get("Status") or "-")
        ins_status = str((st.get("InstanceStatus") or {}).get("Status") or "-")
        az = str((st.get("AvailabilityZone") or "-"))
        if sys_status == "ok":
            ok_system += 1
        if ins_status == "ok":
            ok_instance += 1
        rows.append((iid, state, sys_status, ins_status, az))

    lines = [
        _t(is_en, f"已检查 **{len(rows)}** 台实例健康状态。", f"Checked health status for **{len(rows)}** instances."),
        _t(
            is_en,
            f"System Check OK: {ok_system}/{len(rows)}；Instance Check OK: {ok_instance}/{len(rows)}",
            f"System Check OK: {ok_system}/{len(rows)}; Instance Check OK: {ok_instance}/{len(rows)}",
        ),
        "",
        _t(is_en, "| 实例ID | 运行状态 | System Check | Instance Check | 可用区 |", "| Instance ID | State | System Check | Instance Check | AZ |"),
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
    return "\n".join(lines)


def _summarize_s3_buckets(body: Dict[str, Any], user_text: str = "") -> Optional[str]:
    is_en = _is_english_query(user_text)
    buckets = body.get("Buckets")
    if not isinstance(buckets, list):
        return None
    if not buckets:
        return _t(is_en, "当前账号下没有 S3 Bucket。", "No S3 buckets found under the current account.")
    lines = [
        _t(is_en, f"已找到 **{len(buckets)}** 个 S3 Bucket。", f"Found **{len(buckets)}** S3 buckets."),
        "",
        _t(is_en, "| Bucket | 创建时间 |", "| Bucket | Creation Time |"),
        "| --- | --- |",
    ]
    for b in buckets[:20]:
        if not isinstance(b, dict):
            continue
        lines.append(f"| {b.get('Name','-')} | {b.get('CreationDate','-')} |")
    return "\n".join(lines)


def _summarize_identity(body: Dict[str, Any], user_text: str = "") -> Optional[str]:
    is_en = _is_english_query(user_text)
    if "Account" not in body and "Arn" not in body:
        return None
    return (
        _t(is_en, "**当前 AWS 身份**\n", "**Current AWS Identity**\n")
        + 
        f"- Account: `{body.get('Account', '-')}`\n"
        f"- Arn: `{body.get('Arn', '-')}`\n"
        f"- UserId: `{body.get('UserId', '-')}`"
    )


def _summarize_service_list(body: Dict[str, Any], user_text: str = "") -> Optional[str]:
    is_en = _is_english_query(user_text)
    services = body.get("Services")
    if not isinstance(services, list):
        return None
    if not services:
        return _t(is_en, "未返回服务列表。", "No service list returned.")
    lines = [
        _t(is_en, f"已返回 **{len(services)}** 个服务条目。", f"Returned **{len(services)}** service entries."),
        "",
        _t(is_en, "| 服务代码 | 服务名 |", "| Service Code | Service Name |"),
        "| --- | --- |",
    ]
    for s in services[:25]:
        if not isinstance(s, dict):
            continue
        lines.append(f"| {s.get('ServiceCode','-')} | {s.get('ServiceName','-')} |")
    return "\n".join(lines)


def _summarize_call_aws_result(result: Dict[str, Any], user_text: str = "") -> Optional[str]:
    is_en = _is_english_query(user_text)
    combined = result.get("combined")
    if isinstance(combined, list) and combined:
        parts: List[str] = []
        label = _t(is_en, "命令", "Command")
        for item in combined:
            if not isinstance(item, dict):
                continue
            cli = str(item.get("cli_command") or "")
            sub = item.get("result") if isinstance(item.get("result"), dict) else {}
            section = _summarize_call_aws_result(sub, user_text)
            if section:
                parts.append(f"**{label}** `{cli}`\n{section}")
        if parts:
            return "\n\n".join(parts)

    # Plain-text error response path from call_aws
    content = result.get("content")
    if isinstance(content, list):
        for chunk in content:
            if not isinstance(chunk, dict):
                continue
            text = str(chunk.get("text") or "")
            if "Error calling tool 'call_aws':" in text:
                tail = text.split("Error calling tool 'call_aws':", 1)[-1].strip()
                return _format_error_with_suggestions(
                    title=_t(is_en, "AWS 命令执行失败", "AWS command execution failed"),
                    reason=_t(is_en, f"命令参数校验未通过。{tail[:400]}", f"Command validation failed. {tail[:400]}"),
                    suggestions=[
                        _t(is_en, "改成更明确的只读查询，例如“列出 ap-southeast-2 的 EC2 实例”。", "Use a more specific read-only request, for example: “List EC2 instances in ap-southeast-2”."),
                        _t(is_en, "如果你同意，我可以自动改用保守模板重试（实例列表/健康/成本总览）。", "I can retry with a conservative read-only template (instance list/health/cost summary)."),
                    ],
                    is_en=is_en,
                )

    parsed = _extract_call_aws_payload(result)
    if not parsed:
        return None

    response = parsed.get("response") or {}
    body = parsed.get("body") or {}
    err = response.get("error")
    if err:
        error_text = str(err)
        suggestions = [
            _t(is_en, "确认当前 profile 是否有目标服务的只读权限。", "Confirm the current profile has read-only permissions for the target service."),
            _t(is_en, "确认 region 是否正确（例如 ap-southeast-2）。", "Confirm region is correct (for example: ap-southeast-2)."),
            _t(is_en, "如果是成本查询，请确认已开通 Cost Explorer 且具备 ce:GetCostAndUsage 权限。", "For cost queries, confirm Cost Explorer is enabled and ce:GetCostAndUsage is granted."),
        ]
        if "AccessDenied" in error_text or "not authorized" in error_text.lower():
            suggestions = [
                _t(is_en, "当前是权限不足。请给该 profile 增加对应服务的只读权限。", "This is a permission issue. Grant read-only permissions for the target service to this profile."),
                _t(is_en, "成本场景请至少补齐 ce:GetCostAndUsage。", "For cost scenarios, grant at least ce:GetCostAndUsage."),
                _t(is_en, "权限补齐后重试同一句查询即可。", "After permissions are updated, retry the same query."),
            ]
        guidance = _build_permission_guidance(error_text, user_text)
        if guidance:
            suggestions.append(guidance)
        return _format_error_with_suggestions(
            title=_t(is_en, "AWS 查询失败", "AWS query failed"),
            reason=error_text[:500],
            suggestions=suggestions,
            is_en=is_en,
        )

    # Intent-aware summaries for common AWS shapes.
    for handler in (
        lambda: _summarize_identity(body, user_text),
        lambda: _summarize_cost_or_usage(body, user_text),
        lambda: _summarize_instance_status(body, user_text),
        lambda: _summarize_s3_buckets(body, user_text),
        lambda: _summarize_service_list(body, user_text),
    ):
        out = handler()
        if out:
            return out

    reservations = body.get("Reservations")
    if not isinstance(reservations, list):
        # Generic non-EC2 fallback
        keys = list(body.keys())[:8]
        return _t(is_en, "AWS 查询已完成，已返回结构化结果。\n关键字段: ", "AWS query completed with structured response.\nKey fields: ") + (", ".join(keys) if keys else _t(is_en, "无", "none"))

    instances: List[Dict[str, Any]] = []
    for reservation in reservations:
        if not isinstance(reservation, dict):
            continue
        for inst in reservation.get("Instances", []) or []:
            if isinstance(inst, dict):
                instances.append(inst)

    if not instances:
        return _t(is_en, "在该区域未发现 EC2 实例。", "No EC2 instances found in this region.")

    total = len(instances)
    state_counter = Counter(str((i.get("State") or {}).get("Name") or "unknown") for i in instances)
    type_counter = Counter(str(i.get("InstanceType") or "unknown") for i in instances)

    def _name_tag(i: Dict[str, Any]) -> str:
        tags = i.get("Tags") or []
        if not isinstance(tags, list):
            return "-"
        for tag in tags:
            if isinstance(tag, dict) and tag.get("Key") == "Name":
                return str(tag.get("Value") or "-")
        return "-"

    rows = []
    for i in instances[:15]:
        iid = str(i.get("InstanceId") or "-")
        itype = str(i.get("InstanceType") or "-")
        state = str((i.get("State") or {}).get("Name") or "-")
        az = str((i.get("Placement") or {}).get("AvailabilityZone") or "-")
        pub_ip = str(i.get("PublicIpAddress") or "-")
        rows.append((iid, itype, state, az, pub_ip, _name_tag(i)))

    summary_lines = [
        _t(is_en, f"已找到 **{total}** 台 EC2 实例。", f"Found **{total}** EC2 instances."),
        _t(is_en, "状态汇总: ", "State summary: ") + ", ".join(f"{k}={v}" for k, v in state_counter.most_common()),
        _t(is_en, "规格分布: ", "Instance type distribution: ") + ", ".join(f"{k}={v}" for k, v in type_counter.most_common(5)),
        "",
        _t(is_en, "| 实例ID | 规格 | 状态 | 可用区 | 公网IP | Name |", "| Instance ID | Type | State | AZ | Public IP | Name |"),
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        summary_lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |")
    if total > len(rows):
        summary_lines.append(_t(is_en, f"\n仅展示前 {len(rows)} 台，其余 {total - len(rows)} 台已省略。", f"\nShowing first {len(rows)} instances; {total - len(rows)} more omitted."))
    return "\n".join(summary_lines)


def try_handle_aws_via_mcp(user_text: str, session_context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    pending_action = _get_valid_pending_action(session_context)
    if not _is_aws_query(user_text) and pending_action is None:
        return None

    manager = MCPConfigManager()
    server = _find_enabled_aws_server(manager)
    if not server:
        return None

    if is_high_risk_aws_intent(user_text):
        return {
            "handled": True,
            "blocked": True,
            "message": (
                "Detected high-risk AWS write intent (create/update/delete/terminate). "
                "Chat direct execution is blocked by guardrails."
            ),
        }

    is_en = _resolve_language_is_en(user_text, pending_action)
    if pending_action:
        generic_intent = parse_intent(user_text)
        generic_route = RUNBOOK_ROUTER.route_pending(pending_action, generic_intent)
        if generic_route and generic_route.action == "probe_pending_status":
            refreshed = dict(pending_action)
            refreshed["expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            return {
                "handled": True,
                "blocked": False,
                "pending_action_set": refreshed,
                "message": _pending_status_probe_message(pending_action, is_en),
            }
    if pending_action and pending_action.get("type") == "await_iam_permission_grant":
        intent = parse_intent(user_text)
        route = RUNBOOK_ROUTER.route_pending(pending_action, intent)
        if _is_install_reject(user_text):
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _t(
                    is_en,
                    "好的，已取消权限补齐后的自动续跑。",
                    "Understood. Auto-resume after IAM permission grant has been cancelled.",
                ),
            }
        if route and route.action == "explain_waiting_permission":
            return {
                "handled": True,
                "blocked": False,
                "message": _t(
                    is_en,
                    "我还在等待 IAM 权限补齐确认。权限就绪后回复“继续”，我会自动从中断步骤续跑。",
                    "I am still waiting for IAM permission grant confirmation. Reply 'continue' once permissions are ready and I will auto-resume from the interrupted step.",
                ),
            }
        if route and route.action == "resume_after_permission_probe":
            resume_action = pending_action.get("resume_action")
            if not isinstance(resume_action, dict):
                return {
                    "handled": True,
                    "blocked": True,
                    "pending_action_clear": True,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "续跑上下文已失效", "Resume context expired"),
                        reason=_t(
                            is_en,
                            "找不到要恢复的执行步骤，请重新发起监控查询。",
                            "Cannot find the execution step to resume. Please rerun monitoring query.",
                        ),
                        suggestions=[
                            _t(
                                is_en,
                                "请重试：查看 i-xxxx 在 ap-southeast-2 最近30分钟监控。",
                                "Retry: check monitoring for i-xxxx in ap-southeast-2 for last 30 minutes.",
                            ),
                        ],
                        is_en=is_en,
                    ),
                }
            region = str(pending_action.get("region") or "").strip()
            instance_id = str(pending_action.get("instance_id") or "").strip()
            if region and instance_id:
                try:
                    adapter = AwsPlatformActions(server, region)
                    _, probe_err = _run_async(adapter.permission_probe_for_resume(instance_id, resume_action))
                except Exception as exc:
                    probe_err = str(exc)
                if probe_err and _is_unsupported_operation_error(probe_err):
                    return _build_unsupported_operation_response(
                        reason=probe_err,
                        is_en=is_en,
                        pending_action=pending_action,
                    )
                if probe_err and _is_bind_permission_denied(probe_err):
                    missing = _extract_missing_action(probe_err) or "iam:CreateRole"
                    principal = _extract_principal_arn(probe_err) or str(pending_action.get("principal_arn") or "")
                    account_id = _extract_account_id_from_arn(principal)
                    policy_json = _build_minimal_bind_policy_json(account_id)
                    return {
                        "handled": True,
                        "blocked": False,
                        "pending_action_clear": True,
                        "pending_action_set": {
                            **pending_action,
                            "missing_actions": [missing],
                            "principal_arn": principal,
                            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
                        },
                        "message": _format_error_with_suggestions(
                            title=_t(is_en, "权限仍未满足（快速探针）", "Permissions still insufficient (quick probe)"),
                            reason=probe_err[:500],
                            suggestions=[
                                _t(is_en, "继续补齐 IAM 权限后回复“继续”，我会自动续跑。", "Complete IAM permissions and reply 'continue' to auto-resume."),
                                _t(is_en, f"缺失动作: `{missing}`", f"Missing action: `{missing}`"),
                                _t(
                                    is_en,
                                    "操作位置: AWS Console -> IAM -> Users/Roles -> 选择当前身份 -> Add permissions -> Create inline policy -> JSON。",
                                    "Where to configure: AWS Console -> IAM -> Users/Roles -> select current identity -> Add permissions -> Create inline policy -> JSON.",
                                ),
                                _t(
                                    is_en,
                                    "可复制最小策略(JSON):\n```json\n" + policy_json + "\n```",
                                    "Copyable minimal policy (JSON):\n```json\n" + policy_json + "\n```",
                                ),
                            ],
                            is_en=is_en,
                        ),
                    }
            resumed = dict(resume_action)
            resumed.setdefault("region", str(pending_action.get("region") or ""))
            resumed.setdefault("instance_id", str(pending_action.get("instance_id") or ""))
            resumed["lang"] = "en" if is_en else "zh"
            resumed["expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "pending_action_set": resumed,
                "message": _t(
                    is_en,
                    "已收到。将按你刚完成的 IAM 授权继续执行自动修复流程（无需重复描述需求）。",
                    "Received. I will continue the auto-remediation flow with your newly granted IAM permissions (no need to restate your request).",
                ),
            }
        return {
            "handled": True,
            "blocked": False,
            "message": _t(
                is_en,
                "完成 IAM 授权后回复“继续”，我会从中断步骤自动续跑。",
                    "After IAM permissions are granted, reply 'continue' and I will resume from the interrupted step.",
                ),
            }

    if pending_action and pending_action.get("type") == "await_cwagent_metrics":
        intent = parse_intent(user_text)
        route = RUNBOOK_ROUTER.route_pending(pending_action, intent)
        region = str(pending_action.get("region") or "").strip()
        instance_id = str(pending_action.get("instance_id") or "").strip()
        window_minutes = int(pending_action.get("window_minutes") or 30)
        if _is_install_reject(user_text):
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _t(
                    is_en,
                    "好的，已取消 CWAgent 指标续拉。",
                    "Understood. CWAgent metrics follow-up has been cancelled.",
                ),
            }
        if route and route.action == "poll_cwagent_metrics":
            try:
                request_server = _build_server_config_with_region(server, region)
                client = MCPClient(request_server)

                async def _probe_metrics() -> Dict[str, Any]:
                    await client.connect()
                    try:
                        text = f"check ec2 {instance_id} monitoring in {region} for {window_minutes} minutes cpu memory disk"
                        payload = await _execute_monitoring_probe(client, text)
                        payload["region"] = region
                        return payload
                    finally:
                        await client.disconnect()

                probe_payload = _run_async(_probe_metrics())
            except Exception as exc:
                return {
                    "handled": True,
                    "blocked": False,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "CWAgent 指标续拉失败", "CWAgent metrics follow-up failed"),
                        reason=str(exc)[:500],
                        suggestions=[
                            _t(is_en, "稍后回复“继续”重试。", "Reply 'continue' later to retry."),
                        ],
                        is_en=is_en,
                    ),
                }
            has_metrics = _monitor_has_cwagent_metrics(probe_payload)
            if not has_metrics:
                return {
                    "handled": True,
                    "blocked": False,
                    "pending_action_clear": True,
                    "pending_action_set": {
                        "type": "await_cwagent_metrics",
                        "region": region,
                        "instance_id": instance_id,
                        "window_minutes": window_minutes,
                        "lang": "en" if is_en else "zh",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                    },
                    "message": _t(
                        is_en,
                        "CloudWatch Agent 已安装，但内存/磁盘指标首报通常需要 1-3 分钟。你稍后回复“继续”，我会再次拉取。",
                        "CloudWatch Agent is installed, but first memory/disk metrics usually arrive in 1-3 minutes. Reply 'continue' shortly and I will fetch again.",
                    ),
                }
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _summarize_result(probe_payload, user_text, is_en=is_en),
                "raw": probe_payload,
            }
        return {
            "handled": True,
            "blocked": False,
            "message": _t(
                is_en,
                "CWAgent 指标首报可能延迟 1-3 分钟。准备好后回复“继续”，我会再拉一次。",
                "CWAgent first metric delivery may take 1-3 minutes. Reply 'continue' when ready and I will fetch again.",
            ),
        }

    if pending_action and pending_action.get("type") == "await_instance_profile_choice":
        intent = parse_intent(user_text)
        route = RUNBOOK_ROUTER.route_pending(pending_action, intent)
        if _is_install_reject(user_text):
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _t(
                    is_en,
                    "好的，已取消实例角色/Instance Profile 绑定流程。",
                    "Understood. Instance role/profile binding flow has been cancelled.",
                ),
            }
        if route and route.action == "recheck_instance_profile":
            region = str(pending_action.get("region") or "").strip()
            instance_id = str(pending_action.get("instance_id") or "").strip()
            if not region or not instance_id:
                return {
                    "handled": True,
                    "blocked": True,
                    "pending_action_clear": True,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "续跑上下文已失效", "Resume context expired"),
                        reason=_t(
                            is_en,
                            "缺少实例或区域信息，请重新发起监控查询。",
                            "Missing instance or region context. Please rerun monitoring query.",
                        ),
                        suggestions=[
                            _t(is_en, "请重试：查看 i-xxxx 在 ap-southeast-2 最近30分钟监控。", "Retry: check monitoring for i-xxxx in ap-southeast-2 for last 30 minutes."),
                        ],
                        is_en=is_en,
                    ),
                }
            try:
                adapter = AwsPlatformActions(server, region)
                checked = _run_async(adapter.recheck_instance_profile_binding(instance_id))
            except Exception as exc:
                checked = {"ok": False, "error": str(exc)}
            if _is_unsupported_operation_error(str(checked.get("error") or "")):
                return _build_unsupported_operation_response(
                    reason=str(checked.get("error") or ""),
                    is_en=is_en,
                    pending_action=pending_action,
                )

            if checked.get("ok"):
                profile_name = str(checked.get("profile_name") or "").strip()
                return {
                    "handled": True,
                    "blocked": False,
                    "pending_action_clear": True,
                    "pending_action_set": {
                        "type": "bind_instance_profile",
                        "region": region,
                        "instance_id": instance_id,
                        "choice": {"kind": "profile", "name": profile_name},
                        "lang": "en" if is_en else "zh",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                    },
                    "message": _t(
                        is_en,
                        f"已检测到实例已绑定 Instance Profile `{profile_name}`。我将基于该 profile 继续自动修复并安装 Agent。请回复“继续”。",
                        f"Detected instance profile `{profile_name}` is now bound. I will continue remediation and agent installation based on this profile. Reply 'continue'.",
                    ),
                }
            return {
                "handled": True,
                "blocked": False,
                "message": _t(
                    is_en,
                    "我重新检查过，实例仍未绑定 IAM Role/Profile，这一步完成前还不能继续安装 CloudWatch Agent。你可以回复 Role 名称、Profile 名称，或“创建最小权限并绑定”。",
                    "I rechecked and the instance still has no IAM role/profile binding. Agent installation cannot continue before this step. Reply with a Role name, Profile name, or 'create minimal and bind'.",
                ),
            }
        if route and route.action == "explain_waiting_role_profile":
            return {
                "handled": True,
                "blocked": False,
                "message": _t(
                    is_en,
                    "我现在还卡在 IAM Role/Profile 绑定这一步，完成前不能继续安装 CloudWatch Agent。请回复 Role 名称、Profile 名称、或“创建最小权限并绑定”；如果你已在控制台处理完，直接回复“继续”。",
                    "We are still blocked on IAM role/profile binding. CloudWatch Agent installation cannot continue until this is done. Reply with a Role name, Profile name, or 'create minimal and bind'; if already done in console, reply 'continue'.",
                ),
            }
        choice = _extract_iam_choice(user_text)
        if not choice:
            return {
                "handled": True,
                "blocked": False,
                "message": _t(
                    is_en,
                    "我还在等待 IAM Role/Profile 信息。这一步还不能继续安装。请回复 Role 名称、Profile 名称、或“创建最小权限并绑定”；如果你已处理完，回复“继续”。",
                    "Still waiting for IAM role/profile input. Installation cannot continue yet. Reply with a Role name, Profile name, or 'create minimal and bind'; if already done, reply 'continue'.",
                ),
            }
        region = str(pending_action.get("region") or "").strip()
        instance_id = str(pending_action.get("instance_id") or "").strip()
        choice_text = (
            _t(is_en, "创建最小权限并绑定", "create minimal role/profile and bind")
            if choice.get("kind") == "create_minimal"
            else f"{choice.get('kind')}: {choice.get('name')}"
        )
        return {
            "handled": True,
            "blocked": False,
            "pending_action_set": {
                "type": "bind_instance_profile",
                "region": region,
                "instance_id": instance_id,
                "choice": choice,
                "lang": "en" if is_en else "zh",
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            },
            "message": _t(
                is_en,
                f"我将按 `{choice_text}` 绑定实例的 IAM 权限，然后自动执行：等待 SSM Online -> 安装 CloudWatch Agent -> 回拉监控。继续吗？（继续/取消）",
                f"I will use `{choice_text}` to bind IAM for this instance, then run: wait SSM online -> install CloudWatch Agent -> fetch monitoring again. Continue? (continue/cancel)",
            ),
        }

    if pending_action and pending_action.get("type") == "bind_instance_profile":
        if _is_install_reject(user_text):
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _t(
                    is_en,
                    "好的，已取消绑定与自动修复流程。",
                    "Understood. Binding and auto-remediation flow has been cancelled.",
                ),
            }
        if _is_install_confirmation(user_text):
            region = str(pending_action.get("region") or "").strip()
            instance_id = str(pending_action.get("instance_id") or "").strip()
            choice = pending_action.get("choice")
            if not region or not instance_id or not isinstance(choice, dict):
                return {
                    "handled": True,
                    "blocked": True,
                    "pending_action_clear": True,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "绑定上下文已失效", "Binding context expired"),
                        reason=_t(is_en, "缺少实例、区域或绑定目标。请重新发起监控查询。", "Missing instance, region, or binding target. Please rerun monitoring query."),
                        suggestions=[
                            _t(is_en, "请重试：查看 i-xxxx 在 ap-southeast-2 最近30分钟监控。", "Retry: check monitoring for i-xxxx in ap-southeast-2 for last 30 minutes."),
                        ],
                        is_en=is_en,
                    ),
                }
            try:
                request_server = _build_server_config_with_region(server, region)
                client = MCPClient(request_server)

                async def _bind_install_probe() -> Dict[str, Any]:
                    await client.connect()
                    try:
                        async def _bind() -> Dict[str, Any]:
                            return await _execute_bind_instance_profile_flow(client, instance_id, choice)

                        async def _install() -> Dict[str, Any]:
                            return await _execute_cwagent_install(client, instance_id)

                        async def _probe() -> Dict[str, Any]:
                            probe_text = f"check ec2 {instance_id} monitoring in {region} for 30 minutes cpu memory disk"
                            payload = await _execute_monitoring_probe(client, probe_text)
                            payload["region"] = region
                            return payload

                        return await execute_bind_install_probe_flow(
                            bind_fn=_bind,
                            install_fn=_install,
                            probe_fn=_probe,
                        )
                    finally:
                        await client.disconnect()

                flow = _run_async(_bind_install_probe())
            except Exception as exc:
                flow = {"ok": False, "stage": "bind_exception", "error": str(exc)}

            if not flow.get("ok"):
                err = str(flow.get("error") or "")
                if _is_unsupported_operation_error(err):
                    return _build_unsupported_operation_response(
                        reason=err,
                        is_en=is_en,
                        pending_action=pending_action,
                    )
                guidance = _build_permission_guidance(err, user_text)
                suggestions = [
                    _t(is_en, "我可以继续分步排查（IAM 绑定、SSM Online、Agent 安装），你回复“继续排查”。", "I can continue with step-by-step troubleshooting (IAM binding, SSM online, agent install). Reply 'continue troubleshooting'."),
                ]
                if "NoSuchEntity" in err and "GetRole" in err:
                    suggestions.insert(
                        0,
                        _t(
                            is_en,
                            "未找到该 Role。你可以直接回复“创建最小权限并绑定”，我会创建并绑定最小权限 Role/Profile 后重试。",
                            "Role not found. Reply 'create minimal and bind' and I will create a least-privilege role/profile, bind it, and retry.",
                        ),
                    )
                    suggestions.append(
                        _t(
                            is_en,
                            "手工操作位置: AWS Console -> IAM -> Roles -> Create role（EC2 信任实体），附加 AmazonSSMManagedInstanceCore 与 CloudWatchAgentServerPolicy。",
                            "Manual path: AWS Console -> IAM -> Roles -> Create role (trusted entity: EC2), attach AmazonSSMManagedInstanceCore and CloudWatchAgentServerPolicy.",
                        )
                    )
                if guidance:
                    suggestions.append(guidance)
                pending_set = None
                if _is_bind_permission_denied(err):
                    principal = _extract_principal_arn(err) or ""
                    account_id = _extract_account_id_from_arn(principal)
                    missing = _extract_missing_action(err) or "iam:CreateRole"
                    policy_json = _build_minimal_bind_policy_json(account_id)
                    suggestions.insert(
                        0,
                        _t(
                            is_en,
                            "你只需要补一次 IAM 权限，然后回复“继续”，我会从当前步骤自动续跑。",
                            "You only need to grant IAM permissions once; then reply 'continue' and I will auto-resume from this step.",
                        ),
                    )
                    if principal:
                        suggestions.append(
                            _t(
                                is_en,
                                f"当前身份: `{principal}`",
                                f"Current identity: `{principal}`",
                            )
                        )
                    suggestions.append(
                        _t(
                            is_en,
                            f"缺失动作: `{missing}`",
                            f"Missing action: `{missing}`",
                        )
                    )
                    suggestions.append(
                        _t(
                            is_en,
                            "操作位置: AWS Console -> IAM -> Users/Roles -> 选择当前身份 -> Add permissions -> Create inline policy -> JSON。",
                            "Where to configure: AWS Console -> IAM -> Users/Roles -> select current identity -> Add permissions -> Create inline policy -> JSON.",
                        )
                    )
                    suggestions.append(
                        _t(
                            is_en,
                            "可复制最小策略(JSON):\n```json\n" + policy_json + "\n```",
                            "Copyable minimal policy (JSON):\n```json\n" + policy_json + "\n```",
                        )
                    )
                    pending_set = {
                        "type": "await_iam_permission_grant",
                        "region": region,
                        "instance_id": instance_id,
                        "lang": "en" if is_en else "zh",
                        "principal_arn": principal,
                        "missing_actions": [missing],
                        "resume_action": {
                            "type": "bind_instance_profile",
                            "choice": choice,
                        },
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
                    }
                return {
                    "handled": True,
                    "blocked": False,
                    "pending_action_clear": True,
                    "pending_action_set": pending_set,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "自动绑定/安装未完成", "Auto binding/installation not completed"),
                        reason=err[:500] or _t(is_en, "未知错误", "Unknown error"),
                        suggestions=suggestions,
                        is_en=is_en,
                    ),
                }

            probe_payload = flow.get("probe") if isinstance(flow.get("probe"), dict) else {}
            bind_payload = flow.get("bind") if isinstance(flow.get("bind"), dict) else {}
            has_metrics = _monitor_has_cwagent_metrics(probe_payload)
            summary = _summarize_result(probe_payload, user_text, is_en=is_en)
            if not has_metrics:
                summary = _t(
                    is_en,
                    "CloudWatch Agent 已安装，内存/磁盘指标首报通常需要 1-3 分钟。你回复“继续”，我会再次拉取并给出监控结果。\n\n",
                    "CloudWatch Agent is installed; first memory/disk metrics usually arrive in 1-3 minutes. Reply 'continue' and I will fetch monitoring again.\n\n",
                ) + summary
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "pending_action_set": (
                    {
                        "type": "await_cwagent_metrics",
                        "region": region,
                        "instance_id": instance_id,
                        "window_minutes": 30,
                        "lang": "en" if is_en else "zh",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                    }
                    if not has_metrics
                    else None
                ),
                "message": (
                    _extract_bind_change_summary(bind_payload, is_en)
                    + "\n\n"
                    + _t(
                        is_en,
                        "实例 IAM 绑定、SSM 接管与 CloudWatch Agent 安装已完成，我已重新拉取监控数据：\n\n",
                        "Instance IAM binding, SSM takeover, and CloudWatch Agent installation are complete. Refreshed monitoring data:\n\n",
                    )
                    + summary
                ),
                "raw": probe_payload,
            }

    if pending_action and pending_action.get("type") == "remediate_ssm_prereq":
        if _is_install_reject(user_text):
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _t(
                    is_en,
                    "好的，已取消自动修复 SSM 接管前置条件。",
                    "Understood. SSM prerequisite auto-remediation has been cancelled.",
                ),
            }
        if _is_install_confirmation(user_text):
            region = str(pending_action.get("region") or "").strip()
            instance_id = str(pending_action.get("instance_id") or "").strip()
            if not region or not instance_id:
                return {
                    "handled": True,
                    "blocked": True,
                    "pending_action_clear": True,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "修复上下文已失效", "Remediation context expired"),
                        reason=_t(
                            is_en,
                            "缺少实例或区域上下文，请重新发起监控查询。",
                            "Missing instance or region context. Please run monitoring query again.",
                        ),
                        suggestions=[
                            _t(is_en, "请重试：查看 i-xxxx 在 ap-southeast-2 最近30分钟监控。", "Retry: check monitoring for i-xxxx in ap-southeast-2 for last 30 minutes."),
                        ],
                        is_en=is_en,
                    ),
                }
            try:
                request_server = _build_server_config_with_region(server, region)
                client = MCPClient(request_server)

                async def _remediate_then_install() -> Dict[str, Any]:
                    await client.connect()
                    try:
                        async def _remediate() -> Dict[str, Any]:
                            return await _execute_ssm_prereq_remediation(client, instance_id)

                        async def _install() -> Dict[str, Any]:
                            return await _execute_cwagent_install(client, instance_id)

                        async def _probe() -> Dict[str, Any]:
                            probe_text = f"check ec2 {instance_id} monitoring in {region} for 30 minutes cpu memory disk"
                            payload = await _execute_monitoring_probe(client, probe_text)
                            payload["region"] = region
                            return payload

                        return await execute_remediate_install_probe_flow(
                            remediate_fn=_remediate,
                            install_fn=_install,
                            probe_fn=_probe,
                        )
                    finally:
                        await client.disconnect()

                flow_payload = _run_async(_remediate_then_install())
            except Exception as exc:
                flow_payload = {"ok": False, "stage": "remediation_exception", "error": str(exc)}

            if not flow_payload.get("ok"):
                err = str(flow_payload.get("error") or "")
                if _is_unsupported_operation_error(err):
                    return _build_unsupported_operation_response(
                        reason=err,
                        is_en=is_en,
                        pending_action=pending_action,
                    )
                stage = str(flow_payload.get("stage") or "")
                guidance = _build_permission_guidance(err, user_text)
                suggestions = [
                    _t(is_en, "我可以继续做网络连通与 SSM Agent 状态诊断，你回复“继续排查”即可。", "I can continue with network and SSM Agent diagnostics; reply 'continue troubleshooting'."),
                    _t(is_en, "如果你希望手工确认，也可在 Systems Manager -> Managed nodes 查看实例是否 Online。", "If you prefer manual verification, check Systems Manager -> Managed nodes for Online status."),
                ]
                if stage == "instance_profile_missing":
                    suggestions.insert(
                        0,
                        _t(
                            is_en,
                            "这台实例目前没有绑定 IAM Instance Profile。你可以直接回复现有 profile 名称或 role 名称，我可以继续代你完成绑定与后续安装。",
                            "This instance currently has no IAM Instance Profile. Reply with an existing profile name or role name, and I can continue the binding and installation for you.",
                        ),
                    )
                if guidance:
                    suggestions.append(guidance)
                return {
                    "handled": True,
                    "blocked": False,
                    "pending_action_clear": True,
                    "pending_action_set": (
                        {
                            "type": "await_instance_profile_choice",
                            "region": region,
                            "instance_id": instance_id,
                            "lang": "en" if is_en else "zh",
                            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                        }
                        if stage == "instance_profile_missing"
                        else None
                    ),
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "自动修复未完成", "Auto-remediation not completed"),
                        reason=err[:500] or _t(is_en, "未知错误", "Unknown error"),
                        suggestions=suggestions,
                        is_en=is_en,
                    ),
                }

            probe_payload = flow_payload.get("probe") if isinstance(flow_payload.get("probe"), dict) else {}
            has_metrics = _monitor_has_cwagent_metrics(probe_payload)
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "pending_action_set": (
                    {
                        "type": "await_cwagent_metrics",
                        "region": region,
                        "instance_id": instance_id,
                        "window_minutes": 30,
                        "lang": "en" if is_en else "zh",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                    }
                    if not has_metrics
                    else None
                ),
                "message": _t(
                    is_en,
                    "SSM 前置条件修复与 CloudWatch Agent 安装已完成，我已重新拉取监控数据：\n\n",
                    "SSM prerequisites remediation and CloudWatch Agent installation are complete. Refreshed monitoring data:\n\n",
                ) + (
                    _t(
                        is_en,
                        "CloudWatch Agent 指标首报通常需要 1-3 分钟。你回复“继续”，我会再次拉取。\n\n",
                        "CloudWatch Agent first metrics usually take 1-3 minutes. Reply 'continue' and I will fetch again.\n\n",
                    )
                    if not has_metrics
                    else ""
                ) + _summarize_result(probe_payload, user_text, is_en=is_en),
                "raw": probe_payload,
            }

    if pending_action and pending_action.get("type") == "install_cwagent":
        if _is_install_reject(user_text):
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "message": _t(
                    is_en,
                    "好的，已取消本次 CloudWatch Agent 安装流程。",
                    "Understood. CloudWatch Agent installation has been cancelled.",
                ),
            }
        if _is_install_confirmation(user_text):
            region = str(pending_action.get("region") or "").strip()
            instance_id = str(pending_action.get("instance_id") or "").strip()
            if not region or not instance_id:
                return {
                    "handled": True,
                    "blocked": True,
                    "pending_action_clear": True,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "安装上下文已失效", "Installation context expired"),
                        reason=_t(is_en, "缺少实例或区域上下文，请重新发起监控查询。", "Missing instance or region context. Please run monitoring query again."),
                        suggestions=[
                            _t(is_en, "请重试：查看 i-xxxx 在 ap-southeast-2 最近30分钟监控。", "Retry: check monitoring for i-xxxx in ap-southeast-2 for last 30 minutes."),
                        ],
                        is_en=is_en,
                    ),
                }
            try:
                request_server = _build_server_config_with_region(server, region)
                client = MCPClient(request_server)
                async def _install_and_probe() -> Dict[str, Any]:
                    await client.connect()
                    try:
                        async def _install() -> Dict[str, Any]:
                            return await _execute_cwagent_install(client, instance_id)

                        async def _probe() -> Dict[str, Any]:
                            probe_text = f"check ec2 {instance_id} monitoring in {region} for 30 minutes cpu memory disk"
                            payload = await _execute_monitoring_probe(client, probe_text)
                            payload["region"] = region
                            return payload

                        return await execute_install_probe_flow(
                            install_fn=_install,
                            probe_fn=_probe,
                        )
                    finally:
                        await client.disconnect()

                install_payload = _run_async(_install_and_probe())
            except Exception as exc:
                install_payload = {"ok": False, "error": str(exc), "stage": "install_exception"}

            if not install_payload.get("ok"):
                err = str(install_payload.get("error") or "")
                if _is_unsupported_operation_error(err):
                    return _build_unsupported_operation_response(
                        reason=err,
                        is_en=is_en,
                        pending_action=pending_action,
                    )
                guidance = _build_permission_guidance(err, user_text)
                category = _ssm_error_category(err)
                suggestions = [
                    _t(is_en, "确认实例已接入 SSM（Managed Instance 在线）。", "Confirm the instance is managed by SSM and online."),
                    _t(is_en, "确认当前身份有 ssm:SendCommand 与 ssm:GetCommandInvocation。", "Confirm current identity has ssm:SendCommand and ssm:GetCommandInvocation."),
                ]
                if guidance:
                    suggestions.append(guidance)
                pending_set = None
                if category in {"ssm_target_not_managed", "ssm_target_not_connected"}:
                    pending_set = {
                        "type": "remediate_ssm_prereq",
                        "region": region,
                        "instance_id": instance_id,
                        "lang": "en" if is_en else "zh",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
                    }
                    suggestions.insert(
                        0,
                        _t(
                            is_en,
                            "如果你同意，我可以自动修复 SSM 接管前置条件（检查实例角色、补 AmazonSSMManagedInstanceCore、等待 Managed node Online）并重试安装。回复“继续修复”。",
                            "If you agree, I can auto-remediate SSM prerequisites (check instance role, attach AmazonSSMManagedInstanceCore, wait for managed node online) and retry installation. Reply 'continue remediation'.",
                        ),
                    )
                return {
                    "handled": True,
                    "blocked": False,
                    "pending_action_clear": True,
                    "pending_action_set": pending_set,
                    "message": _format_error_with_suggestions(
                        title=_t(is_en, "CloudWatch Agent 安装失败", "CloudWatch Agent installation failed"),
                        reason=err[:500] or _t(is_en, "未知错误", "Unknown error"),
                        suggestions=suggestions,
                        is_en=is_en,
                    ),
                }

            probe_payload = install_payload.get("probe") if isinstance(install_payload.get("probe"), dict) else {}
            has_metrics = _monitor_has_cwagent_metrics(probe_payload)
            message = _t(
                is_en,
                "CloudWatch Agent 安装与启用已完成，我已重新拉取监控数据：\n\n",
                "CloudWatch Agent installation and enablement completed. I refreshed monitoring data:\n\n",
            ) + (
                _t(
                    is_en,
                    "CloudWatch Agent 指标首报通常需要 1-3 分钟。你回复“继续”，我会再次拉取。\n\n",
                    "CloudWatch Agent first metrics usually take 1-3 minutes. Reply 'continue' and I will fetch again.\n\n",
                )
                if not has_metrics
                else ""
            ) + _summarize_result(probe_payload, user_text, is_en=is_en)
            return {
                "handled": True,
                "blocked": False,
                "pending_action_clear": True,
                "pending_action_set": (
                    {
                        "type": "await_cwagent_metrics",
                        "region": region,
                        "instance_id": instance_id,
                        "window_minutes": int(pending_action.get("window_minutes") or 30),
                        "lang": "en" if is_en else "zh",
                        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                    }
                    if not has_metrics
                    else None
                ),
                "message": message,
                "raw": probe_payload,
            }

    inferred_region = _extract_region(user_text)
    if not inferred_region:
        return {
            "handled": True,
            "blocked": True,
            "needs_region": True,
            "message": (
                _t(
                    is_en,
                    "我需要先确认目标 AWS 区域后才能执行操作。请提供区域代码（例如 `ap-southeast-2`）"
                    "或区域地点（例如 `Sydney` / `悉尼`）。",
                    "I need a target AWS region before executing any AWS operation. "
                    "Please specify region code (for example `ap-southeast-2`) "
                    "or location (for example `Sydney`).",
                )
            ),
        }

    try:
        request_server, inferred_region = _build_request_server_config(server, user_text)
        payload = _run_async(_call_server_async(request_server, user_text))
        if inferred_region:
            payload["region"] = inferred_region
    except Exception as exc:
        message = str(exc)
        if _is_unsupported_operation_error(message):
            return _build_unsupported_operation_response(
                reason=message,
                is_en=is_en,
                pending_action=pending_action,
            )
        suggestions = [
            _t(is_en, "确认 AWS MCP 服务端可启动（当前推荐命令为 `uvx awslabs.aws-api-mcp-server@latest`）。", "Confirm AWS MCP server can start (recommended command: `uvx awslabs.aws-api-mcp-server@latest`)."),
            _t(is_en, "确认本机可执行 `aws --version` 且 profile 存在。", "Confirm `aws --version` works locally and the profile exists."),
            _t(is_en, "稍后重试，若持续失败请查看 MCP 服务日志。", "Retry later; if it still fails, check MCP server logs."),
        ]
        if "timed out" in message.lower():
            suggestions = [
                _t(is_en, "初始化超时，通常是网络或首次拉取依赖较慢导致。", "Initialization timed out, often due to network or slow first-time dependency fetch."),
                _t(is_en, "先在终端手动执行一次 `uvx awslabs.aws-api-mcp-server@latest --help` 预热。", "Warm up once in terminal: `uvx awslabs.aws-api-mcp-server@latest --help`."),
                _t(is_en, "确认代理/网络后重试。", "Verify proxy/network and retry."),
            ]
        elif "No such file or directory" in message and "aws-mcp" in message:
            suggestions = [
                _t(is_en, "这是旧命令 `aws-mcp` 不存在导致。", "Legacy command `aws-mcp` is missing."),
                _t(is_en, "将 server 命令切换到 `uvx awslabs.aws-api-mcp-server@latest`。", "Switch server command to `uvx awslabs.aws-api-mcp-server@latest`."),
                _t(is_en, "重新执行 preflight 后再启用。", "Run preflight again, then enable."),
            ]
        return {
            "handled": True,
            "blocked": False,
            "message": _format_error_with_suggestions(
                title=_t(is_en, "AWS MCP 调用失败", "AWS MCP invocation failed"),
                reason=message[:500],
                suggestions=suggestions,
                is_en=is_en,
            ),
        }

    return {
        "handled": True,
        "blocked": False,
        "message": _summarize_result(payload, user_text, is_en=is_en),
        "raw": payload,
        "pending_action_set": (
            {
                "type": "install_cwagent",
                "region": str(payload.get("region") or inferred_region or ""),
                "instance_id": str(payload.get("instance_id") or ""),
                "window_minutes": int(payload.get("window_minutes") or 30),
                "lang": "en" if is_en else "zh",
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
            }
            if payload.get("mode") == "monitor_probe"
            and isinstance(payload.get("monitoring"), dict)
            and not (
                bool((payload.get("monitoring") or {}).get("has_cwagent_memory"))
                or bool((payload.get("monitoring") or {}).get("has_cwagent_disk"))
            )
            else None
        ),
        "pending_action_clear": (
            payload.get("mode") == "monitor_probe"
            and isinstance(payload.get("monitoring"), dict)
            and (
                bool((payload.get("monitoring") or {}).get("has_cwagent_memory"))
                or bool((payload.get("monitoring") or {}).get("has_cwagent_disk"))
            )
        ),
    }


def _format_error_with_suggestions(title: str, reason: str, suggestions: List[str], is_en: Optional[bool] = None) -> str:
    if is_en is None:
        is_en = _is_english_query(f"{title} {reason}")
    lines = [f"**{title}**", "", f"{_t(is_en, '原因', 'Reason')}: {reason}", "", f"{_t(is_en, '建议', 'Suggestions')}:"]
    for idx, suggestion in enumerate(suggestions, start=1):
        lines.append(f"{idx}. {suggestion}")
    return "\n".join(lines)
