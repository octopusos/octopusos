# 任务 3 快速参考

## 核心 API

### BudgetResolver

```python
from agentos.core.chat.budget_resolver import BudgetResolver
from agentos.providers.base import ModelInfo

resolver = BudgetResolver()
```

#### 方法签名

```python
# 1. 自动推导预算
def auto_derive_budget(
    model_info: Optional[ModelInfo],
    generation_max: Optional[int] = None,
    allocation: Optional[Dict[str, float]] = None
) -> ContextBudget

# 2. 获取上下文窗口
def get_context_window(
    model_name: Optional[str],
    model_info: Optional[ModelInfo]
) -> int

# 3. 验证预算
def validate_budget(
    budget: ContextBudget,
    model_info: Optional[ModelInfo] = None
) -> tuple[bool, Optional[str]]

# 4. 解析预算（带优先级）
def resolve_budget(
    session_id: Optional[str] = None,
    project_id: Optional[str] = None,
    model_info: Optional[ModelInfo] = None,
    generation_max: Optional[int] = None
) -> BudgetDerivationResult

# 5. 获取默认预算
def get_default_budget() -> ContextBudget
```

## 使用示例

### 场景 1: 自动推导（推荐）

```python
from agentos.core.chat.budget_resolver import BudgetResolver
from agentos.providers.base import ModelInfo

resolver = BudgetResolver()

# 为 GPT-4o (128k) 推导预算
model_info = ModelInfo(
    id="gpt-4o",
    label="GPT-4o",
    context_window=128000
)

budget = resolver.auto_derive_budget(model_info)

print(f"Input budget: {budget.max_tokens}")  # 106800
print(f"Window tokens: {budget.window_tokens}")  # 53400
print(f"RAG tokens: {budget.rag_tokens}")  # 26700
```

### 场景 2: ContextBuilder 集成

```python
from agentos.core.chat.context_builder import ContextBuilder

# 自动推导（推荐）
builder = ContextBuilder(budget=None)
# builder.budget 已自动设置为基于 8k 的默认预算

# 显式预算
from agentos.core.chat.context_builder import ContextBudget
custom_budget = ContextBudget(max_tokens=10000, ...)
builder = ContextBuilder(budget=custom_budget)
```

### 场景 3: 验证用户输入

```python
from agentos.core.chat.budget_resolver import BudgetResolver
from agentos.core.chat.context_builder import ContextBudget

resolver = BudgetResolver()

# 用户输入的预算
user_budget = ContextBudget(
    max_tokens=5000,
    system_tokens=500,
    window_tokens=2500,
    rag_tokens=1500,
    memory_tokens=500
)

# 验证
is_valid, error = resolver.validate_budget(user_budget)
if not is_valid:
    print(f"Invalid: {error}")
```

### 场景 4: 自适应 max_tokens

```python
from agentos.core.chat.adapters import OllamaChatAdapter

adapter = OllamaChatAdapter()

messages = [
    {"role": "system", "content": "You are helpful"},
    {"role": "user", "content": "Hello"}
]

max_tokens = adapter.get_adaptive_max_tokens(
    messages,
    budget_max_tokens=2000,
    model_context_window=8192
)

# 使用 max_tokens 生成
response = adapter.generate(messages, max_tokens=max_tokens)
```

## 推导公式

```
输入: context_window

步骤 1: 安全裕度 (15%)
  usable_tokens = context_window * 0.85

步骤 2: 生成预留 (25% 或 2000，取小者)
  generation_budget = min(2000, context_window * 0.25)

步骤 3: 输入预算
  input_budget = usable_tokens - generation_budget

步骤 4: 组件分配
  system_tokens  = input_budget * 0.125  (12.5%)
  window_tokens  = input_budget * 0.50   (50%)
  rag_tokens     = input_budget * 0.25   (25%)
  memory_tokens  = input_budget * 0.125  (12.5%)
```

## 回退策略

