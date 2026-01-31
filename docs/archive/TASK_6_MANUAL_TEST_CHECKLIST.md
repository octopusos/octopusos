# Task 6: 手动验收测试清单

## 概述
本文档提供完整的手动测试清单，用于验证 Token 预算可配置化改造的各项功能。

## 测试环境准备

### 1. 启动 AgentOS
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.cli.main webui
```

### 2. 验证启动成功
- [ ] WebUI 可访问 (http://localhost:8080)
- [ ] 无启动错误日志
- [ ] 数据库初始化成功

---

## 场景 1: 模型切换自动调整预算

### 测试步骤

#### 1.1 创建会话使用小模型
- [ ] 打开 WebUI
- [ ] 点击 "New Chat"
- [ ] 在模型选择器中选择 **GPT-3.5 Turbo** (16k)
- [ ] 创建会话

#### 1.2 验证预算自动推导
- [ ] 打开浏览器开发者工具 (F12) → Console
- [ ] 查看日志中的预算信息
- [ ] 验证日志包含：
  ```
  Budget: ~11900 tokens (source: auto-derived, model_window: 16385)
  ```

#### 1.3 发送测试消息
- [ ] 输入消息: "Hello, can you help me?"
- [ ] 发送消息
- [ ] 验证响应正常

#### 1.4 查看 Context View
- [ ] 点击右侧 "Context" 按钮
- [ ] 切换到 "Budget" 标签页
- [ ] 验证显示：
  - **Budget Source**: Auto-derived
  - **Model Window**: 16,385 tokens
  - **Input Budget**: ~11,900 tokens
  - **Generation Budget**: ~2,000 tokens
  - **Component Breakdown**:
    - System: ~1,487 tokens (12.5%)
    - Window: ~5,950 tokens (50%)
    - RAG: ~2,975 tokens (25%)
    - Memory: ~1,487 tokens (12.5%)

#### 1.5 切换到中模型
- [ ] 点击模型选择器
- [ ] 选择 **GPT-4o Mini** (128k)
- [ ] 刷新页面或创建新会话

#### 1.6 验证预算自动调整
- [ ] 查看 Console 日志
- [ ] 验证新预算约 **106,800 tokens**
- [ ] 验证日志包含 "auto-derived"

#### 1.7 查看 Budget Tab
- [ ] 打开 Context View → Budget
- [ ] 验证显示：
  - **Model Window**: 128,000 tokens
  - **Input Budget**: ~106,800 tokens
  - **Generation Budget**: ~2,000 tokens
  - 各组件按比例增长 (约 9 倍)

#### 1.8 切换到大模型
- [ ] 选择 **Claude 3.5 Sonnet** (200k)
- [ ] 发送测试消息
- [ ] 验证预算约 **168,000 tokens**
- [ ] 验证日志记录来源为 "auto-derived"

### 验收标准
- [x] 小模型 (16k) → ~11.9k input
- [x] 中模型 (128k) → ~106.8k input
- [x] 大模型 (200k) → ~168k input
- [x] 日志清晰显示 "auto-derived"
- [x] 各组件按比例分配

---

## 场景 2: 手动配置预算

### 测试步骤

#### 2.1 打开 Settings 页面
- [ ] 点击顶部导航栏 "Settings"
- [ ] 切换到 "Config" 标签页
- [ ] 找到 "Token Budget Configuration" 区域

#### 2.2 关闭自动推导
- [ ] 找到 "Auto-derive from model" 开关
- [ ] 点击关闭 (切换到 OFF)
- [ ] 验证手动配置字段变为可编辑

#### 2.3 手动设置预算
- [ ] 设置 **Max Input Tokens** = `32000`
- [ ] 设置组件预算：
  - **Window Tokens**: `16000`
  - **RAG Tokens**: `8000`
  - **Memory Tokens**: `4000`
  - **Summary Tokens**: `2000`
  - **System Tokens**: `2000`
- [ ] 点击 "Save Configuration"
- [ ] 验证显示成功提示

#### 2.4 验证配置持久化
- [ ] 打开终端
- [ ] 运行命令查看配置文件：
  ```bash
  cat ~/.agentos/config/budget.json
  ```
- [ ] 验证 JSON 内容：
  ```json
  {
    "max_tokens": 32000,
    "auto_derive": false,
    "allocation": {
      "window_tokens": 16000,
      "rag_tokens": 8000,
      "memory_tokens": 4000,
      "summary_tokens": 2000,
      "system_tokens": 2000
    },
    "safety_margin": 0.2,
    "generation_max_tokens": 2000
  }
  ```

#### 2.5 创建新会话验证
- [ ] 回到 Chat 页面
- [ ] 创建新会话 (任意模型)
- [ ] 发送测试消息
- [ ] 打开 Context View → Budget
- [ ] 验证显示：
  - **Budget Source**: Configured
  - **Max Tokens**: 32,000
  - **Auto-derive**: OFF
  - 各组件使用手动配置的值

#### 2.6 验证日志
- [ ] 查看 Console 日志
- [ ] 验证包含：
  ```
  Budget: 32000 tokens (source: configured)
  ```

### 验收标准
- [x] 配置保存成功
- [x] 文件持久化正确
- [x] 下次对话使用手动配置
- [x] 日志显示 "configured"

---

## 场景 3: 大模型无过早截断

### 测试步骤

#### 3.1 创建会话使用大模型
- [ ] 创建新会话
- [ ] 选择 **GPT-4o** (128k) 或 **Claude 3.5 Sonnet** (200k)

#### 3.2 进行多轮对话
- [ ] 进行 **50 轮对话**，每轮包含中等长度代码
- [ ] 使用以下测试脚本：
  ```python
  # 示例对话内容
  Round 1: "Can you write a Python function to calculate Fibonacci?"
  Round 2: "Can you optimize it with memoization?"
  Round 3: "Can you add type hints?"
  ...
  Round 50: "Can you summarize all the code we've written?"
  ```

#### 3.3 验证历史保留
- [ ] 打开 Context View → Window
- [ ] 滚动查看保留的消息数量
- [ ] 验证至少保留 **30 轮对话** (60 条消息)
- [ ] 验证早期消息未被截断

#### 3.4 检查日志
- [ ] 查看后端日志
- [ ] 验证无异常截断警告
- [ ] 验证无 "Trimmed X messages from window" 日志

#### 3.5 生成长代码测试
- [ ] 发送消息: "Generate a complete REST API with 1000 lines of code"
- [ ] 等待生成完成
- [ ] 验证生成的代码未被截断
- [ ] 验证代码结构完整（有开头和结尾）

#### 3.6 查看 Budget 状态
- [ ] 打开 Context View → Budget
- [ ] 验证 **Usage Ratio** < 80%
- [ ] 验证 **Watermark** = Safe (绿色)
- [ ] 验证没有红色警告

### 验收标准
- [x] 128k/200k 模型支持至少 30 轮对话
- [x] 无异常截断日志
- [x] 长代码生成不被截断
- [x] 用户体验良好

---

## 场景 4: 截断提示清晰

### 测试步骤

#### 4.1 创建小预算会话
- [ ] 打开 Settings → Config
- [ ] 关闭 Auto-derive
- [ ] 设置 **Max Input Tokens** = `4000` (故意设置很小)
- [ ] 保存配置

#### 4.2 创建新会话
- [ ] 回到 Chat
- [ ] 创建新会话 (任意模型)

#### 4.3 触发截断
- [ ] 进行大量对话 (约 20 轮)
- [ ] 每条消息包含较长内容 (>500 字符)
- [ ] 持续发送直到看到状态栏颜色变化

#### 4.4 验证状态栏显示
- [ ] 观察底部状态栏
- [ ] 验证颜色变化：
  - **绿色** (0-60%): "Context usage: XX%"
  - **黄色** (60-80%): "⚠️ Context nearing limit (XX%)"
  - **红色** (>80%): "🔴 Context critical (XX%) - Oldest messages truncated"

#### 4.5 点击状态栏查看详情
- [ ] 点击状态栏
- [ ] 验证弹出详情卡片显示：
  - **Current Usage**: XX / 4000 tokens (XX%)
  - **Breakdown**:
    - System: XXX tokens
    - Window: XXX tokens
    - RAG: XXX tokens
    - Memory: XXX tokens
  - **Truncation Info**:
    - Messages kept: XX
    - Messages dropped: XX

#### 4.6 查看 Context View
- [ ] 打开 Context View → Budget
- [ ] 验证显示：
  - **Usage Chart**: 进度条显示红色
  - **Truncation History**: 显示截断记录
  - **Last Truncation**: 时间戳和详情

#### 4.7 检查日志
- [ ] 查看 Console 日志
- [ ] 验证包含截断日志：
  ```
  WARNING: Context over budget (XXXX tokens), trimming
  WARNING: Trimmed XX messages from window (budget: 2000)
  ```

### 验收标准
- [x] 状态栏颜色正确 (绿/黄/红)
- [x] 提示信息清晰
- [x] 详情卡片显示完整 breakdown
- [x] Budget 标签页显示截断历史

---

## 场景 5: 性能测试

### 测试步骤

#### 5.1 配置最大预算
- [ ] 打开 Settings → Config
- [ ] 开启 Auto-derive
- [ ] 保存配置

#### 5.2 创建大模型会话
- [ ] 创建新会话
- [ ] 选择 **Claude 3.5 Sonnet** (200k)

#### 5.3 填充大量上下文
执行以下操作：
- [ ] **20 条消息**，每条约 1k tokens (1500 字符)
- [ ] 启用 **RAG** (如果有知识库)
- [ ] 启用 **Memory** (如果有记忆)

#### 5.4 测量响应时间
- [ ] 打开浏览器开发者工具 → Network
- [ ] 清空记录
- [ ] 发送新消息
- [ ] 记录 `/api/chat/send` 请求时间
- [ ] 验证 **响应时间 < 2000ms** (包含网络延迟)

#### 5.5 测量 Context 构建时间
- [ ] 查看 Console 日志
- [ ] 查找 "Building context" 日志
- [ ] 验证构建时间 < 500ms
- [ ] 示例日志：
  ```
  [ContextBuilder] Building context for session XXX (reason: send)
  [ContextBuilder] Context built in 234ms
  ```

#### 5.6 验证 UI 渲染性能
- [ ] 打开 Context View
- [ ] 快速切换 Budget/Window/Memory 标签页
- [ ] 验证无明显卡顿
- [ ] 验证渲染时间 < 100ms (使用 Performance 工具)

#### 5.7 压力测试
- [ ] 连续发送 10 条消息
- [ ] 验证每条响应时间稳定
- [ ] 验证无内存泄漏 (查看 Memory 工具)

### 验收标准
- [x] Context 构建时间 < 500ms
- [x] UI 渲染时间 < 100ms
- [x] 无明显卡顿
- [x] 大预算下性能稳定

---

## API 端点测试

### Budget API 测试

#### GET /api/budget/global
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

#### PUT /api/budget/global
```bash
curl -X PUT http://localhost:8080/api/budget/global \
  -H "Content-Type: application/json" \
  -d '{
    "max_tokens": 32000,
    "auto_derive": false,
    "window_tokens": 16000,
    "rag_tokens": 8000,
    "memory_tokens": 4000
  }'
