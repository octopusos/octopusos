# ADR-010: No Premature Parallelization

**Status**: Accepted
**Date**: 2026-01-29
**Deciders**: Architecture Committee
**Related**: SEMANTIC_FREEZE.md, ADR-007 (Database Write Serialization)

---

## Context

Phase 2 恢复系统完成后,系统具备了基础的 work_items 管理能力。理论上可以实现并行执行多个 work_items 来提升吞吐量。但我们需要决定:**现在是否应该实现并行化?**

### 当前状态

**串行执行模型**:
```python
# 当前: 一次只执行一个 work_item
while True:
    lease = lease_manager.acquire_lease()
    if lease:
        execute_work_item(lease)
        lease_manager.release_lease(lease.work_item_id, success=True)
    else:
        break
```

**特点**:
- ✅ 执行顺序完全可预测
- ✅ 日志线性,易于追踪
- ✅ 失败定位明确 (单点失败)
- ✅ Chaos 测试覆盖充分 (7/7 场景)
- ⚠️ 吞吐量有限 (单线程)

---

### 并行化的诱惑

**并行执行模型** (如果实现):
```python
# 诱惑: 同时执行多个 work_items
with ThreadPoolExecutor(max_workers=4) as executor:
    leases = [lease_manager.acquire_lease() for _ in range(4)]
    futures = [executor.submit(execute_work_item, lease) for lease in leases if lease]
    # 并行执行
    for future in as_completed(futures):
        result = future.result()
        # ... 处理结果 ...
```

**预期收益**:
- ✅ 吞吐量提升 2-4x (理论值)
- ✅ CPU 利用率提升
- ✅ 长时间运行任务的总时间减少

**但实际代价**:
- ❌ 竞争条件 (文件、数据库)
- ❌ 死锁风险 (资源依赖)
- ❌ 部分失败复杂性
- ❌ 日志交错,难以调试
- ❌ Chaos 测试需要重新设计
- ❌ Evidence 验证复杂化

---

## Decision

我们决定**在 Phase 3 之前,不实现 work_items 并行化**。

### 核心原则

> **串行执行是优势,不是劣势**

在企业级 AI 执行场景,"可解释性 + 可追溯性 + 可靠性" 比 "速度快" 更重要。

---

## Rationale

### 1. 当前的串行执行是竞争优势

#### 可解释性 (Explainability)

**串行执行**:
```
Task-001 > Work-Item-1 > Work-Item-2 > Work-Item-3
          ↓              ↓              ↓
       Step 1         Step 2         Step 3
          ↓              ↓              ↓
     Checkpoint-1   Checkpoint-2   Checkpoint-3
```
- 执行顺序完全确定
- 日志线性,易于理解
- 可以画出清晰的执行时间线

**并行执行**:
```
Task-001 > Work-Item-1 ────────────┐
          ├> Work-Item-2 ─────┐    ├> 结果合并
          └> Work-Item-3 ──┐  ├───┘
                          ↓  ↓  ↓
                    日志交错,难以追踪
```
- 执行顺序不确定
- 日志交错,需要关联分析
- 无法简单画出执行时间线

**结论**: 串行执行的可解释性是企业客户看重的核心能力。

---

#### 失败可定位 (Debuggability)

**串行执行的故障分析**:
```bash
# 查看失败的 work_item
SELECT * FROM work_items WHERE status = 'failed' ORDER BY started_at;

# 查看失败时的 checkpoint
SELECT * FROM checkpoints WHERE task_id = 'task-001' ORDER BY sequence_number DESC LIMIT 1;

# 查看失败的审计日志
SELECT * FROM audit_logs WHERE resource_id = 'work-item-1' ORDER BY timestamp;
```
→ 单点失败,原因明确

**并行执行的故障分析**:
```bash
# 哪个 work_item 先失败的?
SELECT * FROM work_items WHERE status = 'failed' ORDER BY started_at;
# → 可能有多个,需要分析因果关系

# 失败是否有依赖关系?
# → Work-Item-2 失败是因为 Work-Item-1 修改了共享资源?

# 如何重现?
# → 需要重现并发执行顺序,可能无法复现
```
→ 多点失败,因果关系复杂

