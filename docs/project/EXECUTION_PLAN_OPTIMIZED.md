# AgentOS Roadmap 优化执行计划

**版本**: v2 (守门员验收优化版)
**生成时间**: 2026-01-28
**优化依据**: 关键路径分析 + 阻塞关系优化

---

## 🎯 核心优化点

基于守门员验收反馈，执行计划做了以下调整：

### 1. **调整优先级顺序** (最重要)
- ✅ **Task Lifecycle** 优先于 Dashboard（前者是后者和 Supervisor 的地基）
- ✅ **Planning/Execution 强制执行** 优先于可视化（硬闸门比展示重要）
- ✅ **Chat→Task 状态机固化** 前移（Lead Agent 的依赖之一）

### 2. **明确 DoD (Definition of Done)**
Done (100%) 的功能必须满足 5 个维度各 20%：
- 核心代码 (20%)
- 测试 (20%)
- 文档 (20%)
- 集成验证 (20%)
- 运维/观测 (20%)

### 3. **Progress% 可解释**
所有 In Progress 条目的百分比映射到 5 维缺口，可精确追溯。

### 4. **依赖关系显式化**
明确 DAG 关系，不允许上游 <90% 时下游开始实现（可设计）。

---

## 📋 优化后执行序列

### Phase 1: 解锁核心阻塞 (Week 1-4) — **立即执行**

#### Week 1-2: Task Lifecycle 补齐 ⭐ P0
**目标**: 55% → 90%
**为什么优先**: Supervisor/Lead Agent 的基础依赖

**具体任务**:
```
1. Retry 策略实现
   ├─ 指数退避算法 (exponential backoff)
   ├─ 最大重试次数配置
   ├─ 可配置的重试条件
   └─ 审计日志记录每次重试

2. Timeout 控制实现
   ├─ Step-level timeout (单步超时)
   ├─ Task-level timeout (任务总超时)
   ├─ Timeout 触发后的清理逻辑
   └─ 超时审计事件

3. Cancel/Interrupt 语义定义
   ├─ 谁能 cancel (权限模型)
   ├─ Cancel 后的审计链完整性
   ├─ 幂等性保证 (重复 cancel 不出错)
   └─ Cancel 与 Timeout 的交互

4. 集成验证
   ├─ 端到端重试场景测试
   ├─ 端到端超时场景测试
   ├─ 端到端取消场景测试
   └─ 死锁检测验证
```

**交付物**:
- ✅ Retry/Timeout/Cancel 代码 + 测试
- ✅ 操作手册 (如何配置重试策略)
- ✅ 审计事件规范
- ✅ 端到端集成测试通过

---

#### Week 2-3: Planning/Execution 强制执行 ⭐ P0
**目标**: 30% → 70%
**为什么优先**: 没有这个，Supervisor 无法区分哪些操作需要 Guardian

**具体任务**:
```
1. ModeGate 硬闸门实现
   ├─ 不是"建议"，是"强制"
   ├─ 非 implementation mode 禁止破坏性操作
   ├─ ModeViolationError 系统级不可绕过
   └─ Gate 验证在 executor 入口强制执行

2. 操作白名单配置
   ├─ Execution mode 允许的操作清单
   ├─ Planning mode 允许的操作清单
   ├─ 违规操作立即阻断 + 告警
   └─ 白名单配置可热更新

3. 模式转换审计链
   ├─ 每次模式转换记录审计事件
   ├─ 转换原因 + 触发者
   ├─ 违规尝试也记录
   └─ 审计事件不可篡改

4. 测试 + 文档
   ├─ ModeGate 强制执行测试
   ├─ 违规场景测试 (预期阻断)
   ├─ 白名单配置指南
   └─ 模式转换规则文档
```

**交付物**:
- ✅ ModeGate 硬闸门代码 + 测试
- ✅ 白名单配置文件 + 加载机制
- ✅ ModeViolationError 异常处理
- ✅ 模式分离原理文档

---

#### Week 3-4: RAG v1 Git/ADR 索引 + Supervisor 设计
**目标**: RAG 60% → 85%, Supervisor 35% → 50% (设计完成)
**为什么这周**: RAG 对 Lead Agent 间接有用，Supervisor 设计可以和实现分离