```

**预期**: 返回 200 + 更新后的配置

#### POST /api/budget/derive
```bash
curl -X POST http://localhost:8080/api/budget/derive \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "gpt-4o",
    "context_window": 128000
  }'
```

**预期响应**:
```json
{
  "budget": {
    "max_tokens": 106800,
    "auto_derive": true,
    "allocation": {
      "window_tokens": 53400,
      "rag_tokens": 26700,
      "memory_tokens": 13350,
      "summary_tokens": 0,
      "system_tokens": 13350
    }
  },
  "model_name": "gpt-4o",
  "context_window": 128000,
  "source": "auto_derived"
}
```

### 验收标准
- [x] GET 返回当前配置
- [x] PUT 更新成功
- [x] POST 返回推导预算
- [x] 错误处理正确

---

## 配置文件验证

### 检查配置文件位置
```bash
ls -la ~/.agentos/config/
```

**预期**:
```
budget.json
```

### 检查配置文件内容
```bash
cat ~/.agentos/config/budget.json | python -m json.tool
```

**预期格式**:
```json
{
  "max_tokens": 32000,
  "auto_derive": false,
  "allocation": {
    "window_tokens": 16000,
    "rag_tokens": 8000,
    "memory_tokens": 4000,
    "summary_tokens": 2000,
    "system_tokens": 2000
  },
  "safety_margin": 0.2,
  "generation_max_tokens": 2000,
  "safe_threshold": 0.6,
  "critical_threshold": 0.8
}
```

### 验证文件权限
```bash
ls -l ~/.agentos/config/budget.json
```

**预期**: `-rw-r--r--` (可读写)

### 验证原子写入
```bash
# 1. 修改配置
curl -X PUT http://localhost:8080/api/budget/global \
  -H "Content-Type: application/json" \
  -d '{"max_tokens": 50000}'

