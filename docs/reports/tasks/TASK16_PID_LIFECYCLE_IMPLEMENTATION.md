# Task #16: P0.3 - 进程管理 PID 持久化与生命周期改进 - Implementation Report

**Date**: 2026-01-29
**Task**: P0.3 from PROVIDERS_FIX_CHECKLIST_V2.md (Task 3)
**Status**: ✅ Completed

---

## 概述 (Overview)

实施了进程管理的 PID 持久化增强和跨平台生命周期管理改进，使 Stop/Restart 操作在 Windows/macOS/Linux 上可靠工作。

---

## 实施内容 (Implementation Details)

### 1. PID 持久化增强 (PID Persistence Enhancement)

#### 文件: `agentos/providers/process_manager.py`

**新增功能**:

1. **增强 PID 文件格式** - 添加了 ISO 格式时间戳用于验证
   ```python
   def _write_pidfile(self, instance_key: str, proc_info: ProcessInfo, base_url: str):
       """
       Write pidfile with timestamp for validation.

       PID file format includes:
       - pid: Process ID
       - timestamp: ISO format timestamp for verification
       - command: Command line that was used to start the process
       - started_at: Unix timestamp of process start
       - base_url: Service endpoint URL
       - instance_key: Unique identifier for this instance
       """
   ```

2. **新增公共 API 方法**:
   - `save_pid(provider, instance, pid)` - 保存 PID 到文件，包含时间戳
   - `load_pid(provider, instance) -> Optional[dict]` - 加载 PID，返回 {"pid": int, "timestamp": str, "started_at": float} 或 None
   - `verify_pid(pid_info: dict) -> bool` - 验证 PID 文件中的进程是否还在运行

**示例用法**:
```python
# 保存 PID
pm = ProcessManager.get_instance()
pm.save_pid("ollama", "default", 12345)

# 加载和验证 PID
pid_info = pm.load_pid("ollama", "default")
if pid_info and pm.verify_pid(pid_info):
    print(f"Process {pid_info['pid']} is still running")
```

---

### 2. 停止逻辑改进 (Enhanced Stop Logic)

#### 文件: `agentos/providers/process_manager.py`

**改进的 `stop_process_cross_platform()` 函数**:

```python
def stop_process_cross_platform(
    pid: int,
    timeout: float = 5.0,
    force: bool = False
) -> dict:
    """
    Stop a process with cross-platform compatibility and detailed result.

    Implementation:
    - Windows: taskkill /PID <pid> /T → wait 5s → taskkill /PID <pid> /T /F
    - macOS/Linux: SIGTERM → wait 5s → SIGKILL
    - Verifies process is stopped using psutil.pid_exists()

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "old_pid": int,
            "stopped": bool  # True if process was verified stopped
        }
    """
```

**关键特性**:
- ✅ 优先按 PID 停止（不是进程名）
- ✅ Windows: 使用 taskkill /PID <pid> /T，5s 后使用 /F 强制终止
- ✅ macOS/Linux: 先 SIGTERM，5s 后 SIGKILL
- ✅ 使用 `psutil.pid_exists()` 验证进程已停止
- ✅ 返回详细信息：success, message, old_pid, stopped 状态

**ProcessManager.stop_process() 增强**:
- 返回值从 `tuple[bool, str]` 改为 `tuple[bool, str, Optional[int]]`
- 返回 old_pid 用于跟踪和日志记录

---

### 3. 重启逻辑实现 (Restart Logic Implementation)

#### 文件: `agentos/webui/api/providers_lifecycle.py`

**新增 REST API 端点**:

```python
@router.post("/{provider_id}/instances/restart", response_model=RestartInstanceResponse)
async def restart_provider_instance(
    provider_id: str,
    request: RestartInstanceRequest,
    timeout: float = 45.0,
):
    """
    Restart a provider instance.

    Restart sequence:
    1. Stop the instance (if running)
    2. Wait for port to be released (max 5s)
    3. Check for and clean up any process remnants
    4. Start the instance
    5. Return old and new PIDs
    """
```

**请求模型**:
```python
class RestartInstanceRequest(BaseModel):
    instance_id: str
    force: bool = False
    launch_config: Optional[Dict[str, Any]] = None
```

**响应模型**:
```python
class RestartInstanceResponse(BaseModel):
    ok: bool
    instance_key: str
    message: str
    old_pid: Optional[int] = None
    new_pid: Optional[int] = None
```

**重启流程**:
1. ✅ 停止实例（如果正在运行），记录 old_pid
2. ✅ 等待端口释放（最多 5 秒，10 次尝试 × 0.5s）
3. ✅ 检查旧进程残留，如有必要强制终止
4. ✅ 启动实例，获取 new_pid
5. ✅ 返回详细信息（old_pid, new_pid）

---

### 4. 手动启动应用的 Provider 特殊处理 (Manual Lifecycle Providers)

#### 文件: `agentos/providers/providers_config.py`

**扩展 ProviderConfig 数据类**:

