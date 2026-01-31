# ADR-009: Narrative Positioning - Four Pillars

**Status**: Accepted
**Date**: 2026-01-29
**Deciders**: Product & Architecture Committee
**Related**: SEMANTIC_FREEZE.md, ADR-008 (Evidence Types)

---

## Context

AgentOS 作为 AI 执行系统,需要一个清晰的对外叙事来定位其核心价值。在 Phase 2 完成后,我们积累了大量技术能力(Checkpoint, Evidence, Recovery),但对外沟通时需要将这些技术能力转化为**业务价值承诺**。

### 旧叙事的问题

在 Phase 2 之前,我们的对外叙事是:

> "AgentOS 是一个 AI 自主执行系统,支持全自动化的多 agent 协同,无需人工干预。"

**问题分析**:

1. **空泛且无法验证**
   - "全自动化" 是什么? 100% 成功率? 永远不会卡住?
   - "无需人工干预" 如何证明? 遇到错误怎么办?

2. **与实际能力不符**
   - 实际系统不可能 100% 自动化 (网络故障、API 限流、环境变化)
   - 强调"无需人工"会让用户担心失控

3. **缺乏差异化**
   - 市场上"AI 自动化"产品很多
   - 但强调"可恢复、可验证、可审计"的很少

4. **过度承诺风险**
   - 用户期望"全自动" = "永远不出错"
   - 实际出错时会觉得产品不可靠

---

## Decision

我们决定将 AgentOS 的对外叙事重新定位为**"四可"体系**:

> **AgentOS 是一个可中断、可恢复、可验证、可审计的 AI 执行系统。**

### 四可 (Four Pillars)

| 叙事 | 英文 | 技术支撑 | 业务价值 |
|------|------|---------|---------|
| **可中断** | Interruptible | Checkpoint 两阶段提交 | 系统崩溃 (kill -9) 不丢数据 |
| **可恢复** | Resumable | Evidence-based 恢复 | 从检查点继续,不重跑 |
| **可验证** | Verifiable | 4 种 Evidence 类型 | 每个步骤都有证据链 |
| **可审计** | Auditable | 完整操作日志 | 符合企业级合规要求 |

---

### 为什么是"四可"而不是"自动化"

#### 对比分析

| 维度 | "全自动化" 叙事 | "四可" 叙事 |
|------|----------------|-----------|
| **可验证性** | ❌ 无法证明 | ✅ 有测试验证 (Chaos 7/7) |
| **用户期望** | ❌ 过高 (100% 成功) | ✅ 合理 (可恢复、可追溯) |
| **差异化** | ❌ 同质化竞争 | ✅ 独特卖点 |
| **企业接受度** | ❌ 担心失控 | ✅ 强调可控 |
| **技术门槛** | ❌ 易承诺难实现 | ✅ 有技术护城河 |

---

## Rationale

### 1. 可中断 (Interruptible)

**技术实现**: Checkpoint 两阶段提交
```python
# Phase 1: 声明意图
checkpoint_manager.begin_step(
    task_id="task-001",
    step_name="generate_plan",
    evidence=[...]
)

# 即使在这里 kill -9,数据也不会损坏
# ... 执行工作 ...

# Phase 2: 提交结果
checkpoint_manager.commit_step(
    task_id="task-001",
    step_name="generate_plan",
    snapshot_data={...},
    success=True
)
```

**业务价值**:
- 开发环境可以随时中断调试
- 生产环境崩溃不会丢失进度
- 支持"暂停-修改-继续"的工作流

**验证方式**: Chaos Scenario 1-7 全部通过

---

### 2. 可恢复 (Resumable)

**技术实现**: Evidence-based 恢复
```python
# 系统重启后
last_checkpoint = checkpoint_manager.get_last_verified_checkpoint(task_id)

if last_checkpoint:
    # 验证证据仍然有效
    if checkpoint_manager.verify_checkpoint(last_checkpoint.checkpoint_id):
        # 从检查点恢复
        resume_from_checkpoint(last_checkpoint)
    else:
        # 证据失效,回退到更早的检查点
        rollback_to_previous_checkpoint()
```