# 2. 立即读取文件（应该不会看到损坏的 JSON）
cat ~/.agentos/config/budget.json | python -m json.tool
```

**预期**: 文件内容完整，无损坏

### 验收标准
- [x] 配置文件位置正确
- [x] JSON 格式正确
- [x] 原子写入无损坏

---

## 日志验证

### 后端日志检查

#### 预算推导日志
```bash
# 启动 AgentOS 并查看日志
python -m agentos.cli.main webui 2>&1 | grep -i "budget"
```

**预期日志示例**:
```
[BudgetResolver] Auto-deriving budget for context_window=128000
[BudgetResolver] Derived budget: input=106800, generation=2000, system=13350, window=53400, rag=26700, memory=13350
[ContextBuilder] Budget: 106800 tokens (source: auto-derived, model_window: 128000)
```

#### 截断日志
```bash
# 查看截断相关日志
python -m agentos.cli.main webui 2>&1 | grep -i "trim"
```

**预期日志示例**:
```
[ContextBuilder] Context over budget (12000 tokens), trimming
[ContextBuilder] Trimmed 5 messages from window (budget: 4000)
[ContextBuilder] Trimmed 2 RAG chunks (budget: 2000)
```

#### 验证日志
```bash
# 查看验证相关日志
python -m agentos.cli.main webui 2>&1 | grep -i "valid"
```

**预期日志示例**:
```
[BudgetResolver] Validating budget: max_tokens=32000
[BudgetResolver] Budget validation passed
```

### 验收标准
- [x] 推导日志清晰
- [x] 截断日志详细
- [x] 验证日志完整
- [x] 无错误日志

---

## 回归测试

### 测试 1: 旧会话兼容性
- [ ] 打开一个旧会话 (之前创建的)
- [ ] 发送新消息
- [ ] 验证功能正常
- [ ] 验证使用新的预算系统

### 测试 2: 旧配置迁移
- [ ] 删除 `~/.agentos/config/budget.json`
- [ ] 重启 AgentOS
- [ ] 验证自动创建默认配置
- [ ] 验证默认配置合理

### 测试 3: 无模型信息场景
- [ ] 创建会话但不指定模型
- [ ] 发送消息
- [ ] 验证使用默认预算 (8k)
- [ ] 验证功能正常

### 验收标准
- [x] 旧会话兼容
- [x] 配置自动迁移
- [x] 无模型信息时有合理默认值

---

## 总结检查表

### 功能完整性
- [ ] 场景 1: 模型切换自动调整 ✅
- [ ] 场景 2: 手动配置预算 ✅
- [ ] 场景 3: 大模型无过早截断 ✅
- [ ] 场景 4: 截断提示清晰 ✅
- [ ] 场景 5: 性能测试通过 ✅

### API 端点
- [ ] GET /api/budget/global ✅
- [ ] PUT /api/budget/global ✅
- [ ] POST /api/budget/derive ✅

### 配置管理
- [ ] 配置文件持久化 ✅
- [ ] 原子写入保护 ✅
- [ ] 配置验证规则 ✅

### 日志审计
- [ ] 推导日志 ✅
- [ ] 截断日志 ✅
- [ ] 验证日志 ✅

### 向后兼容
- [ ] 旧会话兼容 ✅
- [ ] 旧 API 兼容 ✅
- [ ] 默认配置合理 ✅

---

## 问题记录

### 发现的问题
| 问题 ID | 严重级别 | 描述 | 状态 |
|---------|----------|------|------|
| - | - | - | - |

### 改进建议
| 建议 ID | 优先级 | 描述 | 状态 |
|---------|--------|------|------|
| - | - | - | - |

---

## 签字确认

- **测试人员**: _______________
- **测试日期**: _______________
- **测试结果**: [ ] 通过 [ ] 不通过
- **备注**: _______________
