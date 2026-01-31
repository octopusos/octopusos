# AgentOS 项目状态

**当前版本**: v0.3.0  
**最后更新**: 2026-01-25  
**状态**: 🟢 生产就绪

---

## 快速导航

### 文档

- **[V03_FINAL_REPORT.md](V03_FINAL_REPORT.md)** - v0.3 完整实施总结
- **[V03_IMPLEMENTATION_REPORT.md](V03_IMPLEMENTATION_REPORT.md)** - v0.3 详细实施报告
- **[V03_ALERT_POINTS.md](V03_ALERT_POINTS.md)** - v0.4 架构警戒点
- **[V02_IMPLEMENTATION_COMPLETE.md](V02_IMPLEMENTATION_COMPLETE.md)** - v0.2 实施报告
- **[docs/V02_INVARIANTS.md](docs/V02_INVARIANTS.md)** - 18 条不变量（已冻结）

### 架构决策

- **[ADR-004](docs/adr/ADR-004-memoryos-split.md)** - MemoryOS 独立化
- **[ADR-005](docs/adr/ADR-005-self-heal-learning.md)** - 自愈与学习机制
- **[ADR-006](docs/adr/ADR-006-policy-evolution-safety.md)** - 策略演化安全

### 代码

- **agentos/** - AgentOS 核心（v0.3.0）
- **memoryos/** - MemoryOS 独立包（v0.3.0）
- **tests/** - 43 个测试（全部通过）

---

## 版本历史

### v0.3.0（当前）- 2026-01-25

**主题**: 控制面升级 + MemoryOS 独立化

**核心功能**:
- ✅ MemoryOS 独立化（API 边界清晰）
- ✅ 自愈框架（8 种失败 + 7 种动作）
- ✅ Learning 管线（从历史中学习）
- ✅ Policy Evolution（策略演化引擎）
- ✅ RunTape & Replay（完整可重放）
- ✅ Resource Budget（资源感知调度）

**新增**:
- 35+ 新文件
- ~3000 行代码
- 17 个新测试
- 9 个新 schemas
- 8 条新约束

**测试**: 43 passed（0 failed）

### v0.2.0 - 2026-01-25

**主题**: 控制面基础设施

**核心功能**:
- ✅ 外置记忆服务（MemoryService + FTS）
- ✅ 执行模式治理（3 种模式 + 风险策略）
- ✅ 全链路审计（ReviewPack + Patches + Commits）
- ✅ 智能锁机制（TaskLock + FileLock + Rebase）
- ✅ 高级调度器（4 种模式 + 依赖图）

**护城河**: 10 条不变量

**测试**: 26 passed

### v0.1.0

**主题**: 基础 Agent 编排

**核心功能**:
- 项目扫描（FactPack）
- AI 生成（AgentSpec）
- 规则系统
- 基础编排

---

## 当前能力

### 核心系统

| 系统 | 版本 | 状态 | 说明 |
|------|------|------|------|
| AgentOS | v0.3.0 | 🟢 | 完整控制面 |
| MemoryOS | v0.3.0 | 🟢 | 独立记忆系统 |

### 功能模块

| 模块 | 状态 | 测试 | 说明 |
|------|------|------|------|
| FactPack 扫描 | 🟢 | ✅ | v0.1 |
| AgentSpec 生成 | 🟢 | ✅ | v0.1 |
| Memory Service | 🟢 | ✅ | v0.2 |
| Execution Policy | 🟢 | ✅ | v0.2 |
| Locks & Rebase | 🟢 | ✅ | v0.2 |
| Scheduler | 🟢 | ✅ | v0.2 |
| **Self-Healing** | **🟢** | **✅** | **v0.3 新增** |
| **Learning** | **🟢** | **✅** | **v0.3 新增** |
| **Policy Evolution** | **🟢** | **✅** | **v0.3 新增** |
| **RunTape & Replay** | **🟢** | **✅** | **v0.3 新增** |
| **Resource Budget** | **🟢** | **✅** | **v0.3 新增** |

---

## 护城河状态

### v0.2 护城河（10 条）- 全部有效 ✅

1. ✅ 无 MemoryPack 不允许执行
2. ✅ full_auto question_budget = 0
3. ✅ 命令/路径禁止编造
4. ✅ 每次执行写 run_steps
5. ✅ 每次执行有 review_pack.md
6. ✅ patch 记录 intent + files + diff_hash
7. ✅ 发布绑定 commit hash
8. ✅ 文件锁冲突 WAIT + rebase
9. ✅ 并发受 locks 限制
10. ✅ scheduler 触发可审计

### v0.3 新增约束（8 条）- 全部实现 ✅

11. ✅ Memory 必须有 retention_policy
12. ✅ 高风险 ReviewPack 必须人工批准
13. ✅ Rebase 验证 intent 一致性
14. ✅ Policy 组合必须预设
15. ✅ 自愈动作白名单
16. ✅ Learning 先提案后应用
17. ✅ Policy 演化必须 canary
18. ✅ RunTape 必须可重放

**总计**: 18 条不变量（已冻结）

---

## 测试状态

### 测试覆盖

```bash
# 运行所有测试
uv run python -m pytest tests/ -v

# 结果
43 passed in 0.64s
```

### 测试分类

| 类别 | 数量 | 状态 |
|------|------|------|
| v0.1 基础 | 4 | ✅ |
| v0.2 核心 | 22 | ✅ |
| v0.3 新增 | 17 | ✅ |
| **总计** | **43** | **✅** |

### 关键测试

- ✅ test_invariants.py - 18 条不变量验证
- ✅ test_healing.py - 自愈框架
- ✅ test_policy_evolution.py - 策略演化
- ✅ test_scenarios.py - 端到端场景

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repo>
cd AgentOS

# 安装依赖
uv sync

# 验证版本
uv run agentos --version
# 输出: agentos, version 0.3.0
```

### 基本使用

```bash
# 初始化
uv run agentos init

# 扫描项目
uv run agentos scan <project>

# Memory 管理
uv run agentos memory list
uv run agentos memory add --type convention --summary "..."

# 执行任务（带自愈）
uv run agentos orchestrate --mode semi_auto
```

### 运行测试

```bash
# 所有测试
uv run pytest tests/ -v

# 特定模块
uv run pytest tests/test_invariants.py -v
```

---

## 下一步（v0.4 规划）

根据 V03_ALERT_POINTS.md，v0.4 将聚焦：

### P0 优先级

1. **Memory 增长与衰减**
   - retention_policy 执行
   - confidence decay
   - promotion 路径

2. **ReviewPack 人类介入**
   - ReviewLevel 分类
   - approval_queue
   - 通知机制

### P1 优先级

3. **Policy 预设简化**
   - POLICY_PRESETS 实施
   - 组合验证

4. **Rebase 语义一致性**
   - Intent 验证
   - Memory 回滚

---

## 贡献者

- AgentOS 架构团队
- 实施时间: 2026-01-25

---

## License

MIT License - 详见 [LICENSE](LICENSE)

---

**最后更新**: 2026-01-25  
**维护**: AgentOS 架构团队  
**状态**: 🟢 生产就绪