```python
@dataclass
class ProviderConfig:
    provider_id: str
    enabled: bool = True
    instances: List[ProviderInstance] = field(default_factory=list)
    manual_lifecycle: bool = False  # If True, provider requires manual app management
    supported_actions: List[str] = field(default_factory=lambda: ['start', 'stop', 'restart', 'detect'])
```

**LM Studio 配置示例**:
```python
"lmstudio": {
    "enabled": True,
    "executable_path": None,
    "auto_detect": True,
    "manual_lifecycle": True,  # Requires manual app management
    "supported_actions": ["open_app", "detect"],  # No CLI start/stop/restart
    "instances": [...]
}
```

#### 文件: `agentos/webui/api/providers_lifecycle.py`

**新增 Provider Capabilities API**:

```python
@router.get("/{provider_id}/capabilities", response_model=ProviderCapabilitiesResponse)
async def get_provider_capabilities(provider_id: str):
    """
    Get provider capabilities and supported actions.

    Returns:
        - manual_lifecycle: Whether provider requires manual app management
        - supported_actions: List of supported actions
        - enabled: Whether provider is enabled
    """
```

**Stop/Restart 端点检查**:
- LM Studio 的 stop/restart 请求返回 `UNSUPPORTED_ACTION` 错误
- 使用 `build_unsupported_action_error()` 构建详细错误信息，包含操作指南

---

### 5. UI 动作支持矩阵显示 (UI Actions Support Matrix)

#### 文件: `agentos/webui/static/js/views/ProvidersView.js`

**新增 `loadProviderCapabilities()` 方法**:

```javascript
async loadProviderCapabilities(providerId) {
    const response = await this.apiClient.get(`/api/providers/${providerId}/capabilities`);

    // Display supported actions matrix
    const allActions = ['start', 'stop', 'restart', 'open_app', 'detect'];

    const actionsHTML = allActions.map(action => {
        const supported = response.supported_actions.includes(action);
        const statusIcon = supported ? '✅' : '❌';

        return `
            <span class="action-badge ${supported ? 'supported' : 'unsupported'}">
                <span class="material-icons">${icon}</span>
                ${label} ${statusIcon}
            </span>
        `;
    }).join('');
}
```

**更新 `restartInstance()` 方法**:
- 使用新的 `/api/providers/{provider_id}/instances/restart` 端点
- 显示 old_pid 和 new_pid 在 Toast 通知中
- 添加 `restarting` CSS 类禁用操作期间的交互

**显示效果示例**:
```
Ollama: ✅ Start | ✅ Stop | ✅ Restart | ❌ Open App | ✅ Detect
LM Studio: ❌ Start | ❌ Stop | ❌ Stop | ✅ Open App | ✅ Detect
⚠️ This provider requires manual app management
```

#### 文件: `agentos/webui/static/css/components.css`

**新增 CSS 样式**:
```css
/* Supported Actions Display */
.supported-actions-display { ... }
.actions-matrix { ... }
.action-badge { ... }
.action-badge.supported { background: #d4edda; color: #155724; }
.action-badge.unsupported { background: #f8d7da; color: #721c24; opacity: 0.7; }
.manual-lifecycle-note { background: #fff3cd; color: #856404; }
tr.restarting { opacity: 0.6; pointer-events: none; }
```

---

## 验收标准检查 (Acceptance Criteria Verification)

### ✅ PID 持久化

- [x] PID 文件在启动时创建，包含 pid + timestamp
- [x] PID 文件在停止时删除
- [x] 启动时恢复 PID 并验证进程仍在运行
- [x] 存储位置：`~/.agentos/run/<provider>_<instance>.pid`

### ✅ 停止逻辑改进

- [x] 优先按 PID 停止（不是进程名）
- [x] Windows: `taskkill /PID <pid> /T` → 等待 5s → `taskkill /PID <pid> /T /F`
- [x] macOS/Linux: `SIGTERM` → 等待 5s → `SIGKILL`
- [x] 验证进程已停止（`psutil.pid_exists()`）
- [x] 返回值：`{"success": bool, "message": str, "old_pid": int, "stopped": bool}`

### ✅ 重启逻辑

- [x] Restart 操作先 Stop 再 Start
- [x] 检查端口释放（最多 5s）
- [x] 检查旧进程残留（清理）
- [x] 返回详细信息（old_pid, new_pid）

### ✅ 手动启动应用的 Provider

- [x] LM Studio 标记为 `manual_lifecycle: true`
- [x] `supported_actions: ["open_app", "detect"]`
- [x] Stop/Restart 返回 `UNSUPPORTED_ACTION` 错误

### ✅ UI 动作支持矩阵

- [x] 每个 provider 显示支持的动作
- [x] ✅/❌ 图标显示支持状态
- [x] LM Studio 显示 manual lifecycle 警告

---

## API 变更总结 (API Changes Summary)

### 新增端点 (New Endpoints)