**具体任务**:
```
RAG v1 补齐:
1. Git commit 历史索引
   ├─ 解析 git log 并分块
   ├─ 索引 commit message + diff summary
   ├─ 支持按时间/作者/文件路径查询
   └─ 集成到 ProjectKB 统一接口

2. ADR (Architecture Decision Records) 索引
   ├─ 扫描 docs/adr/ 或配置路径
   ├─ 解析 ADR markdown 格式
   ├─ 索引决策背景 + 结论
   └─ 支持决策历史查询

3. 代码符号索引 (可选)
   ├─ 函数/类/模块定义提取
   ├─ 符号索引到 FTS5
   └─ 支持"这个函数在哪"查询

Supervisor 角色设计:
1. 职责边界定义文档
   ├─ Supervisor vs Executor vs Guardian 区别
   ├─ Supervisor 的触发时机
   ├─ Supervisor 的决策权限
   └─ Supervisor 的失败处理

2. 任务状态订阅机制 POC
   ├─ EventBus 订阅 task 状态变更
   ├─ Supervisor 接收 TaskStateChanged 事件
   └─ 伪代码演示订阅逻辑

3. QA 自动化流程设计
   ├─ 验收条件定义 (acceptance criteria)
   ├─ 自动化验收流程图
   └─ Guardian 介入决策树
```

**交付物**:
- ✅ RAG Git/ADR 索引实现 + 测试
- ✅ Supervisor 角色定义文档 (ADR)
- ✅ 状态订阅机制 POC
- ✅ QA 流程伪代码

---

### Phase 2: Supervisor + Lead Agent (Week 5-8) — **短期目标**

#### Week 5-6: Supervisor 完整实现 ⭐ P1
**目标**: 35% → 80%
**前置依赖**: Task Lifecycle (90%) + Planning/Execution (70%)

**具体任务**:
```
1. 任务状态变更订阅
   ├─ EventBus 完整实现
   ├─ Supervisor 订阅 TaskStateChanged
   ├─ 订阅异常处理 + 重试
   └─ 订阅延迟监控

2. QA 自动化流程实现
   ├─ 验收条件解析
   ├─ 自动化验收执行
   ├─ 验收失败 → 创建 follow-up task
   └─ 验收通过 → 标记 succeeded

3. Guardian 介入决策
   ├─ 何时需要 Guardian (规则引擎)
   ├─ Guardian 阻断机制
   ├─ 人工审查接口 (暂时可以是 CLI)
   └─ Guardian 决策记录审计

4. 集成测试 + 文档
   ├─ Supervisor 端到端测试
   ├─ QA 流程端到端测试
   ├─ Guardian 介入场景测试
   └─ Supervisor 操作手册
```

**交付物**:
- ✅ Supervisor 角色完整代码 + 测试
- ✅ EventBus 订阅机制生产就绪
- ✅ QA 自动化流程实现
- ✅ Guardian 介入决策逻辑

---

#### Week 7-8: Lead Agent POC ⭐ P1
**目标**: 5% → 40% (POC 完成)
**前置依赖**: Supervisor (80%) + Task Lifecycle (90%) + RAG (85%)

**具体任务**:
```
1. Cron 调度框架
   ├─ 配置定时任务 (如每日凌晨)
   ├─ 调度器启动 + 停止控制
   ├─ 调度日志审计
   └─ 调度失败告警

2. 风险挖掘逻辑 (基于审计日志)
   ├─ 解析审计日志查找异常模式
   ├─ 风险评分算法 (基于频率/严重性)
   ├─ 风险阈值配置
   └─ 风险报告生成

3. Follow-up 任务创建
   ├─ 从风险报告生成任务建议
   ├─ 任务优先级计算
   ├─ 任务创建调用 TaskManager
   └─ 创建失败回滚

4. 端到端验证
   ├─ 风险 → 任务 → 执行 → 验收 全流程
   ├─ Lead Agent 日志可追溯
   └─ POC Demo 准备
```

**交付物**:
- ✅ Lead Agent 角色 POC 代码
- ✅ Cron 调度框架
- ✅ 风险挖掘逻辑 v1
- ✅ 端到端 Demo

---

### Phase 3: Multi-Agent + MCP 设计 (Week 9-16) — **中期目标**

