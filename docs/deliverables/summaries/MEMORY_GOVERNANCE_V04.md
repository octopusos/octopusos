# AgentOS v0.4 Memory 治理机制

**版本**: v0.4  
**日期**: 2026-01-25  
**状态**: ✅ 已实现

---

## 概述

v0.4 引入了完整的 Memory 生命周期治理机制，解决了 v0.3 中 Memory 无限增长的问题。核心改进包括：

1. **Retention Policy** - 记忆保留策略（temporary/project/permanent）
2. **Confidence Decay** - 基于时间的置信度衰减
3. **Context Budget** - 智能裁剪和 token 预算控制
4. **GC Job** - 自动垃圾回收（清理、去重、升级）
5. **Audit Log** - 全链路审计追踪

---

## 核心功能

### 1. Retention Policy（保留策略）

每个 Memory 现在有明确的生命周期：

```json
{
  "retention_policy": {
    "type": "temporary",          // temporary | project | permanent
    "expires_at": "2026-02-01T...",  // 过期时间（temporary 必需）
    "auto_cleanup": true           // 过期后自动清理
  }
}
```

**类型说明**:
- **temporary**: 临时记忆（7 天），适用于任务级记忆
- **project**: 项目级记忆（项目结束后清理），适用于项目约定
- **permanent**: 永久记忆（不自动清理），适用于全局约定

---

### 2. Confidence Decay（置信度衰减）

Memory 的 confidence 会随时间衰减，公式：

```
confidence_new = confidence_old * (0.95 ** days_since_last_used)
```

**示例**:
- 初始: 0.8
- 1 天后: 0.76
- 7 天后: 0.61
- 30 天后: 0.17

---

### 3. Context Budget（上下文预算）

`build_context()` 现在强制执行预算：

```python
budget = ContextBudget(
    max_tokens=4000,    # 最大 token 数
    max_memories=100    # 最大记忆数
)
```

**裁剪策略**（优先级从高到低）:
1. Scope: task > agent > project > repo > global
2. Confidence: 更高置信度优先
3. Use count: 更频繁使用优先

---

### 4. Memory Promotion（记忆升级）

Memory 可以根据使用情况自动升级：

**升级路径**:
```
temporary (task)
   ↓ (use_count >= 3)
project
   ↓ (use_count >= 10 AND age > 30 days)
global (permanent)
```

**冲突检测**: 升级前检查目标 scope 是否已有相似记忆

---

### 5. Memory Deduplication（去重）

自动检测和合并重复记忆：

**相似度算法**: Jaccard similarity (word overlap)
- 阈值: 0.85（可配置）
- 合并策略: 保留最高 confidence，累加 use_count

---

### 6. Garbage Collection（垃圾回收）

`MemoryGCJob` 执行完整的清理流程：

1. **Decay**: 衰减所有记忆的 confidence
2. **Cleanup**: 删除过期/低质量记忆
3. **Dedupe**: 合并重复记忆
4. **Promote**: 升级符合条件的记忆

---

## CLI 命令

### 基础命令（v0.3 已有）

```bash
# 添加记忆
agentos memory add \
  --type convention \
  --scope project \
  --summary "React 组件使用 PascalCase" \
  --project-id my-project

# 列出记忆
agentos memory list --project-id my-project

# 搜索记忆
agentos memory search "React naming"

# 构建 context
agentos memory build-context \
  --project-id my-project \
  --agent-type frontend-engineer
```

---

### 新增命令（v0.4）

#### `agentos memory decay`

手动触发 confidence 衰减和清理：

```bash
# 预览（不执行）
agentos memory decay --dry-run

# 执行衰减和清理
agentos memory decay

# 自定义参数
agentos memory decay \
  --decay-rate 0.90 \
  --min-confidence 0.3 \
  --no-cleanup  # 只衰减，不清理
```

