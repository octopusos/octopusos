# Mode Bug 修复测试指南

**版本**: 1.0.0
**生效日期**: 2026-01-30
**状态**: Active

---

## 目录

1. [测试概述](#1-测试概述)
2. [测试类型](#2-测试类型)
3. [测试覆盖率要求](#3-测试覆盖率要求)
4. [测试工具](#4-测试工具)
5. [测试用例模板](#5-测试用例模板)
6. [测试报告模板](#6-测试报告模板)
7. [最佳实践](#7-最佳实践)

---

## 1. 测试概述

### 1.1 测试目标

Bug 修复测试的主要目标：

1. **验证修复** - 确保 Bug 已被修复
2. **防止回归** - 确保同样的问题不会再次出现
3. **保证质量** - 确保修复没有引入新问题
4. **验证性能** - 确保性能没有退化

### 1.2 测试原则

- **必要性** - 每个 Bug 修复必须有对应的回归测试
- **完整性** - 测试应覆盖 Bug 场景和边界条件
- **独立性** - 测试应独立运行，不依赖其他测试
- **可重复性** - 测试结果应一致可重复

### 1.3 测试金字塔

```
         /\
        /  \  E2E Tests (少)
       /────\
      /      \  Integration Tests (中)
     /────────\
    /          \  Unit Tests (多)
   /────────────\
```

**测试分布建议**:
- **单元测试**: 70% - 快速、隔离、大量
- **集成测试**: 20% - 中速、组件间、适量
- **端到端测试**: 10% - 慢速、全链路、少量

---

## 2. 测试类型

### 2.1 单元测试 (Unit Tests)

#### 定义
测试单个函数或方法的最小可测试单元。

#### 特点
- ✅ 快速执行 (< 1 秒)
- ✅ 完全隔离
- ✅ 不依赖外部资源
- ✅ 易于调试

#### 示例

```python
# tests/unit/mode/test_mode_policy.py

import pytest
from agentos.core.mode import ModePolicy

def test_evaluate_with_none_rules():
    """
    单元测试：测试 rules 为 None 的情况
    """
    # Arrange (准备)
    policy = ModePolicy(rules=None)

    # Act (执行)
    result = policy.evaluate("read")

    # Assert (断言)
    assert result is False

def test_evaluate_with_valid_rules():
    """
    单元测试：测试 rules 正常的情况
    """
    rules = [{"mode": "read", "action": "allow"}]
    policy = ModePolicy(rules=rules)

    result = policy.evaluate("read")

    assert result is True
```

#### 最佳实践

1. **使用 AAA 模式** (Arrange-Act-Assert)
   ```python
   def test_example():
       # Arrange - 准备测试数据
       policy = ModePolicy()

       # Act - 执行被测方法
       result = policy.evaluate("read")

       # Assert - 验证结果
       assert result is True
   ```

2. **一个测试一个断言**
   ```python
   # ✅ 好的做法
   def test_evaluate_returns_true():
       assert policy.evaluate("read") is True

   def test_evaluate_returns_false():
       assert policy.evaluate("invalid") is False

   # ❌ 不好的做法
   def test_evaluate():
       assert policy.evaluate("read") is True
       assert policy.evaluate("invalid") is False  # 如果第一个失败，这个不会执行
   ```

3. **使用 Mock 隔离依赖**
   ```python
   from unittest.mock import Mock, patch

   def test_with_mock():
       # Mock 外部依赖
       with patch('agentos.core.mode.external_service') as mock_service:
           mock_service.return_value = True

           policy = ModePolicy()
           result = policy.evaluate("read")

           assert result is True
           mock_service.assert_called_once()
   ```

---

### 2.2 集成测试 (Integration Tests)

#### 定义
测试多个组件之间的交互和集成。

#### 特点
- ⚡ 中等速度 (1-10 秒)
- 🔗 测试组件间交互
- 💾 可能使用真实资源 (测试数据库等)
- 🎯 验证端到端流程

#### 示例

```python
# tests/integration/mode/test_mode_system_integration.py

import pytest
from agentos.core.mode import ModePolicy, ModeSelector, ModeMonitor

@pytest.fixture
def mode_system():
    """准备完整的 Mode 系统"""
    policy = ModePolicy.load_from_config("configs/mode/test_policy.json")
    selector = ModeSelector(policy)
    monitor = ModeMonitor()
    return policy, selector, monitor

def test_mode_selection_flow(mode_system):
    """
    集成测试：测试 Mode 选择完整流程
    """
    policy, selector, monitor = mode_system

    # 1. 策略允许 read 模式
    assert policy.evaluate("read") is True

    # 2. Selector 选择 read 模式
    selected = selector.select(["read", "write"])
    assert selected == "read"

    # 3. Monitor 记录选择
    monitor.record(selected)
    stats = monitor.get_stats()
    assert stats["read"] == 1

def test_policy_reload_integration():
    """
    集成测试：测试策略重新加载
    """
    # 初始策略
    policy = ModePolicy.load_from_config("configs/mode/default_policy.json")
    assert policy.evaluate("write") is True

    # 修改配置文件
    with open("configs/mode/test_policy.json", "w") as f:
        f.write('{"rules": [{"mode": "write", "action": "deny"}]}')

    # 重新加载
    policy.reload()

    # 验证新策略生效
    assert policy.evaluate("write") is False
```

#### 最佳实践

1. **使用 Fixture 准备环境**
   ```python
   @pytest.fixture(scope="function")
   def test_db():
       """为每个测试创建临时数据库"""
       db = create_test_database()
       yield db
       db.close()
   ```

2. **清理测试数据**
   ```python
   @pytest.fixture
   def temp_config():
       """创建临时配置文件"""
       config_path = "/tmp/test_config.json"
       with open(config_path, "w") as f:
           f.write('{}')

       yield config_path

       # 清理
       os.remove(config_path)
   ```

3. **测试错误处理**
   ```python
   def test_invalid_config_handling():
       """测试无效配置的处理"""
       with pytest.raises(ConfigError):
           ModePolicy.load_from_config("invalid_path.json")
   ```

---

### 2.3 端到端测试 (E2E Tests)

#### 定义
测试整个系统从用户角度的完整流程。

#### 特点
- 🐌 较慢 (10秒-分钟)
- 🌐 使用真实环境
- 👤 模拟用户行为
- 🎭 测试完整场景

#### 示例

```python
# tests/e2e/test_mode_system_e2e.py

import pytest
from agentos.core.task import TaskRunner
from agentos.core.mode import ModeSystem

@pytest.mark.e2e
def test_full_task_lifecycle_with_mode():
    """
    E2E 测试：测试带 Mode 的任务完整生命周期
    """
    # 1. 初始化系统
    mode_system = ModeSystem()
    runner = TaskRunner(mode_system=mode_system)

    # 2. 创建任务
    task = runner.create_task(
        name="test_task",
        mode="read",
        command="echo 'hello'"
    )
    assert task.id is not None

    # 3. 执行任务
    result = runner.run_task(task.id)

    # 4. 验证结果
    assert result.status == "completed"
    assert result.output == "hello\n"

    # 5. 检查 Mode 监控
    stats = mode_system.monitor.get_stats()
    assert stats["read"] == 1

@pytest.mark.e2e
def test_mode_policy_violation_handling():
    """
    E2E 测试：测试策略违规处理
    """
    # 配置禁止 write 的策略
    mode_system = ModeSystem(policy="strict")
    runner = TaskRunner(mode_system=mode_system)

    # 尝试执行 write 操作
    task = runner.create_task(
        name="write_task",
        mode="write",
        command="echo 'data' > file.txt"
    )

    # 应该被拒绝
    with pytest.raises(PolicyViolationError):
        runner.run_task(task.id)

    # 验证告警
    alerts = mode_system.alerts.get_recent()
    assert len(alerts) == 1
    assert alerts[0].type == "policy_violation"
```

#### 最佳实践

1. **使用标记隔离慢测试**
   ```python
   @pytest.mark.e2e
   @pytest.mark.slow
   def test_full_system():
       # 慢速 E2E 测试
       pass
   ```

   运行时可以选择:
   ```bash
   # 只运行快速测试
   pytest -m "not slow"

   # 运行所有测试包括 E2E
   pytest -m "e2e"
   ```

2. **使用真实但隔离的环境**
   ```python
   @pytest.fixture(scope="session")
   def test_environment():
       """为测试会话创建隔离环境"""
       env = create_isolated_environment()
       yield env
       teardown_environment(env)
   ```

3. **测试关键用户路径**
   ```python
   def test_happy_path():
       """测试正常用户流程"""
       pass

   def test_error_recovery_path():
       """测试错误恢复流程"""
       pass
   ```

---

### 2.4 回归测试 (Regression Tests)

#### 定义
专门用于验证 Bug 修复的测试，防止问题再次出现。

#### 特点
- 🎯 针对特定 Bug
- 📝 与 Issue 关联
- 🔒 长期保留
- 📚 文档化

#### 示例

```python
# tests/unit/mode/test_mode_policy_bugfix_123.py

"""
回归测试：Issue #123 - Mode policy crash when rules is None

问题描述：
  当 ModePolicy.rules 为 None 时，evaluate() 方法会崩溃。

修复方案：
  添加 None 检查，返回 False (deny-by-default)。

测试策略：
  1. 测试 rules 为 None 的情况
  2. 测试边界条件（空字符串、None mode等）
  3. 测试正常情况仍然工作

相关：
  - Issue: #123
  - PR: #456
  - 修复日期: 2026-01-15
"""

import pytest
from agentos.core.mode import ModePolicy

class TestBugfix123:
    """回归测试集：Issue #123"""

    def test_evaluate_with_none_rules(self, caplog):
        """
        回归测试：修复 Issue #123
        当 rules 为 None 时，evaluate 应该返回 False 而不是崩溃
        """
        policy = ModePolicy(rules=None)

        # 修复前：会抛出 AttributeError
        # 修复后：返回 False
        result = policy.evaluate("read")

        assert result is False
        assert "Mode policy rules is None" in caplog.text

    def test_evaluate_with_empty_mode(self):
        """
        回归测试：边界条件 - 空字符串 mode
        """
        policy = ModePolicy(rules=None)

        assert policy.evaluate("") is False
        assert policy.evaluate(None) is False

    def test_evaluate_with_invalid_mode_type(self):
        """
        回归测试：边界条件 - 无效的 mode 类型
        """
        policy = ModePolicy(rules=None)

        assert policy.evaluate(123) is False
        assert policy.evaluate([]) is False
        assert policy.evaluate({}) is False

    def test_evaluate_normal_case_still_works(self):
        """
        回归测试：确保修复不影响正常情况
        """
        policy = ModePolicy.load_from_config("configs/mode/default_policy.json")

        # 正常情况应该仍然工作
        assert policy.evaluate("read") is True
        assert policy.evaluate("write") is True
```

#### 命名规范

```
测试文件：test_{module}_bugfix_{issue_number}.py
测试类：TestBugfix{issue_number}
测试方法：test_{scenario}_issue_{issue_number}
```

---

### 2.5 性能测试 (Performance Tests)

#### 定义
验证修复没有引入性能退化。

#### 特点
- ⏱️ 测量执行时间
- 📊 统计性能指标
- 🎯 设定性能基准
- 🔔 性能退化告警

#### 示例

```python
# tests/performance/test_mode_policy_performance.py

import pytest
import time
from agentos.core.mode import ModePolicy

@pytest.mark.performance
def test_evaluate_performance():
    """
    性能测试：evaluate() 方法性能
    基准：< 1ms per call
    """
    policy = ModePolicy.load_from_config("configs/mode/default_policy.json")

    iterations = 10000

    start = time.perf_counter()
    for _ in range(iterations):
        policy.evaluate("read")
    duration = time.perf_counter() - start

    avg_ms = (duration / iterations) * 1000

    # 断言：平均每次调用 < 1ms
    assert avg_ms < 1.0, f"Performance regression: {avg_ms}ms per call (target: <1ms)"

    # 记录性能数据
    print(f"\nPerformance: {avg_ms:.3f}ms per call")

@pytest.mark.performance
def test_policy_loading_performance():
    """
    性能测试：策略加载性能
    基准：< 100ms
    """
    start = time.perf_counter()
    policy = ModePolicy.load_from_config("configs/mode/large_policy.json")
    duration = (time.perf_counter() - start) * 1000

    assert duration < 100, f"Loading too slow: {duration}ms (target: <100ms)"

@pytest.mark.performance
def test_memory_usage():
    """
    性能测试：内存使用
    """
    import tracemalloc

    tracemalloc.start()

    # 创建策略
    policy = ModePolicy.load_from_config("configs/mode/default_policy.json")

    # 执行操作
    for _ in range(1000):
        policy.evaluate("read")

    # 检查内存
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)

    # 断言：峰值内存 < 10MB
    assert peak_mb < 10, f"Memory usage too high: {peak_mb}MB (target: <10MB)"
```

#### 性能基准

| 操作 | 目标 | 警告阈值 |
|------|------|---------|
| **evaluate()** | < 1ms | > 5ms |
| **load_policy()** | < 100ms | > 500ms |
| **内存使用** | < 10MB | > 50MB |
| **吞吐量** | > 1000 ops/s | < 500 ops/s |

---

### 2.6 安全测试 (Security Tests)

#### 定义
验证修复没有引入安全漏洞。

#### 示例

```python
# tests/security/test_mode_policy_security.py

import pytest
from agentos.core.mode import ModePolicy, SecurityError

@pytest.mark.security
def test_path_traversal_blocked():
    """
    安全测试：路径遍历攻击应该被阻止
    """
    policy = ModePolicy()

    # 尝试路径遍历攻击
    with pytest.raises(SecurityError):
        policy.load_policy("../../../etc/passwd")

@pytest.mark.security
def test_sql_injection_protection():
    """
    安全测试：SQL 注入防护
    """
    policy = ModePolicy()

    # 尝试 SQL 注入
    malicious_mode = "read'; DROP TABLE users; --"

    # 应该安全处理，不崩溃
    result = policy.evaluate(malicious_mode)
    assert result is False

@pytest.mark.security
def test_xss_protection():
    """
    安全测试：XSS 防护
    """
    policy = ModePolicy()

    # 尝试 XSS 攻击
    malicious_mode = "<script>alert('xss')</script>"

    result = policy.evaluate(malicious_mode)
    assert result is False
```

---

## 3. 测试覆盖率要求

### 3.1 覆盖率目标

| Bug 级别 | 覆盖率要求 | 说明 |
|---------|-----------|------|
| **P0** | 100% | 新增代码必须 100% 覆盖 |
| **P1** | 90%+ | 核心逻辑必须覆盖 |
| **P2** | 80%+ | 主要路径覆盖 |
| **P3** | 70%+ | 基本覆盖即可 |

### 3.2 覆盖率类型

#### 行覆盖率 (Line Coverage)
```bash
# 运行覆盖率测试
pytest tests/unit/mode/ --cov=agentos/core/mode --cov-report=term-missing

# 输出示例
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
agentos/core/mode/mode_policy.py          45      2    96%   123-124
agentos/core/mode/mode_selector.py        38      0   100%
---------------------------------------------------------------------
TOTAL                                     83      2    98%
```

#### 分支覆盖率 (Branch Coverage)
```bash
# 运行分支覆盖率测试
pytest tests/unit/mode/ --cov=agentos/core/mode --cov-branch --cov-report=html

# 生成 HTML 报告
# 打开 htmlcov/index.html 查看详细报告
```

### 3.3 覆盖率报告

```python
# 配置 pytest-cov 在 pytest.ini
[tool:pytest]
addopts =
    --cov=agentos/core/mode
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

---

## 4. 测试工具

### 4.1 pytest - 测试框架

#### 基础用法

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/unit/mode/test_mode_policy.py

# 运行特定测试
pytest tests/unit/mode/test_mode_policy.py::test_evaluate

# 详细输出
pytest -v

# 显示打印输出
pytest -s

# 只运行失败的测试
pytest --lf

# 并行运行
pytest -n auto
```

#### Fixture 使用

```python
import pytest

@pytest.fixture
def mode_policy():
    """提供 ModePolicy 实例"""
    return ModePolicy()

@pytest.fixture(scope="session")
def test_database():
    """会话级别的数据库 fixture"""
    db = setup_database()
    yield db
    teardown_database(db)

def test_with_fixture(mode_policy):
    """使用 fixture 的测试"""
    result = mode_policy.evaluate("read")
    assert result is True
```

### 4.2 unittest.mock - Mock 工具

```python
from unittest.mock import Mock, MagicMock, patch, call

# Mock 对象
mock_service = Mock()
mock_service.get_data.return_value = {"key": "value"}

# Patch 函数
with patch('module.function') as mock_func:
    mock_func.return_value = 42
    result = my_code()
    assert result == 42

# Patch 类
with patch('module.MyClass') as MockClass:
    instance = MockClass.return_value
    instance.method.return_value = 'mocked'
    # 使用 mock

# 验证调用
mock_func.assert_called_once_with(arg1, arg2)
mock_func.assert_called_with(arg1, kwarg=value)
assert mock_func.call_count == 3
```

### 4.3 pytest-cov - 覆盖率工具

```bash
# 基础覆盖率
pytest --cov=agentos/core/mode

# 生成 HTML 报告
pytest --cov=agentos/core/mode --cov-report=html

# 显示缺失的行
pytest --cov=agentos/core/mode --cov-report=term-missing

# 设置最低覆盖率
pytest --cov=agentos/core/mode --cov-fail-under=80

# 分支覆盖率
pytest --cov=agentos/core/mode --cov-branch
```

### 4.4 pytest-benchmark - 性能测试

```python
def test_performance(benchmark):
    """使用 pytest-benchmark 进行性能测试"""
    policy = ModePolicy()

    # benchmark 会自动运行多次并统计
    result = benchmark(policy.evaluate, "read")

    assert result is True

# 运行性能测试
# pytest tests/performance/ --benchmark-only
```

### 4.5 pytest-timeout - 超时控制

```python
import pytest

@pytest.mark.timeout(10)
def test_with_timeout():
    """10秒超时的测试"""
    # 如果超过10秒未完成，测试失败
    pass

# 配置全局超时
# pytest.ini:
# [pytest]
# timeout = 300
```

### 4.6 pytest-xdist - 并行测试

```bash
# 自动使用所有 CPU 核心
pytest -n auto

# 使用 4 个进程
pytest -n 4

# 分布式测试（跨机器）
pytest --dist loadscope
```

---

## 5. 测试用例模板

### 5.1 单元测试模板

```python
# tests/unit/mode/test_{module}.py

"""
模块测试：{module_name}

测试范围：
  - 正常功能
  - 边界条件
  - 错误处理

依赖：
  - 无（完全隔离）
"""

import pytest
from agentos.core.mode import {ClassName}

class Test{ClassName}:
    """测试类：{ClassName}"""

    @pytest.fixture
    def instance(self):
        """创建测试实例"""
        return {ClassName}()

    def test_{method}_normal_case(self, instance):
        """
        测试：{method} - 正常情况
        """
        # Arrange
        input_data = "test"

        # Act
        result = instance.{method}(input_data)

        # Assert
        assert result == expected

    def test_{method}_boundary_case(self, instance):
        """
        测试：{method} - 边界条件
        """
        # 测试空输入
        assert instance.{method}("") == expected

        # 测试 None
        assert instance.{method}(None) == expected

    def test_{method}_error_case(self, instance):
        """
        测试：{method} - 错误处理
        """
        with pytest.raises(ExpectedError):
            instance.{method}(invalid_input)
```

### 5.2 集成测试模板

```python
# tests/integration/mode/test_{feature}_integration.py

"""
集成测试：{feature_name}

测试范围：
  - 组件间交互
  - 端到端流程
  - 真实环境验证

依赖：
  - 测试数据库
  - 测试配置文件
"""

import pytest
from agentos.core.mode import ComponentA, ComponentB

@pytest.fixture(scope="module")
def test_environment():
    """准备测试环境"""
    env = setup_test_environment()
    yield env
    teardown_test_environment(env)

def test_{feature}_integration_flow(test_environment):
    """
    集成测试：{feature} 完整流程
    """
    # 1. 初始化组件
    comp_a = ComponentA(test_environment)
    comp_b = ComponentB(test_environment)

    # 2. 执行流程
    result_a = comp_a.process()
    result_b = comp_b.process(result_a)

    # 3. 验证结果
    assert result_b.status == "success"
    assert result_b.data == expected_data

def test_{feature}_integration_error_handling(test_environment):
    """
    集成测试：{feature} 错误处理
    """
    comp_a = ComponentA(test_environment)

    # 模拟错误情况
    with pytest.raises(IntegrationError):
        comp_a.process_invalid_data()
```

### 5.3 回归测试模板

```python
# tests/unit/mode/test_{module}_bugfix_{issue}.py

"""
回归测试：Issue #{issue_number} - {bug_title}

问题描述：
  {detailed_description}

修复方案：
  {fix_description}

测试策略：
  {test_strategy}

相关：
  - Issue: #{issue_number}
  - PR: #{pr_number}
  - 修复日期: {date}
  - 修复人: {author}
"""

import pytest
from agentos.core.mode import {ClassName}

class TestBugfix{issue_number}:
    """回归测试集：Issue #{issue_number}"""

    def test_{scenario}_issue_{issue_number}(self):
        """
        回归测试：Issue #{issue_number} - {scenario}

        Before fix: {behavior_before}
        After fix: {behavior_after}
        """
        # 重现 Bug 场景
        instance = {ClassName}({bug_trigger_params})

        # 验证修复
        result = instance.{method}()

        # 断言修复后的行为
        assert result == expected_after_fix

    def test_{scenario}_boundary_issue_{issue_number}(self):
        """
        回归测试：Issue #{issue_number} - 边界条件

        测试相关的边界情况，确保修复全面。
        """
        # 测试边界条件
        pass

    def test_{scenario}_no_regression_issue_{issue_number}(self):
        """
        回归测试：Issue #{issue_number} - 无回归

        确保修复不影响正常情况。
        """
        # 测试正常情况
        pass
```

---

## 6. 测试报告模板

### 6.1 测试执行报告

```markdown
# 测试执行报告

**Bug Issue**: #{issue_number}
**测试日期**: {date}
**测试人员**: {tester}
**测试环境**: {environment}

---

## 1. 测试摘要

| 测试类型 | 总数 | 通过 | 失败 | 跳过 | 通过率 |
|---------|------|------|------|------|--------|
| 单元测试 | {total} | {passed} | {failed} | {skipped} | {rate}% |
| 集成测试 | {total} | {passed} | {failed} | {skipped} | {rate}% |
| E2E 测试 | {total} | {passed} | {failed} | {skipped} | {rate}% |
| 性能测试 | {total} | {passed} | {failed} | {skipped} | {rate}% |
| **总计** | **{total}** | **{passed}** | **{failed}** | **{skipped}** | **{rate}%** |

---

## 2. 覆盖率报告

| 模块 | 语句覆盖率 | 分支覆盖率 | 缺失行 |
|------|-----------|-----------|--------|
| {module1} | {line_coverage}% | {branch_coverage}% | {missing} |
| {module2} | {line_coverage}% | {branch_coverage}% | {missing} |
| **总计** | **{total_coverage}%** | **{branch_coverage}%** | **-** |

---

## 3. 性能指标

| 指标 | 目标 | 实际 | 结果 |
|------|------|------|------|
| evaluate() 平均时间 | < 1ms | {actual}ms | ✅/❌ |
| load_policy() 时间 | < 100ms | {actual}ms | ✅/❌ |
| 内存峰值 | < 10MB | {actual}MB | ✅/❌ |
| 吞吐量 | > 1000 ops/s | {actual} ops/s | ✅/❌ |

---

## 4. 失败的测试

{如果有失败的测试，列出详情}

### Test #{index}: {test_name}

**失败原因**: {reason}

**错误信息**:
\```
{error_message}
\```

**修复计划**: {plan}

---

## 5. 安全扫描结果

| 工具 | 漏洞数 | 严重 | 高 | 中 | 低 |
|------|--------|------|----|----|----| | bandit | {total} | {critical} | {high} | {medium} | {low} |
| safety | {total} | {critical} | {high} | {medium} | {low} |

---

## 6. 测试结论

**总体评价**: ✅ 通过 / ❌ 不通过

**结论说明**:
{detailed_conclusion}

**建议**:
- {recommendation1}
- {recommendation2}

---

**测试负责人签名**: {name}
**审批日期**: {date}
```

---

## 7. 最佳实践

### 7.1 测试命名

```python
# ✅ 好的命名：清晰描述测试内容
def test_evaluate_returns_false_when_rules_is_none():
    pass

def test_evaluate_raises_error_for_invalid_mode_type():
    pass

# ❌ 不好的命名：不清晰
def test_1():
    pass

def test_bug():
    pass
```

### 7.2 测试隔离

```python
# ✅ 好的做法：每个测试独立
def test_a():
    policy = ModePolicy()  # 独立实例
    assert policy.evaluate("read") is True

def test_b():
    policy = ModePolicy()  # 独立实例
    assert policy.evaluate("write") is True

# ❌ 不好的做法：测试间有依赖
shared_policy = ModePolicy()

def test_a():
    shared_policy.evaluate("read")  # 修改了共享状态

def test_b():
    # 依赖 test_a 的状态
    shared_policy.evaluate("write")
```

### 7.3 测试数据

```python
# ✅ 好的做法：使用 fixture
@pytest.fixture
def test_data():
    return {
        "valid_mode": "read",
        "invalid_mode": "invalid",
        "rules": [...]
    }

def test_with_fixture(test_data):
    policy = ModePolicy(rules=test_data["rules"])
    assert policy.evaluate(test_data["valid_mode"]) is True

# ✅ 好的做法：使用 parametrize
@pytest.mark.parametrize("mode,expected", [
    ("read", True),
    ("write", True),
    ("invalid", False),
])
def test_evaluate_modes(mode, expected):
    policy = ModePolicy()
    assert policy.evaluate(mode) == expected
```

### 7.4 测试断言

```python
# ✅ 好的做法：清晰的断言消息
assert result is True, f"Expected True, got {result}"
assert len(items) == 3, f"Expected 3 items, got {len(items)}"

# ✅ 好的做法：使用 pytest 的断言
assert result == expected  # pytest 会显示详细的对比

# ✅ 好的做法：测试异常
with pytest.raises(ValueError, match="Invalid mode"):
    policy.evaluate(invalid_mode)

# ❌ 不好的做法：不清晰的断言
assert result  # 不知道期望什么
```

### 7.5 测试组织

```
tests/
├── unit/                    # 单元测试
│   └── mode/
│       ├── test_mode_policy.py
│       ├── test_mode_selector.py
│       └── test_mode_policy_bugfix_123.py  # 回归测试
├── integration/             # 集成测试
│   └── mode/
│       └── test_mode_system_integration.py
├── e2e/                    # 端到端测试
│   └── test_mode_system_e2e.py
├── performance/            # 性能测试
│   └── test_mode_policy_performance.py
├── security/               # 安全测试
│   └── test_mode_policy_security.py
└── conftest.py            # 共享 fixture
```

---

## 相关文档

- [MODE_BUG_FIX_PROCESS.md](./MODE_BUG_FIX_PROCESS.md) - Bug 修复流程
- [MODE_BUG_FIX_WORKFLOW.md](./MODE_BUG_FIX_WORKFLOW.md) - 工作流程图
- [templates/BUG_FIX_TEMPLATE.md](./templates/BUG_FIX_TEMPLATE.md) - Bug 修复模板
- [examples/MODE_BUG_FIX_EXAMPLES.md](./examples/MODE_BUG_FIX_EXAMPLES.md) - 修复示例

---

**文档状态**: ✅ Active
**最后更新**: 2026-01-30
**维护者**: QA Team & Architecture Committee