#### Week 9-12: Multi-Agent 基础
**目标**: 10% → 60%
**前置依赖**: Supervisor (80%) + Lead Agent (40%)

**具体任务**:
```
1. Agent 注册表
   ├─ Agent 元数据定义 (角色/能力/版本)
   ├─ 注册表 CRUD 接口
   ├─ Agent 发现机制
   └─ Agent 健康检查

2. 角色定义正式化
   ├─ Executor / Supervisor / Guardian / Lead 职责文档
   ├─ 角色间通信协议
   ├─ 角色权限模型
   └─ 角色生命周期管理

3. 通信协议
   ├─ Agent 间消息格式定义
   ├─ 消息路由机制
   ├─ 消息确认 + 重试
   └─ 消息审计

4. 治理规则引擎
   ├─ 规则定义语言 (DSL 或 YAML)
   ├─ 规则解析 + 执行引擎
   ├─ 冲突检测
   └─ 规则演进机制
```

**交付物**:
- ✅ Agent 注册表实现
- ✅ 角色定义规范文档
- ✅ Agent 间通信协议
- ✅ 治理规则引擎 v1

---

#### Week 13-16: MCP 架构设计 (不实现，只设计)
**目标**: 0% → 30% (架构设计完成)
**前置依赖**: Multi-Agent (60%)

**具体任务**:
```
1. 三平面协议定义 (ADR)
   ├─ Dev Plane: 代码生成/测试/部署能力
   ├─ Governance Plane: 审批/合规/审计能力
   ├─ Management Plane: 项目/任务/资源管理能力
   └─ 三平面交互边界

2. 适配器抽象层设计
   ├─ MCP 适配器接口定义
   ├─ 适配器注册机制
   ├─ 适配器版本兼容
   └─ 适配器 fallback 策略

3. Capability 注册表设计
   ├─ Capability 元数据定义
   ├─ Capability 发现机制
   ├─ Capability 组合策略
   └─ Capability 权限控制

4. 审计链集成设计
   ├─ 每个 MCP 调用挂到 task 的审计链
   ├─ MCP 调用前置验证
   ├─ MCP 调用后置验证
   └─ MCP 失败处理
```

**交付物**:
- ✅ MCP 三平面架构 ADR
- ✅ 适配器抽象层设计文档
- ✅ Capability 注册表设计
- ✅ 审计链集成设计

---

## 🔗 依赖关系 DAG (可执行版本)

```
Task Lifecycle (W1-2, 55%→90%) ──┐
                                  ├─→ Supervisor (W5-6, 35%→80%) ─→ Lead Agent (W7-8, 5%→40%)
Planning/Execution (W2-3, 30%→70%) ─┘                              │
                                                                    ├─→ Multi-Agent (W9-12, 10%→60%)
RAG v1 (W3-4, 60%→85%) ────────────────────────────────────────────┘
                                                                    │
                                                                    └─→ MCP Design (W13-16, 0%→30%)
                                                                         │
                                                                         └─→ NL-Delivery (未来)
```

---

## ✅ 每周交付物检查清单

### Week 1-2 检查点
- [ ] Retry 策略代码 + 测试 (20%)
- [ ] Timeout 控制代码 + 测试 (20%)
- [ ] Cancel 语义代码 + 测试 (20%)
- [ ] 集成验证端到端通过 (20%)
- [ ] 操作手册 + 审计规范 (20%)
- **验收标准**: Task Lifecycle 达到 90% (符合 DoD)

### Week 2-3 检查点
- [ ] ModeGate 硬闸门代码 + 测试 (30%)
- [ ] 白名单配置 + 加载机制 (20%)
- [ ] 模式转换审计链 (20%)
- [ ] 违规场景测试通过 (15%)
- [ ] 文档 (模式分离原理 + 白名单配置指南) (15%)
- **验收标准**: Planning/Execution 达到 70%

### Week 3-4 检查点
- [ ] RAG Git/ADR 索引实现 + 测试 (30%)
- [ ] Supervisor 角色定义 ADR (20%)
- [ ] 状态订阅 POC (30%)
- [ ] QA 流程伪代码 (20%)
- **验收标准**: RAG 85%, Supervisor 设计完成 (50%)

