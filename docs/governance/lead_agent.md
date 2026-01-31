# Lead Agent 设计文档

## 概述

Lead Agent 是 AgentOS 的自动化风险线索挖掘系统，通过分析 Supervisor 决策历史，识别系统性风险、异常模式和潜在问题，并自动创建后续调查任务。

## 核心职责

Lead Agent 的核心职责是：

1. **风险扫描**：定期扫描 Supervisor 决策历史，识别风险模式
2. **线索挖掘**：通过规则引擎检测系统性风险（如超时模式、阻塞激增、红线违规等）
3. **去重存储**：基于 fingerprint 幂等存储，避免重复告警
4. **任务创建**：为高优先级风险自动创建后续调查任务

## Lead Agent 不做什么

为了保持系统简洁和职责清晰，Lead Agent **明确不做**以下事情：

1. **不做实时监控**：Lead Agent 是离线批处理系统，通过定时任务扫描历史数据，不提供实时告警
2. **不做决策执行**：Lead Agent 只发现风险并创建任务，不直接干预 Supervisor 决策或任务执行
3. **不做复杂统计**：初期只做简单规则检测（计数、阈值、比率），不引入机器学习或复杂时序分析
4. **不做人工审查**：Lead Agent 完全自动化，发现的风险通过任务系统流转，不需要人工审批
5. **不做直接 DB 访问**：Lead Agent 通过 StorageAdapter 查询数据，不直接访问数据库

## 核心概念

### 1. LeadFinding（风险发现）

LeadFinding 代表 Lead Agent 发现的单个风险或异常模式。

**关键字段**：
- `finding_id`: 唯一标识符
- `fingerprint`: 幂等指纹（用于去重）
- `rule_code`: 触发的规则代码（如 `TASK_TIMEOUT_PATTERN`）
- `severity`: 严重程度（`low` | `medium` | `high` | `critical`）
- `title`: 简短标题
- `description`: 详细描述
- `evidence`: 证据数据（count、samples、metrics 等）
- `window`: 扫描窗口
- `detected_at`: 检测时间

**Fingerprint 机制**（🔒 FROZEN）：

Fingerprint 用于去重 LeadFinding，确保相同风险不会重复创建 follow-up tasks。

**生成算法**：
```
fingerprint = SHA256(rule_code|window_kind|dimensions)[:16]
```

**关键特性**：
1. ✅ **只包含 window.kind**：不包含具体时间范围（start_ts/end_ts），确保每日扫描能正确去重
2. ✅ **区分窗口类型**：24h 和 7d 窗口产生不同 fingerprint，避免混淆
3. ✅ **幂等性**：相同输入永远产生相同 fingerprint
4. ✅ **维度排序**：dimensions 按 key 排序，顺序无关

**必须包含的字段**：
- `rule_code`: 规则代码（如 `blocked_reason_spike`）
- `window_kind`: 窗口类型（`24h` 或 `7d`）
- `dimensions`: 关键维度（如 `finding_code`, `task_id` 等）

**示例**：
```python
# 24h 窗口的 NETWORK_TIMEOUT 错误
fingerprint_24h = LeadFinding.generate_fingerprint(
    rule_code="blocked_reason_spike",
    window=window_24h,  # window.kind = "24h"
    dimensions={"finding_code": "NETWORK_TIMEOUT"}
)
# 结果: "cdb89e41216d9128"

# 7d 窗口的相同错误（不同 fingerprint）
fingerprint_7d = LeadFinding.generate_fingerprint(
    rule_code="blocked_reason_spike",
    window=window_7d,  # window.kind = "7d"
    dimensions={"finding_code": "NETWORK_TIMEOUT"}
)
# 结果: "f5b13c0a1407aa9e" (不同！)

# 第二天扫描相同风险（相同 fingerprint，正确去重）
window_next_day = ScanWindow(
    kind=WindowKind.HOUR_24,
    start_ts="2025-01-02T00:00:00Z",  # 不同时间
    end_ts="2025-01-03T00:00:00Z"
)
fingerprint_next_day = LeadFinding.generate_fingerprint(
    rule_code="blocked_reason_spike",
    window=window_next_day,
    dimensions={"finding_code": "NETWORK_TIMEOUT"}
)
# 结果: "cdb89e41216d9128" (相同！去重生效)

# 创建 finding
finding = LeadFinding(
    finding_id="lead_abc123",
    fingerprint=fingerprint_24h,
    rule_code="blocked_reason_spike",
    severity="high",
    title="Finding code 'NETWORK_TIMEOUT' spiked",
    description="Finding code 'NETWORK_TIMEOUT' appeared 10 times in the last 24h",
    evidence={"count": 10, "finding_code": "NETWORK_TIMEOUT"},
    window=window_24h
)
```

**变更管理**：

Fingerprint 生成逻辑已通过 snapshot 测试冻结（`tests/unit/lead/test_fingerprint_freeze.py`）。

如果需要修改 fingerprint 生成逻辑：
1. 更新 `LeadFinding.generate_fingerprint()` 方法
2. 更新所有 snapshot 测试的期望值
3. 在 CHANGELOG 中记录变更原因
4. 考虑数据迁移方案（历史 findings 的 fingerprint 会失效）