**结论**: 串行执行的单点失败更容易定位和修复。

---

#### 恢复可验证 (Recoverability)

**串行执行的恢复**:
```python
# 从最后一个验证的 checkpoint 继续
last_checkpoint = get_last_verified_checkpoint(task_id)
resume_from_checkpoint(last_checkpoint)
```
→ 线性恢复,逻辑简单

**并行执行的恢复**:
```python
# 多个 work_items 部分完成,部分失败
completed = get_completed_work_items(task_id)  # [1, 3]
failed = get_failed_work_items(task_id)        # [2]
pending = get_pending_work_items(task_id)      # [4, 5]

# 需要合并状态
if work_item_2_affects_work_item_4:
    # 需要回滚 work_item_4
    rollback_work_item(4)
```
→ 状态合并复杂,需要依赖分析

**结论**: 串行执行的恢复逻辑更简单可靠。

---

### 2. 并行化会引入新的复杂度

#### 2.1 竞争条件 (Race Conditions)

**场景 1: 文件写入竞争**
```python
# Work-Item-1
write_file("output.txt", "Result from Work-Item-1")

# Work-Item-2 (并行执行)
write_file("output.txt", "Result from Work-Item-2")

# → 最终 output.txt 的内容不确定
```

**场景 2: 数据库竞争**
```python
# Work-Item-1
conn.execute("UPDATE tasks SET status = 'processing' WHERE task_id = ?", (task_id,))

# Work-Item-2 (并行执行)
conn.execute("UPDATE tasks SET status = 'completed' WHERE task_id = ?", (task_id,))

# → 最终 task 状态不确定
```

**缓解方案**:
- 文件锁机制
- 数据库事务隔离
- 命名空间隔离 (每个 work_item 独立目录)

**代价**: 需要设计和实现复杂的并发控制机制。

---

#### 2.2 死锁风险 (Deadlocks)

**场景: 资源依赖死锁**
```python
# Work-Item-1 需要资源 A 和 B
acquire_lock(resource_A)
# ... 等待 resource_B ...
acquire_lock(resource_B)

# Work-Item-2 需要资源 B 和 A
acquire_lock(resource_B)
# ... 等待 resource_A ...
acquire_lock(resource_A)

# → 死锁: Work-Item-1 等待 B, Work-Item-2 等待 A
```

**缓解方案**:
- 锁超时机制
- 死锁检测和恢复
- 资源预分配

**代价**: 需要实现死锁检测和恢复机制,增加系统复杂度。

---

#### 2.3 部分失败 (Partial Failures)

**场景: 3 个并行 work_items, 1 个失败**
```python
# 并行执行
results = [
    execute(work_item_1),  # ✅ 成功
    execute(work_item_2),  # ❌ 失败
    execute(work_item_3),  # ✅ 成功
]

# 如何处理?
# 选项 1: 回滚所有 work_items (包括成功的)
rollback_all()

# 选项 2: 只重试失败的 work_item
retry(work_item_2)

# 选项 3: 让用户决定
ask_user_what_to_do()
```

**问题**:
- 回滚成功的 work_item 浪费资源
- 只重试失败的可能导致状态不一致
- 让用户决定增加复杂度

**结论**: 部分失败的处理逻辑非常复杂。

---

#### 2.4 Evidence 验证复杂化

**串行执行的 Evidence**:
```python
# Work-Item-1 完成
evidence = [
    Evidence(type="file_sha256", payload={
        "path": "output.txt",
        "expected_hash": "abc123..."
    })
]
# → 文件 hash 在 Work-Item-1 完成时计算
```

