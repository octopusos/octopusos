# CLI Task Control Plane - 架构契约与铁律

## 文档目的

本文档记录 CLI Task Control Plane 的**不可变契约**和**架构铁律**，这些规则在任何重构或扩展中都必须保持。

违反这些契约将导致系统可审计性崩溃或运行时不一致。

---

## 🔒 铁律 1: Runner ID 全局唯一性

### 规则

> **Runner `run_id` 必须全局唯一，不得依赖 `pid` 作为唯一因子**

### 背景

在 P2-C2 修复中发现：
- 同一进程中多个 `TaskRunner` 实例会生成相同的 `run_id`（如测试场景）
- 导致 lineage 表约束冲突或数据覆盖
- 破坏 "每次 runner spawn 都可追溯" 的审计保证

### 当前实现（P2-C2）

```python
# task_runner.py
import time
run_id = f"runner_{task_id}_{os.getpid()}_{int(time.time() * 1000)}"
```

**组成**:
- `task_id`: 任务唯一标识
- `pid`: 进程 ID
- `timestamp_ms`: 毫秒级时间戳

**保证**: 即使同一进程中创建多个 runner，时间戳也能确保唯一性。

### 未来演进方向

**允许的改进**:
- 使用 UUID: `run_id = f"runner_{task_id}_{uuid.uuid4().hex[:8]}"`
- 使用 sequence: `run_id = f"runner_{task_id}_{get_next_sequence()}"`

**禁止的行为**:
- ❌ 仅依赖 `pid`: `run_id = f"runner_{task_id}_{os.getpid()}"`（P2-C2 前的错误实现）
- ❌ 仅依赖 task_id: `run_id = task_id`（无法追踪多次 resume）
- ❌ 任何可能在合理场景下重复的策略

### 验收标准

**E2E 测试必须覆盖**:
```python
# 同一 task 多次 runner
runner1 = TaskRunner(...)
runner1.run_task(task_id)

runner2 = TaskRunner(...)
runner2.run_task(task_id)

# 断言: 至少 2 个不同的 runner_spawn lineage
spawns = [e for e in trace.timeline if e.kind == "runner_spawn"]
assert len(spawns) >= 2
assert len(set(e.ref_id for e in spawns)) == len(spawns)  # 全部唯一
```

**代码审查检查点**:
- 任何修改 `run_id` 生成逻辑的 PR 必须附带唯一性证明
- 必须通过 P2 E2E 测试（包含两次 runner_spawn 验证）

---

## 🔒 铁律 2: Lineage 写失败不得静默吞掉

### 规则

> **Lineage 写入失败必须被记录或在 debug 模式下中断执行，不得静默吞掉**

### 背景

当前实现（P2）：
```python
# task_runner.py
try:
    self.task_manager.add_lineage(...)
except Exception as e:
    logger.error(f"Failed to record runner spawn: {e}")  # ← 仅 log
    # 继续执行
```

**问题**:
- 如果 lineage 写入持续失败（如 DB 权限、磁盘满），系统会"静默丢失审计数据"
- 在生产环境中可能几周后才发现 trace timeline 不完整
- 违反 "可审计性优先" 的核心原则

### 当前状态（P2）

**暂时可接受**，因为：
- P2 目标是"功能闭环"，不是"生产强化"
- 测试环境中 lineage 写入通常不会失败
- 已通过 E2E 验证关键 lineage 存在

### TechDebt: 必须在 P3 或后续阶段修复

**修复方案选项**:

#### 选项 A: Debug 模式强制中断（推荐）

```python
try:
    self.task_manager.add_lineage(...)
except Exception as e:
    logger.error(f"Failed to record runner spawn: {e}")
    
    # Debug 模式下中断
    if os.getenv("AGENTOS_DEBUG") == "1":
        raise
    
    # 生产模式下记录到 audit（至少留下痕迹）
    try:
        self.task_manager.add_audit(
            task_id=task_id,
            event_type="lineage_write_failed",
            level="error",
            payload={"error": str(e), "kind": "runner_spawn"}
        )
    except:
        pass  # 如果 audit 也失败，无能为力
```

#### 选项 B: 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(0.1))
def add_lineage_with_retry(self, ...):
    self.task_manager.add_lineage(...)