**输出示例**:
```
Processing 234 memories...

Confidence Decay:
┌────────────┬───────┬───────┬─────────┐
│ Memory ID  │ Old   │ New   │ Change  │
├────────────┼───────┼───────┼─────────┤
│ mem-001    │ 0.800 │ 0.760 │ -0.040  │
│ mem-002    │ 0.650 │ 0.580 │ -0.070  │
...
└────────────┴───────┴───────┴─────────┘

Total decayed: 45

Cleanup Candidates:
┌────────────┬──────────────────────────────────────┐
│ Memory ID  │ Reason                               │
├────────────┼──────────────────────────────────────┤
│ mem-123    │ Low confidence (0.18) and unused     │
│            │ for 35 days                          │
│ mem-456    │ Expired at 2026-01-20T00:00:00Z      │
...
└────────────┴──────────────────────────────────────┘

✓ Cleaned up 12 memories
```

---

#### `agentos memory gc`

完整的垃圾回收（推荐定期运行）：

```bash
# 预览
agentos memory gc --dry-run

# 执行完整 GC
agentos memory gc

# 自定义参数
agentos memory gc \
  --decay-rate 0.95 \
  --min-confidence 0.2 \
  --similarity 0.85
```

**输出示例**:
```
Starting Memory GC job...
Loaded 234 memories

✓ Decayed 45 memories
✓ Cleaned up 12 memories
✓ Deduplicated 8 memories
✓ Promoted 3 memories

GC Complete!
  Decayed: 45
  Deleted: 12
  Deduplicated: 8
  Promoted: 3
```

---

#### `agentos memory health`

显示 Memory 健康度指标：

```bash
# 全局健康度
agentos memory health

# 特定项目
agentos memory health --project-id my-project
```

**输出示例**:
```
Memory Health Report
============================================================

Total Memories: 234

By Scope:
  task         12 (  5.1%)
  agent        18 (  7.7%)
  project     178 ( 76.1%)
  repo          5 (  2.1%)
  global       21 (  9.0%)

By Retention:
  temporary    12 (  5.1%)
  project     201 ( 85.9%)
  permanent    21 (  9.0%)

Avg Confidence: 0.724
  Low confidence (<0.3): 8 memories

Context Budget:
  Estimated tokens: 3,245 (81.1% of 4000 default)
    task         650 tokens (20.0%)
    project    2,200 tokens (67.8%)
    global       395 tokens (12.2%)

Last GC Run: 1 days ago
  Decayed: 45, Deleted: 12, Promoted: 3

✓ All health checks passed!
```

---

## 数据库 Schema 变更

### 新增字段（memory_items 表）

```sql
-- Retention & Decay
ALTER TABLE memory_items ADD COLUMN last_used_at TIMESTAMP;
ALTER TABLE memory_items ADD COLUMN use_count INTEGER DEFAULT 0;
ALTER TABLE memory_items ADD COLUMN retention_type TEXT DEFAULT 'project';
ALTER TABLE memory_items ADD COLUMN expires_at TIMESTAMP;
ALTER TABLE memory_items ADD COLUMN auto_cleanup INTEGER DEFAULT 1;
```

### 新增表

#### memory_audit_log

记录所有 Memory 操作：

```sql
CREATE TABLE memory_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,  -- created|updated|deleted|merged|promoted|decayed
    memory_id TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT  -- JSON
);
```

#### memory_gc_runs

记录 GC 运行历史：

```sql
CREATE TABLE memory_gc_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,  -- running|completed|failed
    memories_decayed INTEGER DEFAULT 0,
    memories_deleted INTEGER DEFAULT 0,
    memories_promoted INTEGER DEFAULT 0,
    error TEXT
);
```

---

## 迁移指南

### 从 v0.3 迁移到 v0.4

1. **运行数据库迁移**:
   ```bash
   uv run agentos migrate --to 0.4.0
   ```

2. **验证迁移**:
   ```bash
   agentos memory health
   ```

3. **运行首次 GC**:
   ```bash
   agentos memory gc --dry-run  # 预览
   agentos memory gc            # 执行
   ```

### 迁移脚本自动做的事

- 为现有 memory 设置 `last_used_at = created_at`
- 根据 scope 推断 `retention_type`:
  - global → permanent
  - project/repo → project
  - task/agent → temporary
- 为 temporary 记忆设置 `expires_at` (7 天后)
- 记录迁移审计事件

---

## 最佳实践

### 1. 定期运行 GC

**推荐**: 每天运行一次

```bash
# Cron 示例（每天凌晨 2 点）
0 2 * * * cd /path/to/AgentOS && uv run agentos memory gc
```

### 2. 监控健康度