**并行执行的 Evidence**:
```python
# Work-Item-1 和 Work-Item-2 同时写 output.txt
# 什么时候计算 hash?
# - 选项 1: Work-Item-1 完成时 → 可能被 Work-Item-2 覆盖
# - 选项 2: 所有 work_items 完成时 → 无法判断哪个 work_item 的结果

# 如何验证?
# - 选项 1: 记录每个 work_item 的 hash → 需要合并验证
# - 选项 2: 只记录最终 hash → 丧失中间状态验证
```

**结论**: 并行执行会破坏 Evidence-based 恢复的语义。

---

#### 2.5 Chaos 测试需要重新设计

**当前 Chaos 测试的假设**:
- 7 个场景都假设串行执行
- kill -9 只会中断一个 work_item
- 恢复只需要从一个 checkpoint 继续

**并行化后的 Chaos 场景**:
- kill -9 可能中断 2-3 个并行 work_items
- 需要设计 C(n,2) + C(n,3) + ... 种组合场景
- 需要测试竞争条件的恢复
- 需要测试死锁的恢复
- 需要测试部分失败的恢复

**估算工作量**:
- 当前 7 个场景 → 并行化后需要 20+ 个场景
- 每个场景的实现和验证时间: 2-3 天
- **总计: 4-6 周**

**结论**: 并行化的 Chaos 测试成本非常高。

---

### 3. 并行化应该在 Phase 3 (分布式) 一起做

#### 单机并行 vs. 分布式并行

| 维度 | 单机并行 | 分布式并行 |
|------|---------|----------|
| **并发模型** | ThreadPoolExecutor | Celery / RabbitMQ / Redis |
| **租约管理** | 本地内存 | 分布式锁 (Redis / etcd) |
| **Checkpoint 存储** | 本地 SQLite | PostgreSQL / S3 |
| **故障恢复** | 进程级 | 机器级 |
| **扩展性** | 受限于单机 CPU | 可水平扩展 |

**结论**: 单机并行的设计会成为分布式的**技术债**。

---

#### Phase 3 的正确时机

**Phase 3: 分布式 Worker Pool**:
```
Coordinator (Redis / etcd)
    ↓
┌───┴───┬───────┬───────┐
│       │       │       │
Worker-1 Worker-2 Worker-3 Worker-4
(机器1) (机器1) (机器2) (机器2)
    ↓       ↓       ↓       ↓
PostgreSQL / S3 (分布式存储)
```

**特点**:
- 中心化 Coordinator 管理全局租约
- 多台机器并行执行,自然实现并行化
- 分布式 Checkpoint 存储 (PostgreSQL / S3)
- 网络分区、时钟偏移等新的故障场景

**为什么要等到 Phase 3**:
1. **一次性解决并行+容错**: 分布式天然需要并行,设计更合理
2. **避免技术债**: 单机并行的代码在分布式下需要重写
3. **更高的 ROI**: 分布式的吞吐量提升 > 单机并行

**估算收益**:
- 单机并行: 2-4x 吞吐量提升 (受限于单机 CPU)
- 分布式: 10-100x 吞吐量提升 (水平扩展)

**结论**: 不如直接跳到分布式,一次性解决并行+容错问题。

---

### 4. 如何抵制并行化的诱惑

#### 错误的论据 (❌)

**论据 1**: "用户反馈任务执行太慢,需要并行加速"
- **反驳**: 先做性能分析,瓶颈可能是:
  - LLM API 延迟 → 优化: 批量请求、流式输出
  - 网络 I/O → 优化: 异步请求、连接池
  - 数据库查询 → 优化: 索引、缓存
  - **不是串行执行本身**

**论据 2**: "竞争对手都支持并行执行"
- **反驳**: 我们的差异化是"可解释+可审计",不是速度
- 竞争对手的并行执行可能:
  - 没有恢复机制
  - 没有 Chaos 测试验证
  - 部分失败时行为不确定

**论据 3**: "并行化只是加个 ThreadPoolExecutor,很简单"
- **反驳**:
  - 竞争条件: 需要文件锁、数据库事务
  - 死锁: 需要检测和恢复机制
  - 部分失败: 需要复杂的状态合并逻辑
  - Chaos 测试: 需要重新设计 20+ 场景
  - **估算工作量: 5-7 周**

