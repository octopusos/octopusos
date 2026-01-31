# Task 4: WebUI Settings Interface - Quick Start Guide

## 快速测试

### 1. 启动 WebUI
```bash
cd /Users/pangge/PycharmProjects/AgentOS
agentos webui --host 0.0.0.0 --port 8080
```

### 2. 访问 Settings 页面
浏览器打开: `http://localhost:8080`
点击左侧导航 → **Config**

### 3. 查看 Token Budget 配置
在页面顶部应该看到 "Token Budget Configuration" 段，包含：
- Auto-derive 开关
- 当前模型信息预览框
- 高级设置字段
- Save / Reset 按钮

---

## API 测试

### 获取当前配置
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
  },
  "safety_margin": 0.2,
  "generation_max_tokens": 2000,
  "safe_threshold": 0.6,
  "critical_threshold": 0.8
}
```

### 更新配置（开启 auto-derive）
```bash
curl -X PUT http://localhost:8080/api/budget/global \
  -H "Content-Type: application/json" \
  -d '{"auto_derive": true}'
```

### 预览自动推导结果
```bash
curl -X POST http://localhost:8080/api/budget/derive \
  -H "Content-Type: application/json" \
  -d '{"model_id": "gpt-4o", "context_window": 128000}'
```

**预期响应**:
```json
{
  "budget": {
    "max_tokens": 91800,
    "auto_derive": true,
    "allocation": {
      "window_tokens": 45900,
      "rag_tokens": 22950,
      "memory_tokens": 11475,
      "summary_tokens": 0,
      "system_tokens": 11475
    },
    "safety_margin": 0.15,
    "generation_max_tokens": 17000,
    "safe_threshold": 0.6,
    "critical_threshold": 0.8
  },
  "model_name": "gpt-4o",
  "context_window": 128000,
  "source": "auto_derived"
}
```

---

## 单元测试

### 运行所有 Budget API 测试
```bash
python3 -m pytest tests/unit/webui/test_budget_api.py -v
```

**预期结果**: ✅ 15 passed

### 运行特定测试类
```bash
# 测试 GET endpoint
python3 -m pytest tests/unit/webui/test_budget_api.py::TestGetGlobalBudget -v

# 测试 PUT endpoint
python3 -m pytest tests/unit/webui/test_budget_api.py::TestUpdateGlobalBudget -v

# 测试 POST /derive endpoint
python3 -m pytest tests/unit/webui/test_budget_api.py::TestPreviewDerive -v
```

---

## 配置文件位置

Budget 配置存储在:
```
~/.agentos/config/budget.json
```

### 查看当前配置
```bash
cat ~/.agentos/config/budget.json | jq
```

### 手动编辑（不推荐，应通过 WebUI）
```bash
nano ~/.agentos/config/budget.json
```

---

## 常见使用场景

### 场景 1: 使用默认配置
适用于小模型（8k-16k context window）

1. 保持 `auto_derive = false`
2. 使用默认值（max_tokens=8000）
3. 直接开始使用

### 场景 2: 使用大模型（GPT-4o, Claude-3.5）
适用于 128k+ context window

1. 访问 Config 页面
2. 勾选 "Auto-derive from model"
3. 点击 Save
4. 系统自动计算最优预算（~91k input + 17k generation）

### 场景 3: 精细控制
适用于特殊需求（例如限制 RAG tokens）

1. 关闭 auto-derive
2. 手动设置各组件 tokens
3. 确保总和不超过 max_tokens
4. 保存配置

---

## 故障排查

### 问题: Budget 段不显示
**检查**:
1. CSS 是否正确加载: `http://localhost:8080/static/css/budget-config.css`
2. 浏览器控制台是否有 JS 错误
3. API 是否可访问: `curl http://localhost:8080/api/budget/global`

### 问题: 保存失败
**可能原因**:
1. 组件总和超过 max_tokens
2. 负数或无效输入
3. 文件权限问题（检查 `~/.agentos/config/` 目录权限）

**解决方案**:
```bash
# 检查配置目录权限
ls -la ~/.agentos/config/

# 如果目录不存在，创建它
mkdir -p ~/.agentos/config/

# 删除损坏的配置文件，重新创建
rm ~/.agentos/config/budget.json
```

### 问题: 预览推导失败
**可能原因**:
1. 模型信息未加载（`/api/runtime/config` 失败）
2. 网络问题

**解决方案**:
```bash
# 手动指定 context_window
curl -X POST http://localhost:8080/api/budget/derive \
  -H "Content-Type: application/json" \
  -d '{"model_id": "custom-model", "context_window": 32000}'
```

---

## 技术细节

### API 路由
- `GET /api/budget/global` - 加载全局配置
- `PUT /api/budget/global` - 更新全局配置
- `POST /api/budget/derive` - 预览推导结果

### 前端组件
- `ConfigView.renderBudgetConfig()` - 渲染 Budget 段
- `ConfigView.loadBudgetConfig()` - 加载配置
- `ConfigView.saveBudgetConfig()` - 保存配置
- `ConfigView.previewDerivedBudget()` - 预览推导

### 依赖
- `agentos.config.BudgetConfigManager` - 配置管理
- `agentos.core.chat.budget_resolver.BudgetResolver` - 自动推导
- `agentos.providers.base.ModelInfo` - 模型信息

---

## 下一步

完成 Task 4 后，继续实施：
- **Task 5**: 运行时可视化（Budget Indicator）
- **Task 6**: 端到端验收测试

---

**文档版本**: 1.0
**更新日期**: 2026-01-30