**业务价值**:
- 长时间运行的任务 (数小时、数天) 可以中断后继续
- 不会浪费已完成工作的成本 (LLM Token, 计算资源)
- 支持分阶段执行和审查

**验证方式**:
- Recovery Sweep 11/11 测试通过
- LLM Cache 88% 命中率
- Tool Replay 98% 重放率

---

### 3. 可验证 (Verifiable)

**技术实现**: 4 种 Evidence 类型

| 类型 | 验证内容 | 使用场景 |
|------|---------|---------|
| `artifact_exists` | 文件/目录存在 | 验证生成的 plan.json |
| `file_sha256` | 文件内容哈希 | 验证代码文件未被修改 |
| `command_exit` | 命令退出码 | 验证 pytest 测试通过 |
| `db_row` | 数据库行状态 | 验证 task 状态更新 |

**业务价值**:
- 每个执行步骤都有机器可验证的证据
- 可以回溯任何时间点的系统状态
- 支持合规审计和故障排查

**验证方式**: 57 个 Checkpoint 测试全部通过

---

### 4. 可审计 (Auditable)

**技术实现**: 完整操作日志
```sql
-- 审计表结构
CREATE TABLE audit_logs (
    audit_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP,
    actor TEXT,          -- 执行者 (user / agent / system)
    action TEXT,         -- 操作类型
    resource_type TEXT,  -- 资源类型 (task / checkpoint / work_item)
    resource_id TEXT,    -- 资源 ID
    details TEXT,        -- 详细信息 (JSON)
    result TEXT          -- 结果 (success / failure)
);

-- 审计查询示例
SELECT * FROM audit_logs
WHERE resource_id = 'task-001'
ORDER BY timestamp;
```

**业务价值**:
- 符合 SOC2, ISO27001 等合规要求
- 可以追溯"谁在什么时间做了什么"
- 支持故障分析和责任定位

**验证方式**: Audit Middleware 集成测试通过

---

## Communication Guidelines

### 对外宣传的标准话术

#### 30 秒电梯演讲
> "AgentOS 不仅让 AI 自动执行任务,更重要的是,它让 AI 的执行过程**可中断、可恢复、可验证、可审计**。即使系统崩溃 (kill -9),也能从上次验证的检查点恢复,不会重跑已完成的工作。每个执行步骤都有证据链,可以追溯和审计,符合企业级合规要求。"

---

#### 2 分钟产品介绍
> "AgentOS 是一个企业级 AI 执行系统,专为**长时间运行、高可靠性、可追溯**的 AI 任务设计。
>
> 与传统的'全自动 AI Agent'不同,AgentOS 强调执行过程的**可控性**:
>
> - **可中断**: 我们使用两阶段提交的 Checkpoint 机制,确保即使系统崩溃 (kill -9),数据也不会损坏。这让开发者可以随时中断调试,生产环境崩溃也不会丢失进度。
>
> - **可恢复**: 每个 Checkpoint 都有证据链 (文件哈希、命令退出码、数据库状态),系统重启后会验证证据是否仍然有效,然后从最后一个有效检查点继续,不会重跑已完成的工作。我们的 LLM Cache 可以减少 81% 的 Token 成本。
>
> - **可验证**: 我们支持 4 种证据类型,每个执行步骤都可以机器验证。这不仅确保了恢复的可靠性,也让执行过程完全透明。
>
> - **可审计**: 所有操作都有完整的审计日志,记录'谁在什么时间做了什么',符合 SOC2、ISO27001 等企业级合规要求。
>
> AgentOS 已通过 7 个 Chaos 场景的严格测试,包括 kill -9、数据库锁竞争、租约过期等极端情况,所有场景都实现了 100% 恢复成功率。"