**测试验证**：
```bash
# 运行 fingerprint 冻结测试
cd tests/unit/lead
python3 run_fingerprint_freeze_tests.py
```

### 2. ScanWindow（扫描窗口）

ScanWindow 定义风险扫描的时间范围。

**支持的窗口类型**：
- `24h`: 24小时窗口（日常监控）
- `7d`: 7天窗口（周趋势分析）

示例：
```python
window = ScanWindow(
    kind=WindowKind.HOUR_24,
    start_ts="2024-01-01T00:00:00Z",
    end_ts="2024-01-02T00:00:00Z"
)
```

### 3. FollowUpTaskSpec（后续任务规格）

FollowUpTaskSpec 描述基于 finding 需要创建的后续任务。

**关键字段**：
- `finding_fingerprint`: 关联的 finding
- `title`: 任务标题
- `description`: 任务描述
- `priority`: 优先级（`low` | `medium` | `high` | `critical`）
- `metadata`: 额外元数据

示例：
```python
task_spec = FollowUpTaskSpec(
    finding_fingerprint=finding.fingerprint,
    title="Investigate timeout pattern for task_123",
    description="Task task_123 has repeated timeouts. Review logs and identify root cause.",
    priority="high",
    metadata={"rule_code": "TASK_TIMEOUT_PATTERN"}
)
```

### 4. ScanResult（扫描结果）

ScanResult 是 `LeadService.run_scan()` 的返回值。

**关键字段**：
- `findings`: 发现的风险列表
- `window`: 扫描窗口
- `tasks_created`: 创建的任务数量
- `metadata`: 扫描元数据（scan_id、规则统计等）

## 核心接口

### LeadService.run_scan()

Lead Agent 的核心接口（**接口冻结**）。

**签名**：
```python
def run_scan(
    self,
    window_kind: str,
    dry_run: bool = True
) -> Dict[str, Any]:
    """
    运行风险扫描
    
    Args:
        window_kind: "24h" | "7d" 扫描窗口类型
        dry_run: True 时不创建 follow-up tasks，只返回发现结果
    
    Returns:
        {
            "findings": [LeadFinding.to_dict(), ...],
            "window": ScanWindow.to_dict(),
            "tasks_created": int,
            "metadata": {
                "scan_id": str,
                "dry_run": bool,
                "total_findings": int,
                "deduplicated_findings": int,
                "rule_stats": {...}
            }
        }
    """
```

**扫描流程**：
1. 构建扫描窗口（基于 window_kind）
2. 执行风险挖掘（调用 RiskMiner）
3. 去重存储（调用 DedupeStore）
4. 创建后续任务（调用 FollowUpTaskCreator，仅 dry_run=False）
5. 返回扫描结果

**使用示例**：
```python
from agentos.core.lead import LeadService

# 初始化服务
service = LeadService()

# 运行扫描（dry_run 模式）
result = service.run_scan(window_kind="24h", dry_run=True)

print(f"Found {len(result['findings'])} risks")
print(f"Created {result['tasks_created']} tasks")
```

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    Jobs/Cron Layer                       │
│              (定时触发 run_scan)                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     LeadService                          │
│         (协调扫描流程，零外部依赖)                       │
└─────────────────────────────────────────────────────────┘
        │               │                │
        ▼               ▼                ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│ RiskMiner   │ │ DedupeStore │ │ FollowUpTask    │
│ (规则引擎)  │ │ (去重存储)  │ │ Creator         │
└─────────────┘ └─────────────┘ └─────────────────┘
        │               │                │
        ▼               ▼                ▼
┌─────────────────────────────────────────────────────────┐
│                   StorageAdapter                         │
│              (只读查询 Supervisor 历史)                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      Database                            │
│      (supervisor_inbox, task_audits, lead_findings)      │
└─────────────────────────────────────────────────────────┘
```

### 设计原则

1. **零外部依赖**：LeadService 不直接依赖 DB/jobs/TaskService，所有依赖通过参数注入
2. **接口冻结**：`run_scan()` 签名不可变，确保调用方稳定
3. **幂等去重**：基于 fingerprint 去重，避免重复告警
4. **纯领域逻辑**：LeadService 只处理扫描流程，存储/调度由外部负责

## 规则引擎

Lead Agent 通过 RiskMiner 执行风险检测规则。

### 初期规则（6条）

1. **TASK_TIMEOUT_PATTERN**：任务超时模式（同一任务重复超时）
2. **BLOCKED_REASON_SPIKE**：阻塞原因激增（某个 finding code 在窗口内激增）
3. **REDLINE_VIOLATION_RATE**：红线违规率（REDLINE findings 比率超过阈值）
4. **RETRY_STORM_PATTERN**：重试风暴模式（RETRY 决策后仍然失败）
5. **TASK_FAILURE_CLUSTER**：任务失败集群（某类任务集中失败）
6. **SUPERVISOR_DECISION_CONFLICT**：Supervisor 决策冲突（同一任务频繁 PAUSE/BLOCK）

### 规则配置

规则阈值可通过 `LeadServiceConfig` 配置：

```python
config = LeadServiceConfig(
    timeout_threshold=3,      # 超时阈值
    blocked_threshold=5,      # 阻塞阈值
    redline_threshold=1,      # 红线阈值
    create_followup_tasks=True
)