1. **POST `/api/providers/{provider_id}/instances/restart`**
   - 请求: `RestartInstanceRequest`
   - 响应: `RestartInstanceResponse` (包含 old_pid, new_pid)

2. **GET `/api/providers/{provider_id}/capabilities`**
   - 响应: `ProviderCapabilitiesResponse` (manual_lifecycle, supported_actions, enabled)

### 修改端点 (Modified Endpoints)

1. **POST `/api/providers/{provider_id}/instances/stop`**
   - 响应中新增: `old_pid: Optional[int]`

---

## 文件修改清单 (Modified Files)

1. ✅ `agentos/providers/process_manager.py`
   - 增强 PID 文件格式（添加 timestamp）
   - 新增 `save_pid()`, `load_pid()`, `verify_pid()` 方法
   - 改进 `stop_process_cross_platform()` 返回详细结果
   - `stop_process()` 返回 old_pid

2. ✅ `agentos/webui/api/providers_lifecycle.py`
   - 新增 `restart_provider_instance()` 端点
   - 新增 `get_provider_capabilities()` 端点
   - 更新 `stop_provider_instance()` 返回 old_pid
   - 添加请求/响应模型

3. ✅ `agentos/providers/providers_config.py`
   - 扩展 `ProviderConfig` 数据类（manual_lifecycle, supported_actions）
   - 更新 LM Studio 默认配置
   - 修改 `get_provider_config()` 方法解析新字段

4. ✅ `agentos/webui/static/js/views/ProvidersView.js`
   - 新增 `loadProviderCapabilities()` 方法
   - 更新 `restartInstance()` 使用新端点
   - 更新 `initExecutableConfigs()` 加载 capabilities

5. ✅ `agentos/webui/static/css/components.css`
   - 新增 supported actions display 样式
   - 新增 restarting 状态样式

---

## 测试建议 (Testing Recommendations)

### 单元测试

1. **PID 管理测试**:
   ```python
   def test_save_and_load_pid():
       pm = ProcessManager()
       pm.save_pid("ollama", "default", 12345)
       pid_info = pm.load_pid("ollama", "default")
       assert pid_info["pid"] == 12345
       assert "timestamp" in pid_info
   ```

2. **停止逻辑测试**:
   ```python
   def test_stop_process_returns_details():
       result = stop_process_cross_platform(12345)
       assert "success" in result
       assert "old_pid" in result
       assert "stopped" in result
   ```

### 集成测试

1. **Restart 端点测试**:
   ```bash
   curl -X POST http://localhost:8000/api/providers/ollama/instances/restart \
     -H "Content-Type: application/json" \
     -d '{"instance_id": "default", "force": false}'
   ```

2. **Capabilities 端点测试**:
   ```bash
   curl http://localhost:8000/api/providers/lmstudio/capabilities
   # 预期: {"manual_lifecycle": true, "supported_actions": ["open_app", "detect"]}
   ```

### 手动测试清单

- [ ] Windows: Restart Ollama 实例，验证 old_pid/new_pid
- [ ] macOS: Restart llama.cpp 实例，验证端口释放
- [ ] Linux: 测试 force restart
- [ ] LM Studio: 验证 stop/restart 返回 UNSUPPORTED_ACTION
- [ ] UI: 验证 supported actions 正确显示
- [ ] UI: 验证 restart 按钮显示 old/new PID

---

## 已知限制和未来改进 (Known Limitations & Future Improvements)

### 已知限制

1. **端口释放检测**: 当前固定等待 5 秒，可能需要根据 provider 调整
2. **进程清理**: 对于某些僵尸进程可能需要额外清理逻辑
3. **Windows 服务**: 以服务形式运行的 provider 可能需要特殊处理

### 未来改进

1. **健康检查集成**: Restart 后自动进行健康检查（Task #17）
2. **批量重启**: 支持一次重启多个实例
3. **重启历史**: 记录重启历史和 PID 变化
4. **进程组管理**: 支持管理进程树（parent-child relationships）

---

## 依赖关系 (Dependencies)

### 前置任务
- ✅ Task #14 (P0.1): API 日志增强 - 用于记录 restart 操作
- ✅ Task #15 (P0.2): 可执行文件定位 - 用于 restart 时定位可执行文件

### 后置任务
- ⏳ Task #17 (P0.4): Providers 状态检测与健康检查
- ⏳ Task #21 (P1.8): 前端交互完善

---

## 总结 (Conclusion)

Task #16 (P0.3) 已成功实施，实现了以下核心功能：

1. ✅ PID 持久化增强（带时间戳验证）
2. ✅ 跨平台停止逻辑改进（Windows/macOS/Linux）
3. ✅ 完整的 Restart 端点实现
4. ✅ 手动生命周期 Provider 支持（LM Studio）
5. ✅ UI 动作支持矩阵显示

所有验收标准已满足，代码已准备好进行测试和集成。

---

**Implementation By**: Claude Sonnet 4.5
**Review Required**: Yes
**Ready for Testing**: Yes
