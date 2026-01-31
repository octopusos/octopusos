# Smoke Test - WebUI Chat → CommunicationOS Integration

## 概述

这是一个快速冒烟测试套件,用于验证 WebUI Chat 和 CommunicationOS 接入的基本可用性。

**执行时间**: < 2 分钟
**测试数量**: 6 个核心测试
**策略**: 快速失败 (首个错误时停止)

## 测试覆盖

### 1. 服务启动测试 (Service Startup)
检查必要的服务和模块是否可以正常初始化:
- 导入 WebUI、ChatEngine、CommCommandHandler、CommunicationService
- 实例化核心服务
- 验证连接器注册表初始化

### 2. 命令注册测试 (Command Registration)
验证 /comm 命令已正确注册:
- 检查命令是否在注册表中
- 验证命令描述
- 确认功能特性

### 3. 基本搜索测试 (Basic Search - Mock)
使用 Mock 适配器测试搜索命令:
- 执行 `/comm search` 命令
- 验证返回结果格式
- 检查归因和元数据

### 4. 基本 Fetch 测试 (Basic Fetch - Mock)
使用 Mock 适配器测试 fetch 命令:
- 执行 `/comm fetch` 命令
- 验证抓取内容格式
- 检查信任层级和引用信息

### 5. Phase Gate 测试 (Phase Gate)
验证计划阶段 (Planning Phase) 会阻止命令执行:
- 尝试在 planning 阶段执行 search
- 尝试在 planning 阶段执行 fetch
- 验证错误消息包含阻止信息

### 6. SSRF 防护测试 (SSRF Protection)
验证 SSRF 防护机制:
- 尝试访问 localhost URL
- 验证请求被阻止
- 检查 SSRF 错误消息

## 快速开始

### 运行测试

```bash
# 进入项目目录
cd /Users/pangge/PycharmProjects/AgentOS

# 运行 smoke 测试
python3 test_smoke.py
```

### 使用 pytest (可选)

```bash
# 安装 pytest
pip install pytest

# 运行测试
pytest test_smoke.py -v
```

## 输出文件

运行测试后会生成以下文件:

1. **SMOKE_TEST_REPORT.md** - 详细测试报告
   - 测试结果汇总
   - 每个测试的执行时间
   - 发现的问题 (如有)
   - 测试结论和下一步建议

## 测试结果解读

### ✅ 成功 (All Tests Passed)

```
Total: 6/6 PASSED in X.XXs ✅

Conclusion: System is ready for further testing
```

**含义**: 系统基本可用,可以继续进行更深入的测试。

**下一步**:
1. 执行 E2E (端到端) 测试
2. 运行场景覆盖测试
3. 进行真实模拟测试

### ❌ 失败 (Tests Failed)

```
Total: X/6 PASSED in X.XXs ❌

Conclusion: Critical issues detected - system not ready
```

**含义**: 发现致命问题,系统无法正常工作。

**行动**:
1. 查看 SMOKE_TEST_REPORT.md 了解详细错误
2. 修复问题
3. 重新运行 smoke 测试
4. **不要继续进行其他测试** 直到所有 smoke 测试通过

## 测试设计原则

### 1. 快速 (Fast)
- 总执行时间 < 2 分钟
- 使用 Mock 减少外部依赖
- 不执行真实网络请求

### 2. 简洁 (Simple)
- 每个测试专注单一功能
- 清晰的成功/失败标准
- 易于理解的错误消息

### 3. 致命问题检测 (Critical Issues Only)
- 只检测阻塞性问题
- 不关注性能优化
- 不验证边界情况

### 4. 快速失败 (Fast-Fail)
- 首个测试失败时立即停止
- 避免浪费时间在后续测试
- 优先修复最早发现的问题

## 故障排除

### 导入错误

```
ModuleNotFoundError: No module named 'agentos'
```

**解决**: 确保在项目根目录运行,或安装项目:
```bash
pip install -e .
```

### Mock 路径错误

```
AttributeError: module 'agentos.core.chat.comm_commands' does not have attribute 'CommunicationAdapter'
```

**原因**: CommunicationAdapter 在 `communication_adapter.py` 中定义,不是 `comm_commands.py`

**解决**: 测试脚本已修复为使用正确的 mock 路径:
```python
with patch('agentos.core.chat.communication_adapter.CommunicationAdapter')
```

### Phase Gate 测试失败

**问题**: 命令在 planning 阶段没有被阻止

**检查**:
1. `CommCommandHandler._check_phase_gate()` 是否正确实现
2. 错误消息是否包含 "阻止" 或 "blocked" 或 "forbidden"

### SSRF 测试失败

**问题**: localhost URL 没有被阻止

**检查**:
1. CommunicationService 的 SSRF 防护是否启用
2. PolicyEngine 是否正确配置
3. Mock 是否正确模拟 SSRF 响应

## 扩展测试

如需添加新的 smoke 测试:

1. 在 `test_smoke.py` 中添加测试函数:
```python
def test_new_feature():
    """Test 7: New Feature

    Description of what this test validates.
    """
    # Test implementation
    assert condition, "Error message"
```

2. 在 `main()` 中注册测试:
```python
runner.run_test("Test 7: New Feature", test_new_feature)
```

3. 更新 `generate_report()` 中的测试覆盖文档

## 相关文档

- **系统架构**: `docs/architecture/COMMUNICATION_OS.md`
- **安全策略**: `docs/security/SSRF_PROTECTION.md`
- **Phase Gate**: `docs/design/PHASE_GATE.md`
- **E2E 测试**: `test_e2e.py` (待创建)
- **场景测试**: `test_scenarios.py` (待创建)

## 维护

**更新频率**: 每次重大功能变更后
**维护责任**: AgentOS 核心团队
**测试时机**:
- 每次提交前
- CI/CD 流水线第一步
- 发布前最终验证

---

**Last Updated**: 2026-01-31
**Version**: 1.0
**Status**: ✅ Active