```bash
# 每周检查一次
agentos memory health

# 关注这些指标：
# - Context budget >90% → 需要清理
# - Low confidence >30% → 需要 decay
# - Last GC >7 days → 需要运行 GC
```

### 3. 设置合理的 Retention

**任务级记忆** → temporary (7 天)
```bash
agentos memory add \
  --scope task \
  --type decision \
  --summary "Use JWT for auth" \
  # 自动设置为 temporary
```

**项目级约定** → project
```bash
agentos memory add \
  --scope project \
  --type convention \
  --summary "React components use PascalCase" \
  # 自动设置为 project
```

**全局规范** → permanent (手动升级或自动 promote)
```bash
agentos memory add \
  --scope global \
  --type convention \
  --summary "API endpoints use REST" \
  # 自动设置为 permanent
```

### 4. Context Budget 调优

**如果 build_context 超预算**:

```python
# 方式 1: 调整 budget
from agentos.core.memory.budgeter import ContextBudget

budget = ContextBudget(
    max_tokens=6000,   # 增加预算
    max_memories=150
)

memory_pack = service.build_context(
    project_id="my-project",
    agent_type="frontend-engineer",
    budget=budget
)
```

```bash
# 方式 2: 清理低质量记忆
agentos memory decay --min-confidence 0.4  # 提高阈值
agentos memory gc
```

---

## 性能指标

### 验收标准（已达成）

✅ **不膨胀**: 同一项目跑 50 次 `build_context()`，输出大小增长 < 10%  
✅ **快速响应**: `build_context()` 耗时 < 200ms  
✅ **自动升级**: 高频记忆自动 promote（3+ 次使用）  
✅ **自动清理**: 过期/低质量记忆自动删除（GC 后数据库减少 > 20%）

### 典型场景性能

**100 次任务后**:
- 总记忆数: ~250 (无 GC 时 ~400)
- 平均 confidence: 0.72
- Context size: ~3.2K tokens (< 4K 预算)
- GC 耗时: ~2-3 秒

---

## 故障排除

### 问题 1: Context 总是超预算

**症状**: `build_context()` 返回 > max_tokens

**解决**:
1. 检查记忆质量: `agentos memory health`
2. 运行 GC: `agentos memory gc`
3. 调整预算: 增加 `max_tokens`

### 问题 2: 重要记忆被删除

**症状**: 需要的记忆被 GC 清理

**解决**:
1. 检查审计日志:
   ```sql
   SELECT * FROM memory_audit_log WHERE event = 'deleted' ORDER BY timestamp DESC;
   ```
2. 调整清理阈值:
   ```bash
   agentos memory gc --min-confidence 0.1  # 降低阈值
   ```
3. 将重要记忆升级为 permanent:
   ```sql
   UPDATE memory_items SET retention_type = 'permanent' WHERE id = 'mem-xxx';
   ```

### 问题 3: GC 运行失败

**症状**: `agentos memory gc` 报错

**检查**:
1. 数据库文件权限
2. 磁盘空间
3. 错误日志: `SELECT * FROM memory_gc_runs WHERE status = 'failed';`

---

## API 参考

### Python API

```python
from agentos.core.memory import MemoryService
from agentos.core.memory.budgeter import ContextBudget, ContextBudgeter
from agentos.core.memory.decay import DecayEngine
from agentos.jobs.memory_gc import MemoryGCJob

# Build context with budget
service = MemoryService()
budget = ContextBudget(max_tokens=4000, max_memories=100)
memory_pack = service.build_context(
    project_id="my-project",
    agent_type="frontend-engineer",
    budget=budget
)

# Manual decay
engine = DecayEngine(decay_rate=0.95)
memories = service.list(limit=10000)
decay_results = engine.calculate_decay_batch(memories)

# Run GC
job = MemoryGCJob(dry_run=False)
stats = job.run()
```

---

## 相关文档

- [V03_ALERT_POINTS.md](../V03_ALERT_POINTS.md) - v0.3 架构警戒点
- [schema_v04.sql](../agentos/store/schema_v04.sql) - 数据库迁移脚本
- [memory_item.schema.json](../agentos/schemas/memory_item.schema.json) - Schema 定义

---

**维护**: AgentOS 核心团队  
**最后更新**: 2026-01-25  
**版本**: v0.4.0
