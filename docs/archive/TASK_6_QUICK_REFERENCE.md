# Task 6: 端到端验收测试 - 快速参考

## 🚀 快速开始

### 运行所有测试

```bash
# E2E 验收测试 (9 个场景)
python3 -m pytest tests/integration/test_budget_e2e.py::TestBudgetE2E -v

# 性能基准测试 (9 个基准)
python3 -m pytest tests/performance/test_budget_benchmark.py -v

# 所有预算相关测试
python3 -m pytest -k budget -v
```

### 运行特定场景

```bash
# 场景 1: 模型切换自动调整
python3 -m pytest tests/integration/test_budget_e2e.py::TestBudgetE2E::test_scenario_1_model_switch_auto_adjust -v

# 场景 2: 手动配置
python3 -m pytest tests/integration/test_budget_e2e.py::TestBudgetE2E::test_scenario_2_manual_configuration -v

# 场景 3: 无过早截断
python3 -m pytest tests/integration/test_budget_e2e.py::TestBudgetE2E::test_scenario_3_no_premature_truncation -v

# 场景 4: 截断提示清晰
python3 -m pytest tests/integration/test_budget_e2e.py::TestBudgetE2E::test_scenario_4_clear_truncation_hints -v

# 场景 5: 性能测试
python3 -m pytest tests/integration/test_budget_e2e.py::TestBudgetE2E::test_scenario_5_large_budget_performance -v
```

---

## 📊 测试结果摘要

### 自动化测试

| 场景 | 状态 | 关键指标 |
|------|------|----------|
| 场景 1: 模型切换自动调整 | ✅ PASSED | 16k→11.9k, 128k→106.8k, 200k→168k |
| 场景 2: 手动配置 | ✅ PASSED | 配置保存、加载、应用正常 |
| 场景 3: 无过早截断 | ✅ PASSED | 10/50 消息保留，无异常截断 |
| 场景 4: 截断提示清晰 | ✅ PASSED | 10/100 消息保留，日志清晰 |
| 场景 5: 性能测试 | ✅ PASSED | Context 构建 <500ms |
| 向后兼容: 无预算 | ✅ PASSED | 默认 5100 tokens |
| 向后兼容: 旧 API | ✅ PASSED | ContextBudget 直接创建可用 |
| 验证: 预算规则 | ✅ PASSED | 所有验证规则正确 |
| 验证: Fallback 窗口 | ✅ PASSED | 所有已知模型正确 |

**总计**: 9/9 通过 (100%)

---

## 📁 关键文件位置

### 测试文件

```
tests/
├── integration/
│   └── test_budget_e2e.py           # E2E 验收测试
└── performance/
    └── test_budget_benchmark.py      # 性能基准测试
```

### 文档

```
TASK_6_MANUAL_TEST_CHECKLIST.md      # 手动测试清单
TASK_6_ACCEPTANCE_REPORT.md          # 完整验收报告
TASK_6_QUICK_REFERENCE.md            # 本文档
```

### 实现代码

```
agentos/
├── config/
│   └── budget_config.py             # 配置管理
├── core/
│   └── chat/
│       ├── budget_resolver.py       # 自动推导逻辑
│       └── context_builder.py       # Context 构建器
└── webui/
    └── api/
        └── budget.py                # API 端点
```

---

## 🎯 验收标准

### ✅ 已达成

- [x] 场景 1-5 自动化测试全部通过
- [x] 手动测试清单完整
- [x] 性能测试达标 (Context 构建 <500ms)
- [x] 无向后兼容性破坏
- [x] 验收报告完整

---

## 🔧 故障排查

### 问题: 测试失败 "No item with that key"

**原因**: 数据库 schema 缺少必需列

**解决方案**:
```sql
-- 确保 chat_sessions 表包含所有必需列
CREATE TABLE chat_sessions (
    session_id TEXT PRIMARY KEY,
    title TEXT,
    task_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
);
```

### 问题: 性能测试超时

**原因**: 数据库操作慢或测试数据过多

**解决方案**:
```bash
# 使用更短的超时和更少迭代
python3 -m pytest tests/performance/test_budget_benchmark.py -v --tb=short
```

---

## 📖 相关文档

| 文档 | 描述 |
|------|------|
| [设计方案](docs/architecture/) | 任务 1 设计文档 |
| [配置层](agentos/config/budget_config.py) | 任务 2 实现 |
| [自动推导](agentos/core/chat/budget_resolver.py) | 任务 3 实现 |
| [WebUI 设置](agentos/webui/api/budget.py) | 任务 4 实现 |
| [运行时可视化](agentos/webui/static/js/views/) | 任务 5 实现 |
| [手动测试清单](TASK_6_MANUAL_TEST_CHECKLIST.md) | 手动测试步骤 |
| [完整验收报告](TASK_6_ACCEPTANCE_REPORT.md) | 详细测试结果 |

---

## 🔗 API 快速测试

### GET /api/budget/global

```bash
curl http://localhost:8080/api/budget/global
```

**预期响应**:
```json
{
  "max_tokens": 8000,
  "auto_derive": false,
  "allocation": {
    "window_tokens": 4000,
    "rag_tokens": 2000,
    "memory_tokens": 1000,
    "summary_tokens": 1000,
    "system_tokens": 1000
  }
}
```

### PUT /api/budget/global

```bash
curl -X PUT http://localhost:8080/api/budget/global \
  -H "Content-Type: application/json" \
  -d '{"max_tokens": 32000}'
```

### POST /api/budget/derive

```bash
curl -X POST http://localhost:8080/api/budget/derive \
  -H "Content-Type: application/json" \
  -d '{"model_id": "gpt-4o", "context_window": 128000}'
```

---

## 🎉 结论

✅ **验收通过**

所有核心功能按预期工作，测试覆盖充分，性能达标，向后兼容。

**可以发布** 🚀

---

**最后更新**: 2026-01-30
**版本**: v1.0