```
优先级 1: model_info.context_window (显式值)
    ↓
优先级 2: FALLBACK_WINDOWS[model_name] (已知模型)
    ↓
优先级 3: FALLBACK_WINDOWS[prefix] (前缀匹配)
    ↓
优先级 4: FALLBACK_WINDOWS["default"] = 8000
```

### 已知模型回退表

| 模型 | 窗口大小 |
|------|---------|
| gpt-4o | 128000 |
| gpt-4o-mini | 128000 |
| claude-3-5-sonnet | 200000 |
| llama3.2:1b | 131072 |
| qwen2.5:7b | 131072 |
| default | 8000 |

## 验证规则

1. **正值校验**: max_tokens > 0, 所有组件 >= 0
2. **总和校验**: system + window + rag + memory + summary <= max_tokens
3. **窗口校验**: max_tokens <= model_window * 0.9
4. **最小值校验**: max_tokens >= 1000
5. **最大组件校验**: 任何单个组件 <= max_tokens * 0.8

## 测试命令

```bash
# 单元测试
pytest tests/unit/core/chat/test_budget_resolver.py -v

# 集成测试
pytest tests/integration/chat/test_budget_resolver_integration.py -v

# 验收测试
pytest tests/acceptance/test_task3_budget_auto_derivation.py -v

# 全部测试
pytest tests/unit/core/chat/test_budget_resolver.py \
       tests/integration/chat/test_budget_resolver_integration.py \
       tests/acceptance/test_task3_budget_auto_derivation.py -v
```

## 典型预算示例

| 窗口 | 输入预算 | 生成预算 | System | Window | RAG | Memory |
|------|---------|---------|--------|--------|-----|--------|
| 4k | 2,457 | 1,024 | 307 | 1,228 | 614 | 307 |
| 8k | 4,963 | 2,000 | 620 | 2,481 | 1,240 | 620 |
| 16k | 11,926 | 2,000 | 1,490 | 5,963 | 2,981 | 1,490 |
| 32k | 25,852 | 2,000 | 3,231 | 12,926 | 6,463 | 3,231 |
| 128k | 106,800 | 2,000 | 13,350 | 53,400 | 26,700 | 13,350 |
| 200k | 168,000 | 2,000 | 21,000 | 84,000 | 42,000 | 21,000 |

## 常见问题

### Q1: 如何修改默认分配比例？

```python
custom_allocation = {
    "system": 0.1,   # 10%
    "window": 0.6,   # 60%
    "rag": 0.2,      # 20%
    "memory": 0.1    # 10%
}

budget = resolver.auto_derive_budget(
    model_info,
    allocation=custom_allocation
)
```

### Q2: 如何修改默认生成预算？

```python
budget = resolver.auto_derive_budget(
    model_info,
    generation_max=4000  # 改为 4000 tokens
)
```

### Q3: 如何添加新的已知模型？

编辑 `budget_resolver.py`:

```python
FALLBACK_WINDOWS = {
    ...
    "my-new-model": 50000,
    ...
}
```

### Q4: 预算推导失败怎么办？

```python
try:
    budget = resolver.auto_derive_budget(model_info)
    is_valid, error = resolver.validate_budget(budget)
    if not is_valid:
        raise ValueError(f"Invalid budget: {error}")
except Exception as e:
    # 回退到安全默认
    budget = resolver.get_default_budget()
```

## 相关文件

- **核心实现**: `agentos/core/chat/budget_resolver.py`
- **集成点**: `agentos/core/chat/context_builder.py`
- **自适应**: `agentos/core/chat/adapters.py`
- **单元测试**: `tests/unit/core/chat/test_budget_resolver.py`
- **集成测试**: `tests/integration/chat/test_budget_resolver_integration.py`
- **验收测试**: `tests/acceptance/test_task3_budget_auto_derivation.py`
- **完整报告**: `TASK_3_AUTO_DERIVATION_COMPLETION_REPORT.md`

## 下一步

- **任务 4**: 实施 WebUI 设置界面（依赖 Task 3）
- **任务 5**: 实施运行时可视化（依赖 Task 3）
- **任务 6**: 端到端验收测试（依赖 Task 4 & 5）
