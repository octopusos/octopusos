from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def ops_report_schema_v1() -> Dict[str, Any]:
    return {
        "schema_version": "opsreport.v1",
        "required": [
            "schema_version",
            "report_id",
            "generated_at",
            "scope",
            "time_window",
            "source",
            "summary",
            "sections",
            "verdict",
        ],
    }


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _parse_ts(v: str) -> Optional[datetime]:
    if not v:
        return None
    try:
        if v.endswith("Z"):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = max(0, min(len(sorted_vals) - 1, math.ceil(0.95 * len(sorted_vals)) - 1))
    return float(sorted_vals[idx])


def _extract_response_body(result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(result, dict):
        return None
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
        if not isinstance(response, dict):
            continue
        if response.get("error"):
            return None
        json_str = response.get("json")
        if isinstance(json_str, str) and json_str.strip():
            try:
                body = json.loads(json_str)
            except Exception:
                continue
            if isinstance(body, dict):
                return body
    return None


def _metric_series_from_call_aws_result(result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    body = _extract_response_body(result)
    if not isinstance(body, dict):
        return []
    datapoints = body.get("Datapoints")
    if not isinstance(datapoints, list):
        return []
    rows: List[Tuple[str, float]] = []
    for dp in datapoints:
        if not isinstance(dp, dict):
            continue
        ts_raw = str(dp.get("Timestamp") or "").strip()
        ts = _parse_ts(ts_raw)
        if not ts:
            continue
        # Prefer Average for trend rendering; fallback to Maximum.
        val = _safe_float(dp.get("Average"))
        if val is None:
            val = _safe_float(dp.get("Maximum"))
        if val is None:
            continue
        rows.append((ts.isoformat(), float(val)))
    rows.sort(key=lambda x: x[0])
    return [{"t": t, "v": v} for t, v in rows]


def _metric_stats_from_series(series: List[Dict[str, Any]]) -> Dict[str, float]:
    values = [float(p["v"]) for p in series if isinstance(p, dict) and p.get("v") is not None]
    if not values:
        return {"avg": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0, "last": 0.0}
    return {
        "avg": float(sum(values) / len(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "p95": float(_p95(values)),
        "last": float(values[-1]),
    }


def _metric_status(stats: Dict[str, float], warn: float, crit: float, unknown: bool) -> str:
    if unknown:
        return "unknown"
    max_v = float(stats.get("max", 0.0))
    if max_v >= crit:
        return "alert"
    if max_v >= warn:
        return "warn"
    return "ok"


def _status_to_severity(status: str) -> str:
    return {
        "ok": "info",
        "warn": "medium",
        "alert": "high",
        "unknown": "low",
    }.get(status, "unknown")


def _severity_rank(severity: str) -> int:
    return {
        "info": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
        "unknown": 0,
    }.get(severity, 0)


def _build_section(
    *,
    section_id: str,
    title: str,
    metric_name: str,
    display_name: str,
    unit: str,
    series: List[Dict[str, Any]],
    warn: float,
    crit: float,
    unknown: bool,
    analysis: str,
    interpretation: str,
) -> Dict[str, Any]:
    stats = _metric_stats_from_series(series)
    status = _metric_status(stats, warn, crit, unknown)
    return {
        "id": section_id,
        "title": title,
        "kind": "metric",
        "metrics": [
            {
                "name": metric_name,
                "display_name": display_name,
                "unit": unit,
                "series": series,
                "stats": stats,
                "thresholds": [
                    {"name": "warn", "operator": ">=", "value": warn, "severity": "medium"},
                    {"name": "crit", "operator": ">=", "value": crit, "severity": "high"},
                ],
                "chart": {
                    "type": "line" if section_id != "memory" else "area",
                    "show_avg_line": True,
                    "show_p95_line": True if section_id == "compute" else False,
                    "annotate_peaks": True,
                    "y_domain": [0, 100],
                },
            }
        ],
        "insight": {
            "status": status,
            "analysis": analysis,
            "interpretation": interpretation,
            "notable_events": [],
        },
    }


def build_ops_report_from_monitoring(
    *,
    payload: Dict[str, Any],
    is_en: bool,
) -> Dict[str, Any]:
    monitoring = payload.get("monitoring") if isinstance(payload.get("monitoring"), dict) else {}
    instance_id = str(payload.get("instance_id") or "-")
    region = str(payload.get("region") or "")
    window_minutes = int(payload.get("window_minutes") or 30)

    cpu_series = _metric_series_from_call_aws_result(monitoring.get("cpu"))
    mem_series = _metric_series_from_call_aws_result(monitoring.get("memory"))
    disk_series = _metric_series_from_call_aws_result(monitoring.get("disk"))

    has_mem = bool(monitoring.get("has_cwagent_memory")) and bool(mem_series)
    has_disk = bool(monitoring.get("has_cwagent_disk")) and bool(disk_series)
    disk_all_zero = bool(disk_series) and all(abs(float(p.get("v", 0.0))) < 1e-9 for p in disk_series)

    cpu_section = _build_section(
        section_id="compute",
        title="Compute",
        metric_name="CPUUtilization",
        display_name="CPU Usage",
        unit="%",
        series=cpu_series,
        warn=70.0,
        crit=90.0,
        unknown=not bool(cpu_series),
        analysis=(
            "CPU stayed low with no sustained pressure."
            if is_en
            else "CPU 整体处于低负载区间，未见持续性压力。"
        ),
        interpretation=(
            "Compute capacity is sufficient."
            if is_en
            else "计算资源充足，暂无性能瓶颈迹象。"
        ),
    )

    memory_unknown = not has_mem
    memory_section = _build_section(
        section_id="memory",
        title="Memory",
        metric_name="mem_used_percent",
        display_name="Memory Used",
        unit="%",
        series=mem_series if has_mem else [],
        warn=70.0,
        crit=90.0,
        unknown=memory_unknown,
        analysis=(
            "Memory usage remained stable without upward drift."
            if is_en
            else "内存使用率整体稳定，未见持续上升趋势。"
        ),
        interpretation=(
            "No memory pressure detected."
            if is_en
            else "未检测到内存压力。"
        ),
    )

    disk_unknown = (not has_disk) or disk_all_zero
    disk_section = _build_section(
        section_id="storage",
        title="Disk",
        metric_name="disk_used_percent",
        display_name="Disk Used",
        unit="%",
        series=disk_series if has_disk else [],
        warn=80.0,
        crit=90.0,
        unknown=disk_unknown,
        analysis=(
            "Disk metric is missing or flat at zero."
            if is_en
            else "磁盘指标缺失或长期为 0。"
        ),
        interpretation=(
            "Likely telemetry gap (CWAgent disk config/mountpoint dimensions)."
            if is_en
            else "更可能是观测配置缺口（CWAgent 磁盘配置/挂载点维度）。"
        ),
    )

    sections = [cpu_section, memory_section, disk_section]
    severities = [_status_to_severity(s.get("insight", {}).get("status", "unknown")) for s in sections]
    severity = max(severities, key=_severity_rank)

    confidence = 0.9
    unknown_count = sum(1 for s in sections if s.get("insight", {}).get("status") == "unknown")
    confidence -= 0.1 * unknown_count
    for s in sections:
        points = len((s.get("metrics") or [{}])[0].get("series") or [])
        if points and points < 5:
            confidence -= 0.1
    confidence = max(0.2, min(0.99, confidence))

    actions: List[Dict[str, Any]] = []
    if disk_unknown:
        actions.append(
            {
                "id": "act_disk_telemetry",
                "title": (
                    "Confirm CWAgent disk telemetry and mountpoint dimensions"
                    if is_en
                    else "确认 CWAgent 磁盘指标与挂载点维度配置"
                ),
                "priority": "p2",
                "type": "configure",
                "why": (
                    "disk_used_percent is missing/invalid; storage observability is incomplete."
                    if is_en
                    else "disk_used_percent 缺失或无效，存储可观测性不完整。"
                ),
                "how": (
                    "Check CloudWatch Agent config and ensure disk metrics are enabled for target mountpoints."
                    if is_en
                    else "检查 CloudWatch Agent 配置，确认已对目标挂载点上报 disk 指标。"
                ),
            }
        )

    action_required = severity in {"medium", "high", "critical"}
    if not actions and action_required:
        actions.append(
            {
                "id": "act_investigate_utilization",
                "title": "Investigate high utilization" if is_en else "排查高利用率原因",
                "priority": "p1",
                "type": "investigate",
                "why": "One or more metrics reached warning/critical thresholds."
                if is_en
                else "有指标达到告警阈值。",
                "how": "Inspect workload spikes, throttling, and recent deployment changes."
                if is_en
                else "检查负载尖峰、限流与近期发布变更。",
            }
        )

    headline = (
        "Instance is healthy: CPU/memory are stable."
        if is_en
        else "实例整体健康：CPU/内存稳定。"
    )
    if disk_unknown:
        headline += (
            " Disk telemetry appears incomplete."
            if is_en
            else " 但磁盘观测数据疑似不完整。"
        )

    now_iso = datetime.now().astimezone().isoformat()
    report = {
        "schema_version": "opsreport.v1",
        "report_id": f"opsrpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{instance_id}",
        "generated_at": now_iso,
        "scope": {
            "provider": "aws",
            "service": "ec2",
            "region": region,
            "resource": {"type": "instance", "id": instance_id},
        },
        "time_window": {
            "duration_minutes": window_minutes,
            "start": "",
            "end": "",
            "timezone": datetime.now().astimezone().tzname() or "UTC",
        },
        "source": {
            "collector": "aws-mcp",
            "system": "CloudWatch",
            "details": {"period_seconds": 300, "namespace_hint": "AWS/EC2 + CWAgent"},
        },
        "summary": {
            "headline": headline,
            "status": "healthy" if severity in {"info", "low"} else "watch",
            "highlights": [
                (
                    "CPU is low and stable."
                    if is_en
                    else "CPU 处于低负载且稳定。"
                ),
                (
                    "Memory has headroom."
                    if is_en
                    else "内存有充足余量。"
                ),
                (
                    "Disk telemetry needs verification."
                    if is_en
                    else "磁盘观测数据需校验。"
                )
                if disk_unknown
                else (
                    "Disk telemetry is available."
                    if is_en
                    else "磁盘观测数据已可用。"
                ),
            ],
        },
        "sections": sections,
        "verdict": {
            "severity": severity,
            "confidence": round(confidence, 2),
            "action_required": action_required,
            "recommended_actions": actions,
            "explanations": [
                (
                    "CPU and memory show no sustained pressure."
                    if is_en
                    else "CPU 与内存未出现持续性压力。"
                ),
                (
                    "Disk metric requires telemetry verification."
                    if is_en
                    else "磁盘指标需要做观测配置校验。"
                )
                if disk_unknown
                else (
                    "Disk metric trend is available."
                    if is_en
                    else "磁盘指标趋势已可用。"
                ),
            ],
        },
    }
    return report


def render_ops_report_markdown(report: Dict[str, Any], *, is_en: bool) -> str:
    scope = report.get("scope") if isinstance(report.get("scope"), dict) else {}
    resource = scope.get("resource") if isinstance(scope.get("resource"), dict) else {}
    time_window = report.get("time_window") if isinstance(report.get("time_window"), dict) else {}
    verdict = report.get("verdict") if isinstance(report.get("verdict"), dict) else {}
    sections = report.get("sections") if isinstance(report.get("sections"), list) else []

    lines = [
        ("**EC2 Instance Ops Report (Last Window)**" if is_en else "**EC2 实例运行状态报告（最近窗口）**"),
        (
            f"{'Instance' if is_en else '实例'}: `{resource.get('id', '-')}`  "
            f"{'Region' if is_en else '区域'}: `{scope.get('region', '-')}`  "
            f"{'Duration' if is_en else '时长'}: `{time_window.get('duration_minutes', '-')}{'m' if is_en else '分钟'}`"
        ),
        "",
        ("**Metric Trend Overview**" if is_en else "**指标趋势概览**"),
        ("| Metric | Avg | Max | P95 | Last |" if is_en else "| 指标 | 平均 | 峰值 | P95 | 最新值 |"),
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    for section in sections:
        metrics = section.get("metrics") if isinstance(section.get("metrics"), list) else []
        if not metrics:
            continue
        m = metrics[0] if isinstance(metrics[0], dict) else {}
        stats = m.get("stats") if isinstance(m.get("stats"), dict) else {}
        name = str(m.get("display_name") or m.get("name") or section.get("title") or "-")
        lines.append(
            f"| {name} | {float(stats.get('avg', 0.0)):.2f}% | {float(stats.get('max', 0.0)):.2f}% | {float(stats.get('p95', 0.0)):.2f}% | {float(stats.get('last', 0.0)):.2f}% |"
        )

    lines.extend(
        [
            "",
            ("**Insights & Interpretation**" if is_en else "**指标解读与分析**"),
        ]
    )
    for section in sections:
        title = str(section.get("title") or "-")
        insight = section.get("insight") if isinstance(section.get("insight"), dict) else {}
        status = str(insight.get("status") or "unknown")
        analysis = str(insight.get("analysis") or "")
        interpretation = str(insight.get("interpretation") or "")
        lines.append(f"- **{title}** [{status}]")
        if analysis:
            lines.append(f"  - {analysis}")
        if interpretation:
            lines.append(f"  - {interpretation}")

    sev = str(verdict.get("severity") or "unknown")
    conf = float(verdict.get("confidence", 0.0))
    action_required = bool(verdict.get("action_required"))
    lines.extend(
        [
            "",
            ("**Overall Verdict**" if is_en else "**综合健康判断**"),
            (
                f"- {'Severity' if is_en else '风险等级'}: `{sev}`"
                f"  {'Confidence' if is_en else '置信度'}: `{conf:.2f}`"
            ),
            (
                f"- {'Action required' if is_en else '是否需要动作'}: "
                f"{'Yes' if action_required and is_en else 'No' if is_en else '是' if action_required else '否'}"
            ),
        ]
    )

    actions = verdict.get("recommended_actions") if isinstance(verdict.get("recommended_actions"), list) else []
    if actions:
        lines.append("")
        lines.append("**Recommendations**" if is_en else "**建议与下一步**")
        for idx, action in enumerate(actions, start=1):
            if not isinstance(action, dict):
                continue
            title = str(action.get("title") or "-")
            why = str(action.get("why") or "")
            lines.append(f"{idx}. {title}")
            if why:
                lines.append(f"   - {why}")

    lines.append("")
    lines.append(
        "_Data source: AWS MCP (CloudWatch)_"
        if is_en
        else "_数据来源: AWS MCP (CloudWatch)_"
    )
    return "\n".join(lines)

