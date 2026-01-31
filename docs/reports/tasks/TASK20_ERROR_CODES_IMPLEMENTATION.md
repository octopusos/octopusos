# Task #20 Implementation Report: 错误码与可操作提示改进

**Task ID**: P1.7
**Status**: ✅ Completed
**Date**: 2026-01-29

## 概述

实施了 PROVIDERS_FIX_CHECKLIST_V2.md 的 Task 7，为核心错误场景添加了详细提示和解决方案。基于现有的 27 个错误码，为 5 个最重要的错误场景创建了详细的错误构建函数。

## 实施内容

### 1. 新增错误码常量

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/providers_errors.py`

新增错误码：
```python
# Action Errors
UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"
```

### 2. 核心错误构建函数

实施了 5 个详细错误构建函数，每个函数都返回包含以下字段的字典：
- `code`: 错误码
- `message`: 简短消息（中文）
- `details`: 技术细节字典
- `suggestion`: 详细解决方案（多行、平台特定）
- `status_code`: HTTP 状态码

#### 2.1 build_exe_not_found_error()

**功能**: 为可执行文件未找到场景构建详细错误

**参数**:
- `provider`: Provider 名称（如 "Ollama"）
- `searched_paths`: 已搜索的路径列表
- `platform`: 平台名称（auto-detect 如果 None）

**特性**:
- ✅ 平台特定的安装指令（macOS/Linux/Windows）
- ✅ 针对 Ollama、llama.cpp、LM Studio 的定制化建议
- ✅ 显示所有已搜索的路径
- ✅ 提供手动配置路径的指引

**示例输出**:
```
Ollama 未安装或路径未配置。

解决方案：
1. 安装 Ollama：
   • brew install ollama
   • 或访问 https://ollama.ai 下载

2. 或手动指定路径：点击 [配置路径] 按钮

搜索路径：
   • /usr/local/bin/ollama
   • /opt/homebrew/bin/ollama
   • PATH environment variable
```

#### 2.2 build_permission_denied_error_detailed()

**功能**: 为权限不足场景构建详细错误

**参数**:
- `exe_path`: 被拒绝的可执行文件路径
- `platform`: 平台名称（auto-detect 如果 None）

**特性**:
- ✅ Unix 系统：提供 `chmod +x` 命令
- ✅ Windows 系统：提供管理员权限运行指引
- ✅ 显示具体文件路径
- ✅ 包含检查文件所有者的提示

**示例输出 (Unix)**:
```
无法执行 /usr/local/bin/ollama（权限不足）

解决方案：
• 添加可执行权限：chmod +x /usr/local/bin/ollama
• 或使用 sudo 运行 AgentOS（不推荐）
• 检查文件所有者：ls -l /usr/local/bin/ollama
```

**示例输出 (Windows)**:
```
无法执行 C:\Program Files\Ollama\ollama.exe（权限不足）

解决方案：
• 以管理员权限运行 AgentOS
  - 右键点击应用图标
  - 选择 "以管理员身份运行"
• 或检查文件属性中的"安全"选项卡
• 确保当前用户有执行权限
```

#### 2.3 build_port_in_use_error_detailed()

**功能**: 为端口被占用场景构建详细错误

**参数**:
- `port`: 被占用的端口号
- `provider`: Provider 名称
- `platform`: 平台名称（auto-detect 如果 None）

**特性**:
- ✅ Unix 系统：提供 `lsof` 命令示例
- ✅ Windows 系统：提供 `netstat` 和 `taskkill` 命令
- ✅ 包含查看和终止进程的完整步骤
- ✅ 提供修改端口的备选方案

**示例输出 (Linux)**:
```
端口 11434 已被占用（可能是另一个 Ollama 实例）

解决方案：
1. 停止占用该端口的进程：
   • 查看占用进程：lsof -i:11434
   • 终止进程：lsof -ti:11434 | xargs kill
   • 或强制终止：lsof -ti:11434 | xargs kill -9

2. 或修改此实例的端口号（在实例配置中更改）
```

**示例输出 (Windows)**:
```
端口 1234 已被占用（可能是另一个 LM Studio 实例）

解决方案：
1. 停止占用该端口的进程：
   • 查看占用进程：netstat -ano | findstr :1234
   • 找到 PID 后终止：taskkill /PID <pid> /F
   • 示例：taskkill /PID 12345 /F

