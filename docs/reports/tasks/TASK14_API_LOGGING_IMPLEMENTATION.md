# Task #14: API调用链路诊断与日志增强 - Implementation Report

## 实施日期
2026-01-29

## 任务目标
实施 PROVIDERS_FIX_CHECKLIST_V2.md 的 Task 1 (P0.1)，增强 API 日志和统一返回格式，让前后端交互可追踪、可验证。

## 实施内容

### 1. 结构化日志系统 (providers/logging_utils.py)

#### 1.1 核心组件
- **ProviderStructuredLogger**: 结构化日志记录器
  - 自动记录 timestamp (ISO 8601 格式，UTC 时区)
  - provider (ollama, llamacpp, lmstudio)
  - action (start, stop, restart, detect, validate)
  - platform (自动检测: windows, macos, linux)
  - resolved_exe (实际使用的可执行文件路径)
  - pid (进程 ID)
  - exit_code (退出码)
  - elapsed_ms (操作耗时，毫秒)
  - error_code (错误码)
  - message (附加消息)

- **OperationTimer**: 上下文管理器，用于自动计时操作
  ```python
  with OperationTimer() as timer:
      # 执行操作
      pass
  elapsed_ms = timer.elapsed_ms()
  ```

#### 1.2 日志文件配置
- 路径: `~/.agentos/logs/providers.log`
- 格式: `时间戳 - 日志名称 - 级别 - 结构化消息`
- 编码: UTF-8
- 自动创建目录
- 支持追加写入

#### 1.3 便捷日志方法
- `log_start()`: 记录启动操作
- `log_start_success()`: 记录启动成功
- `log_start_failure()`: 记录启动失败
- `log_stop()`: 记录停止操作
- `log_stop_success()`: 记录停止成功
- `log_stop_failure()`: 记录停止失败
- `log_restart()`: 记录重启操作
- `log_restart_success()`: 记录重启成功
- `log_restart_failure()`: 记录重启失败
- `log_detect()`: 记录可执行文件检测
- `log_validate()`: 记录可执行文件验证

### 2. API 端点日志增强

#### 2.1 providers_lifecycle.py 修改

**start_provider_instance** 端点:
- ✅ 添加 OperationTimer 计时
- ✅ 记录操作开始 (log_start)
- ✅ 记录成功启动 (log_start_success)，包含 PID 和耗时
- ✅ 记录超时失败 (log_start_failure)，包含超时时间
- ✅ 记录启动失败 (log_start_failure)，包含错误详情
- ✅ 已有 30s 超时控制 (asyncio.wait_for)

**stop_provider_instance** 端点:
- ✅ 添加 OperationTimer 计时
- ✅ 记录操作开始 (log_stop)
- ✅ 记录成功停止 (log_stop_success)，包含 PID 和耗时
- ✅ 记录超时失败 (log_stop_failure)，包含超时时间
- ✅ 记录停止失败 (log_stop_failure)，包含错误详情
- ✅ 已有 10s 超时控制 (asyncio.wait_for)

**detect_executable** 端点:
- ✅ 记录检测结果 (log_detect)
- ✅ 包含搜索路径和检测结果

**validate_executable** 端点:
- ✅ 记录验证成功 (log_validate)
- ✅ 记录验证失败 (log_validate)，包含错误消息

#### 2.2 ollama_controller.py 修改

**start()** 方法:
- ✅ 添加 OperationTimer 计时
- ✅ 记录启动操作开始
- ✅ 记录已运行情况 (幂等性)
- ✅ 记录可执行文件未找到
- ✅ 记录启动成功，包含 PID、resolved_exe、耗时
- ✅ 记录启动超时 (DEGRADED 状态)

**stop()** 方法:
- ✅ 添加 OperationTimer 计时
- ✅ 记录停止操作开始
- ✅ 记录已停止情况 (幂等性)
- ✅ 记录 PID 未追踪错误
- ✅ 记录停止成功，包含 PID 和耗时
- ✅ 记录停止失败

### 3. 统一返回格式

#### 3.1 现有返回格式 (已符合要求)

所有 Providers API 端点已经使用统一的错误处理框架 (providers_errors.py):

**成功响应** (各端点已有专门的响应模型):
```python
StartInstanceResponse(
    ok=True,
    instance_key="ollama:default",
    pid=12345,
    message="Success message"
)
```

**错误响应** (通过 providers_errors.raise_provider_error):
```json
{
  "error": {
    "code": "EXECUTABLE_NOT_FOUND",
    "message": "Ollama executable not found...",
    "details": {
      "provider_id": "ollama",
      "searched_paths": [...]
    },
    "suggestion": "Install Ollama or configure the path"
  }
}
```

#### 3.2 错误码 (providers_errors.py 已定义)
- EXECUTABLE_NOT_FOUND
- PROCESS_START_FAILED
- PROCESS_STOP_FAILED
- PROCESS_NOT_RUNNING
- PROCESS_ALREADY_RUNNING
- STARTUP_TIMEOUT
- SHUTDOWN_TIMEOUT
- PORT_IN_USE
- PERMISSION_DENIED
- CONFIG_ERROR
- INTERNAL_ERROR
- 等 30+ 错误码

