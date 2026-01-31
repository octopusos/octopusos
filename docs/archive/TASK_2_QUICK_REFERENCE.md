# 任务 2：配置层改造 - 快速参考

## 快速开始

### 1. 加载和保存配置

```python
from agentos.config import load_budget_config, save_budget_config

# 加载全局配置
config = load_budget_config()

# 修改配置
config.max_tokens = 16000

# 保存配置
save_budget_config(config)
```

### 2. 创建自定义配置

```python
from agentos.config import BudgetConfig, BudgetAllocation

config = BudgetConfig(
    max_tokens=32000,
    allocation=BudgetAllocation(
        window_tokens=16000,
        rag_tokens=8000,
        memory_tokens=4000,
        summary_tokens=2000,
        system_tokens=2000,
    ),
    generation_max_tokens=4000,
)
```

### 3. 自动推导预算

```python
from agentos.config import BudgetConfig

# 从模型上下文窗口推导
base = BudgetConfig(generation_max_tokens=4000, safety_margin=0.2)
config = base.derive_from_model_window(128000)  # GPT-4

print(f"Derived max_tokens: {config.max_tokens}")  # 98400
```

### 4. 项目级配置

```python
from agentos.config import BudgetConfig
from agentos.schemas.project import Project, ProjectSettings

project = Project(
    id="proj_001",
    name="My Project",
    settings=ProjectSettings(
        budget=BudgetConfig(max_tokens=32000).to_dict()
    )
)
```

### 5. 优先级解析

```python
from agentos.config import get_budget_config_manager

manager = get_budget_config_manager()

# 解析配置：Session > Project > Global
config = manager.resolve_config(
    session_budget={"max_tokens": 32000},
    project_budget={"max_tokens": 16000},
)
```

## 核心 API

### BudgetConfig

```python
@dataclass
class BudgetConfig:
    max_tokens: int = 8000
    auto_derive: bool = False
    allocation: BudgetAllocation = field(default_factory=BudgetAllocation)
    safety_margin: float = 0.2
    generation_max_tokens: int = 2000
    safe_threshold: float = 0.6
    critical_threshold: float = 0.8
```

**方法：**
- `to_dict()`: 转换为字典
- `from_dict(data)`: 从字典创建
- `derive_from_model_window(window)`: 自动推导

### BudgetAllocation

```python
@dataclass
class BudgetAllocation:
    window_tokens: int = 4000
    rag_tokens: int = 2000
    memory_tokens: int = 1000
    summary_tokens: int = 1000
    system_tokens: int = 1000
```

### BudgetConfigManager

```python
class BudgetConfigManager:
    def load() -> BudgetConfig
    def save(config: BudgetConfig)
    def update_max_tokens(max_tokens: int)
    def update_allocation(window_tokens=None, rag_tokens=None, ...)
    def update_auto_derive(enabled: bool)
    def resolve_config(session_budget=None, project_budget=None) -> BudgetConfig
```

### ContextBudget（扩展）

```python
@dataclass
class ContextBudget:
    # 原有字段
    max_tokens: int = 8000
    system_tokens: int = 1000
    window_tokens: int = 4000
    rag_tokens: int = 2000
    memory_tokens: int = 1000
    summary_tokens: int = 0

    # 新增字段
    generation_max_tokens: int = 2000  # 生成 token 上限
    auto_derived: bool = False         # 是否自动推导
    model_context_window: Optional[int] = None  # 模型窗口

    # 阈值
    safe_threshold: float = 0.6
    critical_threshold: float = 0.8
```

## 配置文件位置

```
~/.agentos/config/budget.json
```

**格式：**
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

## 优先级规则

```
Session Config (最高优先级)
    ↓
Project Config
    ↓
Global Config (~/.agentos/config/budget.json)
    ↓
Default Config (代码默认值)
```

## 自动推导公式

```python
# 输入：model_context_window = 128000
# 配置：safety_margin = 0.2, generation_max_tokens = 4000

effective_window = model_context_window * (1 - safety_margin)
# = 128000 * 0.8 = 102400

available_for_context = effective_window - generation_max_tokens
# = 102400 - 4000 = 98400

# 然后按比例缩放各组件分配
```

## 常见场景

### 场景 1：为小模型配置（8k 上下文）

```python
config = BudgetConfig(
    max_tokens=6000,
    generation_max_tokens=2000,
    allocation=BudgetAllocation(
        window_tokens=3000,
        rag_tokens=1500,
        memory_tokens=750,
        summary_tokens=500,
        system_tokens=250,
    ),
)
```

### 场景 2：为大模型配置（128k 上下文）

```python
config = BudgetConfig().derive_from_model_window(128000)
# 自动计算所有分配
```

### 场景 3：生产环境（低安全边距）

```python
config = BudgetConfig(
    safety_margin=0.1,  # 只保留 10% 安全边距
    generation_max_tokens=8000,
).derive_from_model_window(200000)
```

### 场景 4：测试环境（严格限制）

```python
config = BudgetConfig(
    max_tokens=2000,
    generation_max_tokens=500,
    safety_margin=0.3,  # 30% 安全边距
)
```

## 测试命令

```bash
# 运行所有配置测试
python3 -m pytest tests/unit/config/test_budget_config.py -v

# 运行项目集成测试
python3 -m pytest tests/unit/schemas/test_project_budget_integration.py -v

# 运行 ContextBudget 扩展测试
python3 -m pytest tests/unit/chat/test_context_budget_extension.py -v

# 运行所有测试并查看覆盖率
python3 -m pytest tests/unit/config/ tests/unit/schemas/test_project_budget_integration.py tests/unit/chat/test_context_budget_extension.py --cov=agentos.config.budget_config --cov-report=term-missing

# 运行示例
python3 examples/budget_config_demo.py
```

## 故障排查

### 问题 1：配置文件找不到

**症状：** `FileNotFoundError`

**解决：** 配置文件会自动创建，检查权限

```python
from agentos.config import load_budget_config
config = load_budget_config()  # 自动创建 ~/.agentos/config/budget.json
```

### 问题 2：配置未生效

**症状：** 修改配置后没有变化

**解决：** 检查优先级，可能被更高优先级覆盖

```python
# 检查解析结果
manager = get_budget_config_manager()
config = manager.resolve_config()
print(config.max_tokens)
```

### 问题 3：序列化错误

**症状：** `TypeError: Object of type X is not JSON serializable`

**解决：** 使用 `to_dict()` 方法

```python
config = BudgetConfig(max_tokens=16000)
dict_data = config.to_dict()  # 正确
json_str = json.dumps(dict_data)
```

## 性能注意事项

1. **配置缓存**：配置加载后建议缓存，避免频繁读文件
2. **原子写入**：保存操作使用原子写入，并发安全
3. **内存占用**：配置对象很小（<1KB），可以安全缓存

## 下一步

1. 查看完整实施报告：`TASK_2_CONFIG_LAYER_IMPLEMENTATION_REPORT.md`
2. 运行示例代码：`python3 examples/budget_config_demo.py`
3. 继续任务 3：实施自动推导逻辑