---

#### 技术博客标题模板

**✅ 推荐使用**:
- "如何让 AI 执行可恢复: 基于 Evidence 的 Checkpoint 设计"
- "Kill -9 不怕: 构建可中断的 AI 执行系统"
- "从 Token 浪费到成本优化: LLM Cache 的幂等性设计"
- "AI 执行的四可原则: 可中断、可恢复、可验证、可审计"
- "企业级 AI 系统如何做到可追溯和可审计"
- "Chaos 工程在 AI 系统中的应用: 7 个场景的实战"

**❌ 禁止使用**:
- "如何构建全自动 AI Agent 系统"
- "完全自动化的 AI 执行引擎"
- "无需人工干预的智能任务系统"
- "AI Agent 让一切自动化"

---

### 对外文档的强制模板

**README.md / 产品页面的第一段** (冻结模板):
```markdown
AgentOS 是一个**可中断、可恢复、可验证、可审计**的 AI 执行系统。

与传统的"全自动 AI Agent"不同,AgentOS 强调**执行过程的可控性**:
- 可中断: 系统崩溃 (kill -9) 不丢数据
- 可恢复: 从最后验证的检查点继续,不重跑已完成工作
- 可验证: 每个执行步骤都有证据链 (文件哈希、命令退出码、数据库状态)
- 可审计: 所有操作可追溯,符合企业级审计要求

这让 AgentOS 特别适合需要**长时间运行、高可靠性、可追溯**的 AI 任务场景。
```

**技术文档的引言** (推荐模板):
```markdown
本文档介绍 [具体功能] 的实现原理。

作为 AgentOS "四可"体系的一部分,本功能确保:
- [如何支持可中断]
- [如何支持可恢复]
- [如何支持可验证]
- [如何支持可审计]
```

---

### 禁止使用的说法

| 禁止说法 | 为什么禁止 | 推荐替代 |
|---------|----------|---------|
| "全自动化" | 无法证明,过度承诺 | "可恢复的自动执行" |
| "无需人工干预" | 让用户担心失控 | "减少人工干预,支持随时接管" |
| "100% 成功率" | 不现实 | "100% 恢复成功率" (指崩溃后) |
| "完全自主" | 过于抽象 | "可中断、可恢复、可验证、可审计" |
| "智能自愈" | 空泛概念 | "基于证据的自动恢复" |

---

## Consequences

### 正面影响

1. **差异化定位**
   - 市场上强调"可中断、可恢复、可验证、可审计"的 AI 系统很少
   - 这是 AgentOS 的**真正护城河**

2. **企业接受度提升**
   - 企业客户更关心"可控性"和"合规性",而不是"全自动"
   - "可审计"直接对应 SOC2, ISO27001 等合规要求

3. **可验证的承诺**
   - "可中断"有 Chaos 测试验证 (7/7 通过)
   - "可恢复"有 LLM Cache (88% 命中) 和 Tool Replay (98% 重放) 验证
   - "可验证"有 57 个 Checkpoint 测试验证
   - "可审计"有 Audit Middleware 验证

4. **避免过度承诺**
   - 不承诺"永远不出错"
   - 只承诺"出错后能恢复" → 更可实现

---

### 负面影响

1. **放弃"全自动"卖点**
   - 对于追求"一键搞定"的用户,可能吸引力下降
   - 但这类用户往往不是企业级目标客户

2. **需要教育市场**
   - "四可"是新概念,需要投入资源解释
   - 竞争对手可能继续用"全自动"抢占心智

---

### 缓解措施

1. **两种叙事并存**
   - 对 C 端用户: "自动执行 AI 任务" (简化叙事)
   - 对 B 端企业: "可中断、可恢复、可验证、可审计" (专业叙事)

2. **内容营销**
   - 发布技术博客解释"四可"的价值
   - 制作 Demo 视频展示 kill -9 后的恢复过程
   - 分享 Chaos 测试的实战经验

