# Mode Pipeline Demo - 快速开始指南

## 5 分钟快速体验

### 1. 验证安装

```bash
cd /Users/pangge/PycharmProjects/AgentOS
uv run agentos run --help
```

预期输出应显示 `run` 命令的帮助信息。

### 2. Dry-run 模式（无实际执行）

```bash
# 测试开发类需求
uv run agentos run "I need a demo landing page" --dry-run

# 测试只读需求
uv run agentos run "analyze the code" --dry-run

# 测试修复需求
uv run agentos run "fix the login bug" --dry-run
```

你将看到：
- Mode 选择结果（primary_mode, pipeline）
- 选择原因
- 不会实际执行

### 3. 运行测试

```bash
# 运行所有 Mode Pipeline 相关测试
uv run pytest tests/unit/test_mode_selector.py \
             tests/integration/test_pipeline_runner.py \
             tests/e2e/test_mode_pipeline_demo.py -v

# 预期：28 个测试全部通过
```

### 4. 查看 Landing Page 模板

```bash
# 查看 HTML 模板
cat agentos/templates/landing_page/index.html

# 查看 CSS 模板
cat agentos/templates/landing_page/style.css
```

### 5. 测试生成器

```python
# 启动 Python REPL
uv run python3

# 测试 Landing Page Generator
from agentos.core.generators import get_landing_page_generator

generator = get_landing_page_generator()

# 生成 planning 输出
planning = generator.generate_planning_output("test input")
print(planning)

# 生成执行步骤
steps = generator.generate_execution_steps()
print(f"Total steps: {len(steps)}")
print(f"First step: {steps[0]['commit_message']}")
print(f"Last step: {steps[-1]['commit_message']}")
```

## 架构验证

### 验证 Mode System 集成

```python
from agentos.core.mode import get_mode

# Planning mode 不允许 diff
planning = get_mode("planning")
assert planning.allows_diff() == False
assert planning.allows_commit() == False

# Implementation mode 允许 diff
impl = get_mode("implementation")
assert impl.allows_diff() == True
assert impl.allows_commit() == True

print("✅ Mode 闸门验证通过")
```

### 验证 ModeSelector

```python
from agentos.core.mode import ModeSelector

selector = ModeSelector()

# 测试不同类型的需求
tests = [
    ("I need a landing page", ["planning", "implementation"]),
    ("analyze the code", ["chat"]),
    ("fix the bug", ["debug", "implementation"]),
    ("deploy to prod", ["ops"]),
]

for nl_input, expected_pipeline in tests:
    result = selector.select_mode(nl_input)
    assert result.pipeline == expected_pipeline
    print(f"✅ {nl_input[:30]:<30} → {result.pipeline}")
```

### 验证 Pipeline Runner

```python
from pathlib import Path
from unittest.mock import Mock, patch
from agentos.core.mode import ModeSelector, ModePipelineRunner

# Mock Executor
with patch('agentos.core.mode.pipeline_runner.ExecutorEngine') as mock_exec:
    mock_instance = Mock()
    mock_instance.execute.return_value = {"status": "success"}
    mock_exec.return_value = mock_instance
    
    selector = ModeSelector()
    selection = selector.select_mode("create a site")
    
    runner = ModePipelineRunner(output_dir="outputs/test")
    result = runner.run_pipeline(
        mode_selection=selection,
        nl_input="create a site",
        repo_path=Path("."),
        policy_path=None
    )
    
    print(f"✅ Pipeline 执行完成")
    print(f"   - Stages: {len(result.stages)}")
    print(f"   - Status: {result.overall_status}")
    print(f"   - Summary: {result.summary}")
```

## 常见问题

### Q1: 如何添加新的任务类型？

编辑 `agentos/core/mode/mode_selector.py` 的 `RULES` 列表：

```python
{
    "patterns": [
        r"(重构|优化).*(代码|性能)",
        r"(refactor|optimize).*(code|performance)",
    ],
    "primary_mode": "planning",
    "pipeline": ["planning", "implementation"],
    "reason": "Refactoring task detected"
}
```

### Q2: 如何自定义 Pipeline？

修改规则中的 `pipeline` 字段：

```python
# 例如：添加测试阶段
"pipeline": ["planning", "implementation", "test"]
```

### Q3: 如何集成真实的 Executor？

当前 demo 使用 mock Executor。要集成真实执行：

1. 移除测试中的 `@patch` 装饰器
2. 确保 `ExecutorEngine` 可以正确处理 `mode_id` 参数
3. 提供真实的 `policy_path`

### Q4: 如何查看执行日志？

Pipeline 执行后，日志保存在：

```
outputs/pipeline/<pipeline_id>/
├── pipeline_metadata.json
├── pipeline_result.json
└── stage_0_planning/
    └── audit/
        └── run_tape.jsonl
```

## 下一步

### 实际执行 Demo

要运行真实的 landing page 生成（需要集成 LLM）：

1. 配置 LLM 端点
2. 修改 `ModePipelineRunner` 使用真实 Executor
3. 运行：
   ```bash
   agentos run "I need a demo landing page" \
     --repo /path/to/empty/dir \
     --policy policies/sandbox_policy.json
   ```

### 扩展功能

参考 `docs/demo/MODE_PIPELINE_DEMO_COMPLETE.md` 的"后续扩展方向"部分。

---

**文档版本**: 1.0  
**更新时间**: 2026-01-26  
**适用版本**: AgentOS v1.0+
