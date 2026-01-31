# 场景覆盖测试指南

## 概述

本测试套件用于验证 WebUI Chat → CommunicationOS 集成的完整性,确保所有用户场景都被测试覆盖。

## 快速开始

### 运行测试

```bash
# 方式1: 直接运行测试脚本
python3 test_scenario_coverage.py

# 方式2: 使用 pytest (如果已安装)
pytest test_scenario_coverage.py -v
```

### 查看结果

测试完成后会自动生成两个报告文件:

1. **SCENARIO_COVERAGE_TEST_REPORT.md** - 详细测试报告
   - 每个场景的详细结果
   - 预期与实际输出对比
   - 覆盖率统计
   - 失败场景分析

2. **SCENARIO_TEST_EXECUTION_SUMMARY.md** - 执行总结
   - 测试概况
   - 关键发现
   - 问题与处理
   - 建议

## 测试内容

### 测试场景 (20个)

#### 正常流程 (10个)
- ✅ 简单搜索查询
- ✅ 复杂搜索查询
- ✅ 带参数搜索
- ✅ 抓取公开URL
- ✅ 抓取官方文档
- ✅ 生成AI简报
- ✅ 生成带日期简报
- ✅ 限制条目简报
- ✅ 搜索后抓取工作流
- ✅ 连续执行多个命令

#### 错误处理 (5个)
- ✅ 无效命令
- ✅ 缺少参数
- ✅ 无效URL
- ✅ 不存在的URL
- ✅ Planning阶段阻止

#### 安全场景 (3个)
- ✅ SSRF攻击 - localhost
- ✅ SSRF攻击 - 私有IP
- ✅ SSRF攻击 - 元数据端点

#### 边界场景 (2个)
- ✅ 速率限制
- ✅ 超长查询

## 覆盖率目标

- **目标**: ≥ 90% 覆盖率
- **当前**: 100% (20/20 通过)
- **状态**: ✅ 达标

## 测试架构

```python
test_scenario_coverage.py
├── ScenarioCoverageTest           # 主测试类
│   ├── test_scenario_01-10        # 正常流程测试
│   ├── test_scenario_11-15        # 错误处理测试
│   ├── test_scenario_16-18        # 安全测试
│   └── test_scenario_19-20        # 边界测试
└── 辅助函数
    ├── _execute_command()         # 执行命令
    ├── _verify_contains()         # 验证结果
    └── _record_result()           # 记录结果
```

## 示例输出

```
================================================================================
WebUI Chat → CommunicationOS Scenario Coverage Test
================================================================================
Start Time: 2026-01-31T00:12:11.105887
Target: 90%+ coverage (18+ out of 20 scenarios passing)
================================================================================

✅ Pass 01: Simple Search (0.12s)
✅ Pass 02: Complex Search (0.02s)
✅ Pass 03: Search with Parameters (0.02s)
...
✅ Pass 20: Long Query (0.02s)

================================================================================
Test Summary
================================================================================
Total Scenarios: 20
✅ Passed: 20
❌ Failed: 0
⏭️ Skipped: 0
Coverage Rate: 100.0%
Target Met: ✅ YES
================================================================================
```

## 环境要求

### 必需
- Python 3.7+
- AgentOS 项目依赖

### 可选 (用于完整功能)
```bash
# 安装搜索库 (可选)
pip install ddgs

# 或
pip install duckduckgo-search
```

**注意**: 即使不安装搜索库,测试也能通过,因为系统会正确处理缺失依赖的情况。

## 故障排查

### 问题1: 导入错误
```
ModuleNotFoundError: No module named 'agentos'
```

**解决方案**:
```bash
# 确保在项目根目录运行
cd /path/to/AgentOS
python3 test_scenario_coverage.py
```

### 问题2: DuckDuckGo库缺失
```
DuckDuckGo search library not installed
```

**解决方案**:
```bash
# 可选: 安装搜索库
pip install ddgs

# 或继续运行 - 测试会正确处理这种情况
```

### 问题3: 权限错误
```
Permission denied: /Users/xxx/.agentos/
```

**解决方案**:
```bash
# 创建目录
mkdir -p ~/.agentos

# 或使用sudo (不推荐)
sudo python3 test_scenario_coverage.py
```

## 修改测试

### 添加新场景

1. 在 `ScenarioCoverageTest` 类中添加新方法:

```python
def test_scenario_21_new_feature(self):
    """场景21: 新功能测试"""
    start = time.time()
    try:
        result = self._execute_command("/comm new-command")

        success = self._verify_contains(result, [
            "expected", "keywords"
        ])

        self._record_result(
            scenario_id="21",
            name="New Feature",
            description="Test new feature",
            expected="Expected result",
            actual=result,
            status=ScenarioStatus.PASS if success else ScenarioStatus.FAIL,
            duration=time.time() - start
        )
    except Exception as e:
        # Error handling
        pass
```

2. 在 `run_all_scenarios()` 中添加到测试列表:

```python
test_methods = [
    # ... existing tests ...
    self.test_scenario_21_new_feature,
]
```

## 持续集成

### GitHub Actions 示例

```yaml
name: Scenario Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run scenario tests
        run: |
          python3 test_scenario_coverage.py
      - name: Upload test report
        uses: actions/upload-artifact@v2
        with:
          name: test-report
          path: SCENARIO_COVERAGE_TEST_REPORT.md
```

## 相关文档

- **详细报告**: `SCENARIO_COVERAGE_TEST_REPORT.md`
- **执行总结**: `SCENARIO_TEST_EXECUTION_SUMMARY.md`
- **命令文档**: `docs/chat/COMM_COMMANDS.md`
- **框架文档**: `COMM_FRAMEWORK_COMPLETED.md`

## 联系与支持

如有问题或建议,请参考项目文档或提交issue。

---

**最后更新**: 2026-01-31
**测试版本**: v1.0
**状态**: ✅ 所有测试通过