2. 或修改此实例的端口号（在实例配置中更改）
```

#### 2.4 build_start_failed_error()

**功能**: 为进程启动失败场景构建详细错误

**参数**:
- `provider`: Provider 名称
- `exit_code`: 进程退出码（None 如果未启动）
- `stderr`: 标准错误输出
- `log_file`: 完整日志文件路径（可选）
- `instance_key`: 实例标识符（可选）

**特性**:
- ✅ 显示最后 30 行 stderr 输出
- ✅ 自动截断过长输出（> 2000 字符）
- ✅ 包含日志文件路径引导
- ✅ 针对不同 provider 的特定故障排查步骤
  - Ollama: 模型完整性验证、重新拉取
  - llama.cpp: GGUF 格式检查、资源检查
  - LM Studio: 手动应用内检查

**示例输出**:
```
Ollama 启动失败（退出码：1）

最后 30 行错误日志：
[2026-01-29 10:30:00] Starting Ollama server...
[2026-01-29 10:30:01] Error: failed to load model 'llama2'
[2026-01-29 10:30:01] Model file not found: /models/llama2.gguf
[2026-01-29 10:30:02] Exit with code 1

解决方案：
1. 检查完整日志文件：~/.agentos/logs/ollama.log
2. 验证模型文件完整性：ollama list
3. 尝试重新拉取模型：ollama pull <model-name>
4. 查看官方文档：https://ollama.ai/docs
5. 提交 Issue：https://github.com/ollama/ollama/issues
```

#### 2.5 build_unsupported_action_error()

**功能**: 为不支持的操作构建详细错误

**参数**:
- `provider`: Provider 名称
- `action`: 不支持的操作（如 "stop", "restart"）

**特性**:
- ✅ 针对 LM Studio 的特殊处理
- ✅ 详细说明为什么不支持
- ✅ 提供替代方案
- ✅ 建议使用其他 provider

**示例输出 (LM Studio)**:
```
LM Studio 不支持通过 CLI stop。

说明：
LM Studio 是独立的 GUI 应用，需要在应用内手动管理。

操作方法：
1. 打开 LM Studio 应用（点击 [Open App] 按钮）
2. 在应用内点击 "Stop Server" 停止服务
3. 关闭应用窗口以完全退出

提示：
• 如果需要命令行控制，建议使用 Ollama 或 llama.cpp
• LM Studio 主要设计用于图形界面交互
• 可以通过 API 检测 LM Studio 服务是否运行
```

### 3. API 端点更新

**文件**: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/providers_lifecycle.py`

#### 3.1 start_provider_instance 端点

更新了错误处理逻辑，使用新的详细错误构建函数：

```python
# 可执行文件未找到
if "not found" in message.lower() or "no such file" in message.lower():
    from agentos.providers import platform_utils
    exe_name = bin_name
    searched_paths = [str(p) for p in platform_utils.get_standard_paths(exe_name)]
    error_info = providers_errors.build_exe_not_found_error(
        provider=provider_id.capitalize(),
        searched_paths=searched_paths
    )
    providers_errors.raise_provider_error(**error_info)

# 权限被拒绝
elif "permission denied" in message.lower():
    error_info = providers_errors.build_permission_denied_error_detailed(
        exe_path=bin_name
    )
    providers_errors.raise_provider_error(**error_info)

# 端口被占用
elif "port" in message.lower() and ("in use" in message.lower() or "already" in message.lower()):
    import re
    port_match = re.search(r':(\d+)', instance_config.base_url)
    port = int(port_match.group(1)) if port_match else None
    if port:
        error_info = providers_errors.build_port_in_use_error_detailed(
            port=port,
            provider=provider_id.capitalize()
        )
        providers_errors.raise_provider_error(**error_info)

# 通用启动失败（包含 stderr 和日志）
proc_info = process_mgr.get_process_info(instance_key)
stderr_output = ""
if proc_info and proc_info.stderr_buffer:
    stderr_output = '\n'.join(list(proc_info.stderr_buffer))

log_file = str(process_mgr.log_dir / f"{instance_key.replace(':', '__')}.log")

error_info = providers_errors.build_start_failed_error(
    provider=provider_id.capitalize(),
    exit_code=proc_info.returncode if proc_info else None,
    stderr=stderr_output or message,
    log_file=log_file,
    instance_key=instance_key
)
providers_errors.raise_provider_error(**error_info)
```