### Week 5-6 检查点
- [ ] EventBus 订阅机制生产就绪 (25%)
- [ ] QA 自动化流程实现 (30%)
- [ ] Guardian 介入决策逻辑 (25%)
- [ ] 端到端测试 + 文档 (20%)
- **验收标准**: Supervisor 达到 80%

### Week 7-8 检查点
- [ ] Cron 调度框架 (25%)
- [ ] 风险挖掘逻辑 v1 (30%)
- [ ] Follow-up 任务创建 (25%)
- [ ] 端到端 Demo (20%)
- **验收标准**: Lead Agent POC 完成 (40%)

---

## 🚨 风险与缓解

### Risk #1: Week 1-2 Retry/Timeout 实现复杂度被低估
**概率**: 中
**影响**: 高 (阻塞 Supervisor)
**缓解**:
- Week 1 前两天先做技术预研
- 如果发现复杂，立刻调整范围 (如先实现 Retry，Timeout 延后)
- 保留 1 天 buffer

### Risk #2: ModeGate 强制执行可能破坏现有流程
**概率**: 中
**影响**: 中
**缓解**:
- Week 2 先在 dry-run 模式实现 (记录违规但不阻断)
- Week 3 逐步切换到强制模式
- 有回滚开关

### Risk #3: Supervisor 设计与实现脱节
**概率**: 低
**影响**: 高
**缓解**:
- Week 4 设计时邀请实现者参与
- 设计完成后立刻做 POC 验证
- Week 5 开始实现前再次 review 设计

---

## 📊 进度追踪机制

### 每周例会 (建议)
- **时间**: 每周五下午
- **内容**:
  1. 本周交付物验收 (对照检查清单)
  2. 下周任务拆解
  3. 风险识别 + 缓解计划
  4. 阻塞点升级

### 进度报告格式
```markdown
## Week X 进度报告

### ✅ 已完成 (符合 DoD)
- [功能名] Progress: X% → Y%
  - 代码: ✅
  - 测试: ✅
  - 文档: ✅
  - 集成: ✅
  - 运维: ✅

### ⚠️ 进行中 (未达 DoD)
- [功能名] Progress: X%
  - 缺口: [具体缺什么]
  - 预计完成: [日期]

### 🚨 阻塞
- [阻塞描述]
  - 原因: [根因]
  - 缓解: [措施]
```

---

## 🎯 Phase 1 成功标准 (Week 4 验收)

### 必须达成 (P0)
1. ✅ Task Lifecycle 达到 90% (Retry/Timeout/Cancel 全部实现 + 测试 + 文档)
2. ✅ Planning/Execution 达到 70% (ModeGate 硬闸门强制执行)
3. ✅ RAG v1 达到 85% (Git/ADR 索引可用)
4. ✅ Supervisor 设计完成 (ADR + POC)

### 可选达成 (P1)
- ⏳ Dashboard 可视化 (可延后到 Phase 2)
- ⏳ External Views (可延后到 Phase 2)

### 验收方式
- 代码 Review
- 端到端集成测试通过
- 文档完整性检查
- 演示 Demo

---

## 📝 后续 Phase 概览 (不展开)

**Phase 2 (Week 5-8)**: Supervisor + Lead Agent 实现
**Phase 3 (Week 9-16)**: Multi-Agent + MCP 设计
**Phase 4 (Week 17+)**: MCP 实现 + NL-Delivery 启动

---

## 总结

这份优化后的执行计划基于以下原则：

1. **依赖优先**: Task Lifecycle 和 Planning/Execution 是地基，必须先做
2. **阻塞解除**: 每个 Phase 结束时必须解锁下游
3. **可验收**: 每周都有明确的交付物和检查清单
4. **可追溯**: Progress% 映射到 5 维缺口，不是主观数字
5. **风险可控**: 提前识别风险并准备缓解措施

**关键成功因素**:
- Week 1-4 的 Phase 1 必须严格执行，否则后续全部延期
- DoD 不能妥协，宁可延期也不能降低质量标准
- 重复规格必须先清理（见 Roadmap Hygiene epic）

---

**文档版本**: v2
**下次更新**: Week 4 Phase 1 验收后
**负责人**: [待填写]