```

#### 选项 C: 缓冲队列（复杂但健壮）

```python
# 如果 lineage 写入失败，缓存到内存队列
# 定期 flush 或在 runner_exit 时批量写入
```

### P3 TechDebt 任务

**任务 ID**: `P3-DEBT-1`  
**优先级**: P1（影响审计完整性）  
**实施阶段**: P3 或独立 TechDebt sprint  

**验收标准**:
1. Debug 模式下 lineage 写入失败必须 raise
2. 生产模式下必须至少写入 `lineage_write_failed` audit
3. E2E 测试模拟 lineage 写入失败场景

---

## 🔒 铁律 3: Pause Checkpoint 唯一性（P0-2 已冻结）

### 规则

> **V1 只能在 `open_plan` checkpoint 暂停，任何其他 checkpoint 必须被 PauseGate 拒绝**

### 实现

```python
# pause_gate.py
class PauseCheckpoint(str, Enum):
    OPEN_PLAN = "open_plan"
    
    @classmethod
    def is_valid_v1(cls, checkpoint: str) -> bool:
        return checkpoint == cls.OPEN_PLAN.value

def enforce_pause_checkpoint(checkpoint: str) -> None:
    if not PauseCheckpoint.is_valid_v1(checkpoint):
        raise PauseGateViolation(f"Invalid checkpoint: {checkpoint}")
```

**已在 P0-2 冻结，本条作为存档记录。**

---

## 🔒 铁律 4: Mode Gate 强制执行（P1 已验证）

### 规则

> **非 `implementation` mode 禁止 `apply_diff` / `commit`，必须由 ExecutorEngine 裁决**

### 实现

```python
# executor_engine.py
def apply_diff_or_raise(self, ...):
    if not self.mode.allows_commit():
        raise ModeGateViolation(f"Mode {self.mode.name} does not allow commit")
```

**已在 P1 验证，本条作为存档记录。**

---

## 🔒 铁律 5: Task Trace Timeline 必需条目（P2-4 已验证）

### 规则

> **E2E 测试必须断言以下 timeline 条目存在，缺失任何一项视为测试失败**

**必需条目**（P2 版本）:
1. `runner_spawn` - 至少 1 次（resume 场景至少 2 次）
2. `pipeline` - 真实 pipeline 执行时必须有
3. `execution_request` - open_plan 相关
4. `pause_checkpoint` - 如果 run_mode 需要暂停
5. `approval` - 如果从 awaiting_approval 恢复
6. `resume` - 如果调用了 resume 命令（P2-C2）
7. `runner_exit` - 至少 1 次（resume 场景至少 2 次）
8. `artifact` - open_plan artifact（P2-C1）

### 验收

```python
required_timeline_kinds = {
    "runner_spawn": False,
    "pipeline": False,
    ...
}

for entry in trace.timeline:
    if entry.kind in required_timeline_kinds:
        required_timeline_kinds[entry.kind] = True

assert all(required_timeline_kinds.values()), "Timeline missing required entries"
```

**已在 P2-4 E2E 测试中强制执行。**

---

## 📋 契约版本历史

| 版本 | 日期 | 新增铁律 | 修改原因 |
|------|------|----------|----------|
| v1.0 | 2026-01-26 | 铁律 1, 2 | P2-C 收口后文档化 |
| v0.2 | 2026-01-20 | 铁律 3, 4, 5 | P0-P2 冻结规则归档 |

---

## 🚨 违反铁律的后果

| 铁律 | 违反后果 | 检测方式 |
|------|---------|----------|
| 铁律 1 | runner 追踪混乱，审计失效 | E2E 测试 fail（两次 runner_spawn） |
| 铁律 2 | 审计数据静默丢失 | 生产监控告警（待 P3 实现） |
| 铁律 3 | 暂停点漂移，用户体验不一致 | PauseGate 运行时 raise |
| 铁律 4 | 破坏性动作泄漏到非 impl mode | Mode Gate 运行时 raise |
| 铁律 5 | Trace 不完整，无法回溯 | E2E 测试 fail |

---

## 📚 相关文档

- `CLI_P0_CLOSEOUT.md` - PauseGate 和 runner lineage 设计
- `CLI_P1_COMPLETION.md` - Mode Gate 和真实 pipeline 集成
- `CLI_P2_CLOSEOUT.md` - Artifact 和 resume 审计
- `CLI_ARCHITECTURE.md` - 整体架构设计

---

**维护者**: 前端架构团队 + CLI 工作组  
**最后更新**: 2026-01-26  
**状态**: 🟢 生效中 - 强制执行