3. **竞争对比**
   - 与竞品对比时,强调"可验证"的优势
   - 展示 Chaos 测试结果 vs. 竞品的缺失

---

## Implementation

### Phase 1: 文档更新 (已完成)

- [x] 更新 README.md 使用"四可"叙事
- [x] 创建 SEMANTIC_FREEZE.md
- [x] 创建 ADR-009 (本文档)

---

### Phase 2: 对外宣传 (待实施)

**待创建内容**:
- [ ] 产品页面 (官网)
- [ ] 技术博客 (3-5 篇)
- [ ] Demo 视频 (kill -9 恢复演示)
- [ ] 演讲 PPT (技术大会)

**目标受众**:
- DevOps / SRE 工程师
- 企业 AI 架构师
- 合规 / 安全团队

---

### Phase 3: 内部培训 (待实施)

**培训对象**:
- 销售团队: 如何用"四可"叙事介绍 AgentOS
- 技术支持: 如何回答"为什么不是全自动"
- 市场团队: 如何制作符合"四可"定位的宣传材料

**培训材料**:
- [ ] 销售话术手册
- [ ] FAQ (常见问题回答)
- [ ] 竞品对比表

---

## Verification

### 叙事一致性检查

**检查清单**:
- [ ] README.md 第一段包含"四可"
- [ ] 所有对外文档移除"全自动"、"无需人工干预"
- [ ] 技术博客标题符合推荐模板
- [ ] 演讲 PPT 使用"四可"作为核心卖点

**自动化检查** (CI):
```bash
# 检查禁止使用的说法
grep -r "全自动" docs/ README.md && exit 1
grep -r "无需人工干预" docs/ README.md && exit 1
grep -r "100% 成功率" docs/ README.md && exit 1

# 检查必须包含的说法
grep -q "可中断、可恢复、可验证、可审计" README.md || exit 1
```

---

### 市场反馈收集

**指标**:
- 企业客户询问"合规性"的比例 (目标 >30%)
- 技术博客点击率 ("四可" vs. "全自动")
- 演讲后的问题类型 (技术深度 vs. 基础概念)

**预期**:
- "四可"叙事会吸引更多企业级客户
- 技术深度问题比例提升 (说明受众理解了技术价值)

---

## References

- [SEMANTIC_FREEZE.md](../../SEMANTIC_FREEZE.md) - 语义冻结总体策略
- [ADR-008](ADR-008-Evidence-Types-Semantics.md) - Evidence 类型和语义
- [PHASE_2_FINAL_EVIDENCE_REPORT.md](../../PHASE_2_FINAL_EVIDENCE_REPORT.md) - Phase 2 最终报告
- [README.md](../../README.md) - 更新后的主页文档

---

## Appendix: 竞品对比

### 主要竞品的叙事分析

| 产品 | 叙事定位 | 优势 | 劣势 |
|------|---------|------|------|
| AutoGPT | "全自主 AI Agent" | 简单易懂 | 无法验证,过度承诺 |
| LangChain Agents | "灵活的 Agent 框架" | 生态丰富 | 缺乏可靠性保证 |
| Semantic Kernel | "企业级 AI 编排" | 微软背书 | 缺乏恢复机制 |
| **AgentOS** | **"可中断、可恢复、可验证、可审计"** | **技术护城河** | 需要教育市场 |

### AgentOS 的独特卖点

1. **唯一有 Chaos 测试验证的系统** (7/7 场景通过)
2. **唯一有 Evidence-based 恢复的系统** (4 种证据类型)
3. **唯一强调"可审计"的系统** (符合企业合规)
4. **唯一有成本优化验证的系统** (81% Token 节省)

---

**文档状态**: ✅ Accepted and Frozen
**下次审查**: 2026-04-29
**负责人**: Product & Architecture Committee