#### 3.2 stop_provider_instance 端点

添加了 LM Studio 不支持检查：

```python
# Check if this is LM Studio - it doesn't support CLI stop/restart
if provider_id.lower() == 'lmstudio':
    error_info = providers_errors.build_unsupported_action_error(
        provider="LM Studio",
        action="stop"
    )
    providers_errors.raise_provider_error(**error_info)
```

更新了权限错误处理：

```python
if "permission denied" in message.lower():
    error_info = providers_errors.build_permission_denied_error_detailed(
        exe_path=f"进程 {instance_key}"
    )
    providers_errors.raise_provider_error(**error_info)
```

## 测试验证

### 测试文件

创建了两个测试文件：

1. **test_error_builders_simple.py** - 独立测试脚本
   - 无需依赖项
   - 测试所有 5 个错误场景
   - 验证消息格式和内容

2. **test_error_builders.py** - 完整集成测试
   - 导入实际模块
   - 测试函数调用
   - 验证返回值结构

### 测试结果

```bash
$ python3 test_error_builders_simple.py

✓ All tests completed successfully!

Verification Summary:
- [✓] EXE_NOT_FOUND: Platform-specific installation instructions
- [✓] PERMISSION_DENIED: Unix/Windows-specific permission fixes
- [✓] PORT_IN_USE: Linux/Windows-specific port conflict resolution
- [✓] START_FAILED: Last 30 lines of stderr + provider-specific hints
- [✓] UNSUPPORTED_ACTION: Clear guidance for LM Studio limitations

Task #20 Implementation Complete!
```

### 语法验证

```bash
$ python3 -m py_compile agentos/webui/api/providers_errors.py
✓ providers_errors.py syntax is valid

$ python3 -m py_compile agentos/webui/api/providers_lifecycle.py
✓ providers_lifecycle.py syntax is valid
```

## 验收标准完成情况

- [✅] 5 个核心错误码都有详细提示函数
- [✅] 提示包含平台特定的命令示例（Windows/macOS/Linux）
- [✅] 错误消息易于理解（中文 + 技术细节）
- [✅] EXE_NOT_FOUND 提示包含搜索路径列表
- [✅] START_FAILED 提示包含日志文件路径和最后 30 行输出
- [✅] UNSUPPORTED_ACTION 对 LM Studio 有清晰说明

## 文件修改清单

### 修改文件

1. `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/providers_errors.py`
   - 新增 `UNSUPPORTED_ACTION` 错误码常量
   - 新增 5 个详细错误构建函数（约 400 行代码）
   - 保留所有原有功能

2. `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/providers_lifecycle.py`
   - 更新 `start_provider_instance` 错误处理
   - 更新 `stop_provider_instance` 错误处理
   - 新增 LM Studio 不支持操作检查

### 新增文件

1. `/Users/pangge/PycharmProjects/AgentOS/test_error_builders.py`
   - 完整集成测试脚本

2. `/Users/pangge/PycharmProjects/AgentOS/test_error_builders_simple.py`
   - 独立测试脚本（无依赖）

3. `/Users/pangge/PycharmProjects/AgentOS/TASK20_ERROR_CODES_IMPLEMENTATION.md`
   - 本实施报告文档

## 技术亮点

1. **平台感知**: 所有错误提示都根据平台（macOS/Linux/Windows）自动调整
2. **Provider 特定**: 针对不同 provider 提供定制化的故障排查步骤
3. **可操作性**: 每个错误都包含具体可执行的命令和步骤
4. **完整性**: 包含搜索路径、日志文件路径、端口号等技术细节
5. **用户友好**: 使用中文消息，清晰的结构和排版

## 下一步建议

1. **前端展示**: 在 WebUI 中以友好的方式展示这些详细错误信息
2. **文档链接**: 确保所有链接指向最新的官方文档
3. **本地化**: 考虑支持英文等其他语言
4. **日志聚合**: 将错误信息同步记录到系统日志中
5. **用户反馈**: 收集用户对错误提示的反馈，持续优化

## 总结

Task #20 已成功完成所有验收标准。实施了 5 个核心错误场景的详细错误构建函数，提供平台特定的可操作解决方案。错误消息清晰、友好、易于理解，大大提升了用户体验和问题排查效率。

---

**实施者**: Claude Sonnet 4.5
**完成时间**: 2026-01-29
**任务状态**: ✅ Completed