### 4. 超时控制

#### 4.1 启动操作超时
- `start_provider_instance`: 默认 30s (可通过 timeout 参数配置)
- `install_provider`: 默认 300s (5 分钟，brew 安装)
- 使用 `asyncio.wait_for()` 实现
- 超时后抛出 HTTPException 并记录日志

#### 4.2 停止操作超时
- `stop_provider_instance`: 默认 10s (可通过 timeout 参数配置)
- 使用 `asyncio.wait_for()` 实现
- 超时后建议使用 force=true 强制停止

### 5. 日志示例

#### 5.1 启动成功日志
```
2026-01-29 20:56:12 - agentos.providers - INFO - timestamp=2026-01-29T09:56:12.579039+00:00 provider=ollama action=start platform=macos resolved_exe=/usr/local/bin/ollama pid=12345 elapsed_ms=1234.56 message="Successfully started ollama" instance_key=ollama:default
```

#### 5.2 停止失败日志
```
2026-01-29 20:56:15 - agentos.providers - ERROR - timestamp=2026-01-29T09:56:15.123456+00:00 provider=ollama action=stop platform=macos pid=12345 error_code=SHUTDOWN_TIMEOUT elapsed_ms=10005.23 message="Shutdown timeout for ollama:default" instance_key=ollama:default timeout_seconds=10 force=false
```

#### 5.3 检测日志
```
2026-01-29 20:56:12 - agentos.providers - INFO - timestamp=2026-01-29T09:56:12.579606+00:00 provider=llamacpp action=detect platform=macos resolved_exe=/usr/local/bin/llama-server message="Detecting llamacpp executable" searched_paths=['/usr/local/bin', '/opt/homebrew/bin']
```

## 验收标准完成情况

### ✅ 必需功能
- [x] 所有 provider 操作都有结构化日志 (provider, action, elapsed_ms)
- [x] 统一返回格式 (ok/error, error_code, message, details)
- [x] 启动/停止操作有 30s/10s 超时
- [x] 日志文件可查看: `~/.agentos/logs/providers.log`
- [x] 日志级别可配置 (通过 Python logging 配置)

### ✅ 日志字段
- [x] timestamp (ISO 8601, UTC)
- [x] provider (ollama/llamacpp/lmstudio)
- [x] action (start/stop/restart/detect/validate)
- [x] platform (自动检测)
- [x] resolved_exe (如适用)
- [x] pid (如适用)
- [x] exit_code (如适用)
- [x] elapsed_ms (毫秒)
- [x] error_code (如失败)

## 技术细节

### 依赖模块
- `agentos.providers.platform_utils`: 平台检测和路径管理
- `agentos.providers.providers_config`: Provider 配置管理
- `agentos.providers.process_manager`: 进程管理
- `agentos.webui.api.providers_errors`: 统一错误处理

### 关键设计决策

1. **使用上下文管理器计时**: `OperationTimer` 确保即使发生异常也能获取耗时
2. **结构化日志格式**: 使用 key=value 格式便于日志解析和搜索
3. **自动平台检测**: 使用 `platform_utils.get_platform()` 自动填充平台信息
4. **全局单例**: `get_provider_logger()` 返回全局日志实例，避免重复初始化
5. **UTF-8 编码**: 日志文件使用 UTF-8 编码支持多语言
6. **追加模式**: 日志文件使用追加模式，保留历史记录

## 文件修改列表

### 新增文件
- `agentos/providers/logging_utils.py` (540 行)

### 修改文件
- `agentos/webui/api/providers_lifecycle.py` (添加日志调用)
- `agentos/providers/ollama_controller.py` (添加日志调用)

## 测试验证

### 基础功能测试
```bash
# 测试日志系统
python3 -c "
from agentos.providers.logging_utils import get_provider_logger
logger = get_provider_logger()
logger.log_start('ollama', resolved_exe='/usr/local/bin/ollama')
logger.log_start_success('ollama', pid=12345, elapsed_ms=1234.56)
"

# 检查日志文件
cat ~/.agentos/logs/providers.log
```

### 语法检查
```bash
python3 -m py_compile agentos/providers/logging_utils.py
python3 -m py_compile agentos/webui/api/providers_lifecycle.py
python3 -m py_compile agentos/providers/ollama_controller.py
```

## 后续建议

### P1 优先级
1. **日志轮转**: 实现日志文件大小限制和自动轮转
2. **日志查询 API**: 提供 API 端点查询最近的日志条目
3. **前端日志展示**: 在 Providers 页面展示最近的操作日志

### P2 优先级
1. **日志聚合**: 集成到统一的系统日志查询界面
2. **日志导出**: 支持导出日志用于故障排查
3. **指标统计**: 基于日志统计操作成功率、平均耗时等指标

## 相关文档
- PROVIDERS_FIX_CHECKLIST_V2.md (Task 1)
- agentos/webui/api/providers_errors.py (错误处理框架)
- agentos/providers/platform_utils.py (平台工具)

## 状态
✅ **已完成** - 所有验收标准已满足

---
**实施人员**: Claude Sonnet 4.5
**审核状态**: 待审核