service = LeadService(config)
```

## 存储设计

### lead_findings 表结构

```sql
CREATE TABLE IF NOT EXISTS lead_findings (
    finding_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,  -- 幂等指纹
    rule_code TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    evidence TEXT,                     -- JSON
    window_kind TEXT NOT NULL,
    window_start_ts TEXT NOT NULL,
    window_end_ts TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lead_findings_fingerprint ON lead_findings(fingerprint);
CREATE INDEX idx_lead_findings_rule_code ON lead_findings(rule_code);
CREATE INDEX idx_lead_findings_severity ON lead_findings(severity);
CREATE INDEX idx_lead_findings_detected_at ON lead_findings(detected_at DESC);
```

### 去重机制

通过 `fingerprint UNIQUE` 约束实现幂等：

```python
# 1. 计算 fingerprint
fingerprint = LeadFinding.generate_fingerprint(
    rule_code="TASK_TIMEOUT_PATTERN",
    window=window,
    dimensions={"task_id": "task_123"}
)

# 2. 插入时去重
INSERT OR IGNORE INTO lead_findings (...)
VALUES (...)
```

## 调度设计

Lead Agent 通过 Jobs/Cron 定时触发扫描。

### 推荐调度策略

- **24h 扫描**：每小时执行一次
- **7d 扫描**：每天执行一次

示例：
```python
# 每小时扫描 24h 窗口
@cron("0 * * * *")
def hourly_scan():
    service = LeadService()
    service.run_scan(window_kind="24h", dry_run=False)

# 每天扫描 7d 窗口
@cron("0 2 * * *")
def daily_scan():
    service = LeadService()
    service.run_scan(window_kind="7d", dry_run=False)
```

## 配置管理

### LeadServiceConfig

```python
@dataclass
class LeadServiceConfig:
    # 扫描窗口配置
    default_window_kind: str = "24h"
    
    # 规则阈值
    timeout_threshold: int = 3
    blocked_threshold: int = 5
    redline_threshold: int = 1
    
    # Follow-up 任务配置
    create_followup_tasks: bool = True
```

### 配置更新

```python
service = LeadService()

# 获取当前配置
config = service.get_config()

# 更新配置
service.update_config({
    "timeout_threshold": 10,
    "blocked_threshold": 20
})
```

## 测试策略

### 单元测试

- **models.py**：测试模型序列化、fingerprint 生成、字段验证
- **service.py**：测试扫描流程、窗口构建、配置管理

### 集成测试

- **端到端扫描**：真实数据 → 规则检测 → 去重存储 → 任务创建
- **幂等性验证**：重复扫描不产生重复 findings
- **规则准确性**：验证各规则的检测准确率

## 契约版本管理

### 概述

Lead Agent 使用契约版本号机制防止"静默失败"（数据格式变更导致 findings=0 但无人发现）。

### 背景

当前 Lead Agent 使用"从 payload JSON 提取 + 转换层"的方案，存在两类系统性风险：

1. **Silent failure（静默失败）**：字段名变了、事件名变了、payload 结构变了 → 查询还能跑，但 findings=0
2. **Contract drift（契约漂移）**：storage 输出聚合 vs miner 期望原始 → 必须靠转换层兜底

### 版本号定义

- **Storage Contract Version** (`LeadStorage.CONTRACT_VERSION`): 定义 Storage Adapter 返回的数据格式
- **Miner Contract Version** (`RiskMiner.CONTRACT_VERSION`): 定义 Risk Miner 期望的输入数据格式

当前版本：
- Storage: v1.0.0
- Miner: v1.0.0

### 版本检查行为

Lead Agent 在每次扫描前自动检查契约版本：

- **dry-run 模式**：版本不匹配时输出 `WARNING: CONTRACT_MISMATCH`，允许继续执行
- **非 dry-run 模式**：版本不匹配时抛出 `RuntimeError`，拒绝执行

示例输出：
```
Contract versions: storage=1.0.0, miner=1.0.0
✓ Versions compatible

# 版本不匹配时（dry-run）
⚠️  WARNING: CONTRACT_MISMATCH: Storage version (1.0.0) != Miner version (2.0.0).
This may cause silent failures where findings=0.

# 版本不匹配时（非 dry-run）
✗ Lead scan failed: CONTRACT_MISMATCH: Storage version (1.0.0) != Miner version (2.0.0).
```

### 契约说明

#### Storage Contract v1.0.0

返回聚合数据格式：

```python
{
    "blocked_reasons": [
        {
            "code": str,        # 阻塞原因代码
            "count": int,       # 出现次数
            "task_ids": [str]   # 样例 task_ids（最多5个）
        }
    ],
    "pause_block_churn": [
        {
            "task_id": str,
            "pause_count": int,
            "final_status": str
        }
    ],
    "retry_then_fail": [
        {
            "error_code": str,
            "count": int,
            "task_ids": [str]
        }
    ],
    "decision_lag": {
        "p95_ms": int,
        "samples": [{"decision_id": str, "lag_ms": int}]
    },
    "redline_ratio": {
        "current_ratio": float,
        "previous_ratio": float,
        "current_count": int,
        "total_count": int
    },
    "high_risk_allow": [
        {
            "decision_id": str,
            "task_id": str,
            "risk_level": str
        }
    ]
}
```

#### Miner Contract v1.0.0

期望输入数据格式（通过转换层生成）：

```python
{
    "findings": [
        {
            "code": str,
            "kind": str,
            "severity": str,
            "decision_id": str,
            "message": str
        }
    ],
    "decisions": [
        {
            "task_id": str,
            "decision_id": str,
            "decision_type": str,
            "timestamp": str
        }
    ],
    "metrics": {
        "decision_latencies": [float],
        "decision_lag_p95": float
    }
}
```

### 版本升级指南

当需要修改 Storage 或 Miner 的数据格式时：

1. **修改代码**：更新数据结构和查询逻辑
2. **更新版本号**：更新对应的 `CONTRACT_VERSION`（遵循语义化版本）
   - Major version: 破坏性变更（不兼容）
   - Minor version: 新增字段（向后兼容）
   - Patch version: bug 修复
3. **更新契约说明**：在类文件中更新契约说明注释
4. **版本兼容性**：如果版本不兼容，同步更新另一侧的版本号
5. **运行测试**：运行所有测试确保兼容性

示例：
```python
class LeadStorage:
    # v1.0.0 → v2.0.0: 重构 blocked_reasons 格式
    # v2.0.0:
    # - blocked_reasons 改为返回完整 finding 对象
    # - 移除 task_ids 限制
    CONTRACT_VERSION = "2.0.0"
```

### 测试覆盖

契约版本机制包含以下测试：

1. **版本常量定义测试**：验证 `CONTRACT_VERSION` 已定义
2. **版本格式验证**：验证版本号遵循 X.Y.Z 格式
3. **兼容性检查测试**：验证版本匹配时通过检查
4. **不兼容告警测试**：验证 dry-run 时输出 WARNING
5. **不兼容阻止测试**：验证非 dry-run 时抛出异常
6. **集成测试**：验证扫描结果包含版本信息

运行测试：
```bash
python3.13 tests/unit/lead/run_contract_version_tests.py
```

## Supervisor 事件依赖白名单

### 概述

Lead Agent 依赖 Supervisor 写入 `task_audits` 表的特定事件和 payload 字段。本章节列出完整的依赖白名单，确保 Supervisor 变更时不会破坏 Lead Agent。

**重要性**：如果 Supervisor 修改了事件命名或 payload 结构，Lead Agent 会静默失效（findings=0 但无人发现）。通过明确白名单并锁定测试，可以在 Supervisor 变更时立即发现破坏性变更。

**测试锁定**：所有白名单依赖通过单元测试锁定（`tests/unit/lead/test_supervisor_contract.py`）。

### 事件类型白名单

Lead Agent 依赖以下 Supervisor 事件类型：

| Event Type | 用途 | 关联规则 | 必需? |
|-----------|------|---------|------|
| `SUPERVISOR_BLOCKED` | 任务被阻塞 | 规则1: blocked_reason_spike<br>规则3: retry_recommended_but_fails | ✅ |
| `SUPERVISOR_PAUSED` | 任务暂停 | 规则2: pause_block_churn | ✅ |
| `SUPERVISOR_RETRY_RECOMMENDED` | 建议重试 | 规则3: retry_recommended_but_fails | ✅ |
| `SUPERVISOR_DECISION` | 通用决策 | 规则4: decision_lag_anomaly<br>规则5: redline_ratio_increase | ✅ |
| `SUPERVISOR_ALLOWED` | 允许继续 | 规则6: high_risk_allow | ✅ |

**⚠️ 重要**：修改这些事件类型时，必须同步更新 Lead Agent 的查询逻辑，否则会导致静默失效。

### Payload 字段白名单

#### 通用字段（所有事件）

所有 Supervisor 事件都应包含以下通用字段：

| 字段 | JSONPath | 类型 | 必需? | 说明 | 示例 |
|-----|---------|------|-------|------|------|
| 决策 ID | `$.decision_id` | string | ✅ | 决策唯一标识符，用于关联和追溯 | `"decision_abc123"` |
| 决策类型 | `$.decision_type` | string | ✅ | 决策类型（allow/pause/block/retry） | `"block"` |
| 时间戳 | `$.timestamp` | string | ✅ | 决策时间戳（ISO8601 格式） | `"2025-01-28T10:00:00Z"` |
| 发现列表 | `$.findings` | array | ✅ | 发现的问题列表 | `[{code: "REDLINE_001", ...}]` |
| 决策理由 | `$.reason` | string | ❌ | 决策理由（可选） | `"High risk detected"` |

#### SUPERVISOR_BLOCKED 事件特定字段

| 字段 | JSONPath | 类型 | 必需? | 说明 | 使用场景 |
|-----|---------|------|-------|------|---------|
| 阻塞原因码 | `$.findings[].code` | string | ✅ | 阻塞原因代码 | 规则1: blocked_reason_spike - 统计阻塞原因分布 |
| 问题类型 | `$.findings[].kind` | string | ❌ | 问题类型（REDLINE/CONFLICT/RISK/RUNTIME） | 规则5: redline_ratio_increase - 统计 REDLINE 占比 |
| 严重程度 | `$.findings[].severity` | string | ❌ | 严重程度（LOW/MEDIUM/HIGH/CRITICAL） | 可选，用于优先级排序 |

#### SUPERVISOR_PAUSED 事件特定字段

PAUSE 事件主要依赖事件序列（不依赖特定 payload 字段）：
- 规则2 通过统计 PAUSE 事件次数和检查最终状态（PAUSE -> BLOCK 模式）来检测 churn

#### SUPERVISOR_RETRY_RECOMMENDED 事件特定字段

RETRY 事件主要用于检测 RETRY -> BLOCK 模式（不依赖特定 payload 字段）：
- 规则3 通过事件序列检测失败模式（RETRY 后是否有 BLOCK）

#### SUPERVISOR_DECISION 事件特定字段

用于延迟统计：

| 字段 | JSONPath | 类型 | 必需? | 说明 | 使用场景 |
|-----|---------|------|-------|------|---------|
| 源事件时间 | `$.source_event_ts` | string | ✅ | 源事件时间戳（ISO8601） | 规则4: decision_lag_anomaly - 计算决策延迟（p95） |

延迟计算公式：`lag_ms = (timestamp - source_event_ts) * 1000`

#### SUPERVISOR_ALLOWED 事件特定字段

用于高风险放行检测：

| 字段 | JSONPath | 类型 | 必需? | 说明 | 使用场景 |
|-----|---------|------|-------|------|---------|
| 风险严重程度 | `$.findings[].severity` | string | ✅ | 风险严重程度 | 规则6: high_risk_allow - 检测 HIGH/CRITICAL 风险但仍 ALLOW 的决策 |

有效值：`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

### 版本兼容性

**当前版本**: v1.0.0（基于 Supervisor v0.x）

**向后兼容策略**：

| 变更类型 | 兼容性 | 说明 |
|---------|--------|------|
| 新增字段 | ✅ 兼容 | Lead Agent 使用 `payload.get()` 安全访问，新字段不影响现有逻辑 |
| 删除字段 | ❌ 破坏性变更 | 会导致 Lead Agent 失效，必须同步更新查询逻辑 |
| 重命名字段 | ❌ 破坏性变更 | 会导致 Lead Agent 失效，必须同步更新查询逻辑 |
| 修改枚举值 | ❌ 破坏性变更 | 会导致规则失效，必须同步更新检测逻辑 |
| 新增事件类型 | ✅ 兼容 | Lead Agent 只查询白名单中的事件类型，不影响现有逻辑 |
| 删除事件类型 | ❌ 破坏性变更 | 会导致 Lead Agent 失效，必须同步更新查询逻辑 |

**变更通知机制**：

1. **Supervisor 变更前**：
   - 检查变更是否涉及白名单中的事件或字段
   - 如果是破坏性变更，通知 Lead Agent 维护者
   - 运行 Lead Agent 的 `test_supervisor_contract.py` 测试

2. **测试失败时**：
   - 如果测试失败，说明 Supervisor 变更会破坏 Lead Agent
   - 必须按照 Breaking Changes 处理：
     - 同步更新 Lead Agent 的查询逻辑
     - 更新白名单定义
     - 更新契约版本号

3. **发布协调**：
   - Supervisor 和 Lead Agent 必须同时发布
   - 或先发布 Lead Agent（向后兼容），再发布 Supervisor

### 测试锁定

所有白名单依赖通过单元测试锁定（`tests/unit/lead/test_supervisor_contract.py`）：

#### 测试覆盖

| 测试类 | 测试内容 | 失败时说明 |
|-------|---------|-----------|
| `TestSupervisorEventTypeContract` | 验证事件类型白名单与 Supervisor/LeadStorage 常量一致 | 事件类型定义不一致，可能导致查询失败 |
| `TestSupervisorPayloadContract` | 验证 payload 字段白名单已定义 | 缺少必需字段定义 |
| `TestFixtureCompliance` | 验证测试 fixture 包含所有必需字段 | 测试数据不符合契约，可能导致测试失效 |
| `TestSupervisorContractBreakageDetection` | 检测 Supervisor 是否删除了白名单中的事件类型 | Supervisor 删除了必需事件类型（破坏性变更） |
| `TestPayloadFieldAccessPattern` | 验证安全的字段访问模式（.get() vs []） | 不安全的字段访问可能导致运行时错误 |
| `TestContractDocumentation` | 验证所有必需字段都有文档说明 | 缺少字段文档 |

#### 运行测试

```bash
# 运行 Supervisor 契约测试
. .venv/bin/activate
python -m pytest tests/unit/lead/test_supervisor_contract.py -v

# 预期输出（所有测试通过）：
# ✓ test_event_types_defined
# ✓ test_event_types_match_storage_constants
# ✓ test_event_types_match_supervisor_constants
# ✓ test_common_fields_defined
# ✓ test_event_specific_fields_defined
# ✓ test_blocked_event_fixture_has_required_fields
# ✓ test_paused_event_fixture_has_required_fields
# ✓ test_allowed_event_fixture_has_required_fields
# ✓ test_decision_event_fixture_has_lag_fields
# ✓ test_all_storage_queries_use_whitelisted_events
# ✓ test_supervisor_has_not_removed_required_events
# ... (总共 15 个测试)
```

#### 测试失败场景

**场景 1：Supervisor 删除了必需事件类型**

```
FAILED test_supervisor_has_not_removed_required_events
AssertionError: ❌ BREAKING CHANGE DETECTED!
Supervisor removed required event types: {'SUPERVISOR_BLOCKED'}
Lead Agent will fail silently!
Action required:
1. If intentional: Update Lead Agent to handle missing events
2. If unintentional: Restore event types in Supervisor
```

**场景 2：测试 fixture 缺少必需字段**

```
FAILED test_blocked_event_fixture_has_required_fields
AssertionError: BLOCKED event fixture missing required common field: decision_id
```

**场景 3：契约版本不兼容**

```
FAILED test_contract_version_is_defined
AssertionError: Contract version must follow semantic versioning: invalid_version
```

### Payload 示例

以下是符合契约的 payload 示例：

#### SUPERVISOR_BLOCKED 事件

```json
{
  "decision_id": "dec_abc123",
  "decision_type": "block",
  "timestamp": "2025-01-28T10:00:00Z",
  "reason": "Redline violation detected",
  "findings": [
    {
      "code": "REDLINE_001",
      "severity": "HIGH",
      "kind": "REDLINE",
      "message": "API rate limit exceeded"
    }
  ],
  "actions": []
}
```

#### SUPERVISOR_DECISION 事件（用于延迟计算）

```json
{
  "decision_id": "dec_def456",
  "decision_type": "allow",
  "timestamp": "2025-01-28T10:00:05Z",
  "source_event_ts": "2025-01-28T10:00:00Z",
  "reason": "Normal decision",
  "findings": [],
  "actions": []
}
```

#### SUPERVISOR_ALLOWED 事件（高风险场景）

```json
{
  "decision_id": "dec_ghi789",
  "decision_type": "allow",
  "timestamp": "2025-01-28T10:00:00Z",
  "reason": "Risk acceptable within policy",
  "findings": [
    {
      "code": "RISK_001",
      "severity": "HIGH",
      "kind": "RISK",
      "message": "High risk API call"
    }
  ],
  "actions": []
}
```

### 版本升级指南

当需要修改 Supervisor 事件或 payload 结构时：

1. **评估影响**：
   - 检查变更是否涉及白名单中的事件或字段
   - 确定是否为破坏性变更

2. **更新白名单**（如果需要）：
   - 在 `test_supervisor_contract.py` 中更新白名单定义
   - 更新文档中的白名单表格

3. **运行测试**：
   - 运行 `test_supervisor_contract.py` 确保兼容性
   - 如果测试失败，说明变更会破坏 Lead Agent

4. **同步更新 Lead Agent**：
   - 更新 `LeadStorage` 的查询逻辑
   - 更新转换层（ContractMapper）
   - 更新测试 fixture

5. **更新契约版本号**：
   - 如果是破坏性变更，更新 `SUPERVISOR_CONTRACT_VERSION`
   - 遵循语义化版本（major.minor.patch）

6. **协调发布**：
   - Supervisor 和 Lead Agent 同步发布
   - 或先发布 Lead Agent（向后兼容），再发布 Supervisor

### 常见问题

**Q: 为什么需要白名单？**

A: 防止 Supervisor 修改事件命名或 payload 结构导致 Lead Agent 静默失效（findings=0 但无人发现）。

**Q: 如何验证 Supervisor 变更是否会破坏 Lead Agent？**

A: 运行 `test_supervisor_contract.py`，如果测试失败，说明变更会破坏 Lead Agent。

**Q: 如果必须进行破坏性变更怎么办？**

A: 按照版本升级指南操作，同步更新 Lead Agent 和 Supervisor，确保协调发布。

**Q: payload 中的可选字段如何安全访问？**

A: 使用 `.get()` 方法：`payload.get("optional_field", default_value)`，避免 KeyError。

## 配置管理

### 概述

Lead Agent 的规则阈值通过 YAML 配置文件管理，支持运行时 override，同时保持默认值冻结在代码仓库中。

### 配置文件位置

**默认配置**：`agentos/config/lead_rules.yaml`

配置文件包含：
- 规则阈值（spike_threshold, pause_count_threshold 等）
- 告警阈值（min_blocked_for_alert 等）
- 日志配置（print_threshold_summary, log_level）

### 配置 Override 优先级

配置加载优先级（从高到低）：

1. **环境变量** `LEAD_CONFIG`（最高优先级）
2. **命令行参数** `--config`
3. **默认配置文件** `agentos/config/lead_rules.yaml`
4. **硬编码默认值**（fallback）

### 使用示例

#### 使用默认配置

```bash
python -m agentos.jobs.lead_scan --window 24h
```

#### 使用自定义配置文件

```bash
python -m agentos.jobs.lead_scan --window 24h --config /path/to/custom_config.yaml
```

#### 通过环境变量 override

```bash
export LEAD_CONFIG=/path/to/prod_config.yaml
python -m agentos.jobs.lead_scan --window 24h
```

### 阈值摘要

每次扫描开始时，会打印当前使用的阈值（可通过配置禁用）：

```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ 规则               ┃ 阈值  ┃ 说明              ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ blocked_reason_... │ 5     │ 相同错误码激增    │
│ pause_block_churn  │ 2     │ PAUSE 次数阈值    │
│ retry_then_fail    │ 1     │ RETRY 后失败      │
│ decision_lag       │ 5000ms│ 决策延迟 p95      │
│ redline_ratio      │ 10%   │ 占比增幅阈值      │
│ high_risk_allow    │ 1     │ 高危放行          │
└────────────────────┴───────┴───────────────────┘
```

### 配置文件格式

```yaml
version: "1.0.0"

rules:
  blocked_reason_spike:
    threshold: 5
    description: "检测相同错误码在短时间内大量出现"
    severity: "HIGH"

  pause_block_churn:
    pause_count_threshold: 2
    description: "检测任务多次暂停后最终被阻塞"
    severity: "MEDIUM"

  retry_then_fail:
    threshold: 1
    description: "检测建议重试但仍然失败的任务"
    severity: "HIGH"

  decision_lag:
    p95_threshold_ms: 5000
    description: "检测 Supervisor 决策延迟异常"
    severity: "MEDIUM"

  redline_ratio:
    increase_threshold: 0.10
    min_baseline: 0.05
    description: "检测高风险 findings 占比显著上升"
    severity: "HIGH"

  high_risk_allow:
    threshold: 1
    description: "检测高风险或严重风险被允许通过"
    severity: "CRITICAL"

alert_thresholds:
  min_blocked_for_alert: 5
  min_high_risk_for_alert: 1

logging:
  print_threshold_summary: true
  log_level: "INFO"
```

### 向后兼容

LeadScanJob 保持向后兼容，支持直接传递 `MinerConfig` 和 `alert_thresholds` 参数：

```python
# 新方式：使用配置文件
job = LeadScanJob(config_path=Path("/path/to/config.yaml"))

# 旧方式：直接传递配置对象（仍然支持）
custom_config = MinerConfig(spike_threshold=10)
job = LeadScanJob(config=custom_config)
```

### 阈值调整指南

修改阈值时：

1. **创建自定义配置文件**：复制默认配置并修改
2. **测试验证**：使用 `--dry-run` 验证效果
3. **记录变更**：在 CHANGELOG 中记录阈值调整原因
4. **生产部署**：通过环境变量 `LEAD_CONFIG` 指定配置文件

**注意**：不要直接修改 `agentos/config/lead_rules.yaml`，而是通过 override 机制使用自定义配置。

### 测试覆盖

配置管理包含以下测试：

- **默认配置加载**：验证默认配置正确加载
- **自定义配置加载**：验证 override 机制工作正常
- **环境变量 override**：验证环境变量优先级
- **Fallback 机制**：验证配置文件不存在时使用硬编码默认值
- **部分配置**：验证部分配置文件正确合并默认值
- **向后兼容**：验证旧代码仍然可以直接传递配置对象

运行测试：
```bash
uv run pytest tests/unit/config/test_config_loader.py -v
uv run pytest tests/unit/config/test_lead_scan_integration.py -v
```

## 冗余列优化（v21+）

### 概述

从 v0.21.0 开始，`task_audits` 表添加了冗余列以提升 Lead Agent 的查询性能。这些列与 `payload` JSON 中的字段内容相同，但提供了直接的列访问和索引支持。

### 新增列

| 列名 | 类型 | 说明 | 索引 | v15+ |
|-----|------|------|------|------|
| `decision_id` | TEXT | Supervisor 决策 ID | ✅ | ✅（v15 已添加） |
| `source_event_ts` | TIMESTAMP | 源事件时间戳 | ✅ | ✅（v21 新增） |
| `supervisor_processed_at` | TIMESTAMP | Supervisor 处理时间 | - | ✅（v21 新增） |

### 性能提升

| 查询类型 | v20（JSON 提取） | v21（冗余列） | 提升 |
|---------|-----------------|--------------|------|
| decision_lag 查询 | ~50ms | ~5ms | **10x** |
| 按 decision_id 过滤 | 全表扫描 | 索引查询 | **100x+** |
| 按时间范围查询 | JSON 解析 | 列直接访问 | **10x** |

### 向后兼容性

LeadStorage 自动检测 schema 版本并使用相应的查询路径：

- **v21+**: 优先使用冗余列（性能路径）
- **v20**: Fallback 到 payload JSON（兼容路径）
- **混合数据**: 同时支持冗余列和 JSON 提取（行级 fallback）

**实现机制**：

```python
# LeadStorage.get_decision_lag() 中的自动检测逻辑
cursor.execute("PRAGMA table_info(task_audits)")
columns = {row[1] for row in cursor.fetchall()}
has_redundant_columns = 'source_event_ts' in columns

if has_redundant_columns:
    # v21+ 路径：优先使用冗余列
    if source_event_ts and supervisor_processed_at:
        # 从列直接读取（快速路径）
        ...
    else:
        # Fallback 到 payload JSON（向后兼容）
        ...
else:
    # v20 路径：从 payload JSON 提取
    ...
```

### 迁移策略

**新事件**（v21+）：
- Supervisor 写入时同时填充 payload 和冗余列
- 两者保持同步，确保数据一致性

**旧事件**（v20）：
- payload 仍然有效（作为 source of truth）
- 冗余列为 NULL（触发 fallback）
- 可选：运行 backfill 脚本迁移历史数据

### 索引优化

v21 migration 创建了以下索引：

```sql
-- 单列索引：按 source_event_ts 查询
CREATE INDEX idx_task_audits_source_event_ts
ON task_audits(source_event_ts)
WHERE source_event_ts IS NOT NULL;

-- 复合索引：决策延迟查询（同时使用两个时间戳）
CREATE INDEX idx_task_audits_decision_lag
ON task_audits(source_event_ts, supervisor_processed_at)
WHERE source_event_ts IS NOT NULL AND supervisor_processed_at IS NOT NULL;

-- 复合索引：按事件类型 + 时间查询
CREATE INDEX idx_task_audits_event_source_ts
ON task_audits(event_type, source_event_ts)
WHERE source_event_ts IS NOT NULL;
```

### 查询示例

**v20（旧）**:
```sql
SELECT payload FROM task_audits WHERE event_type='SUPERVISOR_DECISION'
-- 需要：
-- 1. JSON 解析
-- 2. 字段提取
-- 3. 无法使用索引
```

**v21（新）**:
```sql
SELECT decision_id, source_event_ts, supervisor_processed_at
FROM task_audits
WHERE event_type='SUPERVISOR_DECISION'
  AND source_event_ts IS NOT NULL
-- 优势：
-- 1. 直接列访问
-- 2. 使用 idx_task_audits_event_source_ts 索引
-- 3. 查询计划优化
```

### 数据一致性

**原则**：
- **Payload JSON 是 source of truth**：冗余列是性能优化，不是替代
- **同步写入**：新事件同时填充 payload 和冗余列
- **Fallback 机制**：冗余列为 NULL 时，自动从 payload 提取

**验证**：
```bash
# 运行 v21 migration 测试
python3 tests/unit/lead/run_v21_migration_tests.py

# 预期输出：
# ✅ test_v21_migration_adds_columns
# ✅ test_backward_compatibility_with_null_columns
# ✅ test_new_data_uses_redundant_columns
# ✅ test_mixed_data_sources
# ✅ test_filter_negative_lag
# ✅ test_empty_window
```

### 历史数据 Backfill（可选）

如果需要为历史数据填充冗余列：

```sql
-- Backfill source_event_ts
UPDATE task_audits
SET source_event_ts = json_extract(payload, '$.source_event_ts')
WHERE source_event_ts IS NULL
  AND json_extract(payload, '$.source_event_ts') IS NOT NULL;

-- Backfill supervisor_processed_at
UPDATE task_audits
SET supervisor_processed_at = COALESCE(
    json_extract(payload, '$.supervisor_processed_at'),
    json_extract(payload, '$.timestamp')
)
WHERE supervisor_processed_at IS NULL
  AND (
    json_extract(payload, '$.supervisor_processed_at') IS NOT NULL
    OR json_extract(payload, '$.timestamp') IS NOT NULL
  );

-- Backfill decision_id (如果 v15 迁移未填充)
UPDATE task_audits
SET decision_id = json_extract(payload, '$.decision_id')
WHERE decision_id IS NULL
  AND json_extract(payload, '$.decision_id') IS NOT NULL;
```

**注意**：
- Backfill 是可选的，仅用于历史数据分析场景
- 不影响 Lead Agent 的正常运行（fallback 机制确保兼容）
- 对于大表，建议分批执行（避免锁表）

### 监控建议

**查询性能监控**：
```sql
-- 检查索引使用情况
EXPLAIN QUERY PLAN
SELECT source_event_ts, supervisor_processed_at
FROM task_audits
WHERE event_type = 'SUPERVISOR_DECISION'
  AND source_event_ts IS NOT NULL;

-- 预期：USING INDEX idx_task_audits_event_source_ts
```

**数据质量监控**：
```sql
-- 统计冗余列覆盖率
SELECT
  COUNT(*) AS total,
  COUNT(source_event_ts) AS with_source_ts,
  COUNT(supervisor_processed_at) AS with_processed_at,
  ROUND(COUNT(source_event_ts) * 100.0 / COUNT(*), 2) AS coverage_pct
FROM task_audits
WHERE event_type LIKE 'SUPERVISOR_%';
```

## 扩展计划

### 未来增强（不在 MVP 范围）

1. **ML 模型集成**：引入机器学习模型进行异常检测
2. **时序分析**：基于时间序列的趋势分析
3. **多维度聚合**：按任务类型、用户、项目等维度聚合风险
4. **风险评分**：综合评分模型替代简单阈值
5. **实时告警**：集成 EventBus 实现实时风险告警

## 参考资料

- [Supervisor 设计文档](./supervisor_architecture.md)
- [Task Governance 设计](./task_governance.md)
- [Risk Miner 规则引擎](../core/lead/README.md)

## 变更历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 0.1.0 | 2024-01-28 | Claude | 初始版本：domain 模型 + LeadService 骨架 |