---

#### 正确的回应 (✅)

**回应 1**: "我们在 Phase 3 会支持**分布式并行**,会比单机并行更强大"
- 分布式可以水平扩展,吞吐量提升 10-100x
- 单机并行受限于 CPU,提升有限 (2-4x)

**回应 2**: "当前的串行执行保证了**100% 可追溯**,这是我们的护城河"
- 企业客户更看重可追溯性,不是速度
- 并行化会牺牲可追溯性

**回应 3**: "如果用户需要加速,可以用 LLM Cache (81% 成本节省) 和 Tool Replay (98% 重放率)"
- LLM Cache 减少 88% 的重复 API 调用
- Tool Replay 避免 98% 的重复执行
- **这比并行化更有效**

---

## Consequences

### 正面影响

1. **保护核心优势**
   - 串行执行的可解释性、可追溯性不被破坏
   - "四可"叙事不会因并行化而失效

2. **避免技术债**
   - 单机并行的代码不会成为分布式的负担
   - Phase 3 可以从零开始设计分布式架构

3. **降低 Chaos 测试成本**
   - 当前 7 个场景保持有效
   - 不需要重新设计 20+ 个并发场景

4. **聚焦高价值优化**
   - LLM Cache (81% 成本节省) 比并行化更有价值
   - Tool Replay (98% 重放率) 比并行化更可靠

---

### 负面影响

1. **吞吐量受限**
   - 单线程执行,吞吐量有限
   - 长时间运行任务的总时间较长

2. **CPU 利用率低**
   - 等待 I/O 时 CPU 空闲
   - 多核机器的优势未充分利用

---

### 缓解措施

#### 1. 使用 LLM Cache 和 Tool Replay 优化性能

```python
# LLM Cache: 减少重复 API 调用
llm_cache.get_or_generate(
    operation_type="plan",
    prompt=prompt,
    model="gpt-4",
    generate_fn=lambda: call_llm_api(prompt)
)
# → 88% 命中率,节省 81% Token 成本

# Tool Replay: 避免重复执行
tool_ledger.execute_or_replay(
    tool_name="bash",
    command="pytest tests/",
    execute_fn=lambda: run_command("pytest tests/")
)
# → 98% 重放率,节省 90% 执行时间
```

**效果**: 等价于 5-10x 的吞吐量提升,且不引入并发复杂度。

---

#### 2. 异步 I/O 而不是并行执行

```python
# 使用 asyncio 减少 I/O 等待
async def execute_work_item(work_item):
    # 异步调用 LLM API
    response = await llm_client.generate_async(prompt)

    # 异步写文件
    await async_write_file("output.txt", response)

    # 异步更新数据库
    await db.execute_async("UPDATE tasks SET status = 'completed'")
```

**效果**: CPU 利用率提升,但保持串行执行的可解释性。

---

#### 3. 任务级并行 (而不是 work_item 级)

```python
# 多个独立 task 可以并行执行
with ThreadPoolExecutor(max_workers=4) as executor:
    tasks = ["task-001", "task-002", "task-003", "task-004"]
    futures = [executor.submit(execute_task, task_id) for task_id in tasks]

    # 每个 task 内部仍然是串行的
    for future in as_completed(futures):
        result = future.result()
```

**特点**:
- Task 之间并行 (天然隔离)
- Task 内部串行 (保持可追溯性)
- 不需要修改 work_item 执行逻辑

**效果**: 吞吐量提升,且不破坏单个 task 的可追溯性。

---

## Implementation

### Phase 1: 冻结决策文档化 (已完成)

- [x] 创建 SEMANTIC_FREEZE.md
- [x] 创建 ADR-010 (本文档)
- [x] 更新 README.md

---

### Phase 2: 代码审查机制 (待实施)

**新增 CI 检查**:
```bash
# scripts/check_parallelization.sh
#!/bin/bash

# 检查是否实现了 work_item 并行化
if grep -r "ThreadPoolExecutor.*work_item" agentos/; then
    echo "❌ Error: work_item parallelization detected"
    echo "Refer to ADR-010 for rationale."
    exit 1
fi

if grep -r "ProcessPoolExecutor.*work_item" agentos/; then
    echo "❌ Error: work_item parallelization detected"
    echo "Refer to ADR-010 for rationale."
    exit 1
fi

echo "✅ No premature parallelization detected"
```

---

### Phase 3: 性能优化 (替代并行化)

**优先级排序**:
1. **P0**: LLM Cache (已实现,88% 命中率)
2. **P0**: Tool Replay (已实现,98% 重放率)
3. **P1**: 异步 I/O (asyncio)
4. **P1**: 任务级并行 (Task-level, 不是 work_item-level)
5. **P2**: 数据库查询优化 (索引、缓存)
6. **P2**: LLM API 批量请求

---

## Verification

### 禁止并行化的合规性检查

**自动化检查 (CI)**:
```bash
# 1. 检查代码中是否有并行化实现
./scripts/check_parallelization.sh

# 2. 检查 PR 描述是否提到并行化
if [[ "$PR_TITLE" == *"parallel"* ]]; then
    echo "⚠️  PR title mentions parallelization"
    echo "Please provide ADR justification"
fi
```

**人工审查 (PR Review)**:
- [ ] PR 是否实现了 work_item 并行执行?
- [ ] 如果是,是否提交了 ADR 并通过团队审查?

---

### 性能优化的替代方案验证

**已验证的优化**:
- [x] LLM Cache: 88% 命中率,81% Token 节省
- [x] Tool Replay: 98% 重放率,90% 延迟降低

**待验证的优化**:
- [ ] 异步 I/O: 预期 CPU 利用率提升 30-50%
- [ ] 任务级并行: 预期吞吐量提升 2-4x

---

## Deferred to Phase 3

### 何时可以解除冻结

**解除冻结的前置条件**:
1. ✅ Phase 3 分布式架构设计完成
2. ✅ 选择了中心化 Coordinator (Redis / etcd / PostgreSQL)
3. ✅ 设计了全局租约管理协议
4. ✅ 重新设计 Chaos Matrix (包含并发场景)
5. ✅ 实现了分布式 Checkpoint 存储 (PostgreSQL / S3)
6. ✅ 通过了新的 Chaos 测试 (20+ 场景)

---

### Phase 3 分布式架构草案

**组件**:
```
┌─────────────────────────────────────────┐
│     Coordinator (Redis / etcd)          │
│  - 全局租约管理                          │
│  - Worker 注册表                         │
│  - 任务队列                              │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
│Worker1│ │Worker2│ │Worker3│ │Worker4│
│(机器1)│ │(机器1)│ │(机器2)│ │(机器2)│
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │         │         │
    └─────────┴─────────┴─────────┘
              │
    ┌─────────▼───────────────────┐
    │  PostgreSQL / S3            │
    │  - 分布式 Checkpoint 存储    │
    │  - 审计日志                  │
    └─────────────────────────────┘
```

**关键设计**:
- 全局租约: 使用 Redis SETNX 实现 CAS
- Worker 心跳: 每 30 秒向 Coordinator 报告
- 故障检测: Coordinator 扫描超时的 worker
- Checkpoint 存储: PostgreSQL (支持分布式事务)

---

## References

- [SEMANTIC_FREEZE.md](../../SEMANTIC_FREEZE.md) - 语义冻结总体策略
- [ADR-007](ADR-007-Database-Write-Serialization.md) - 数据库写入序列化
- [ADR-008](ADR-008-Evidence-Types-Semantics.md) - Evidence 类型和语义
- [ADR-009](ADR-009-Narrative-Positioning-Four-Pillars.md) - 四可叙事定位

---

**文档状态**: ✅ Accepted and Frozen
**下次审查**: 2026-04-29 (或 Phase 3 开始时)
**负责人**: Architecture Committee
