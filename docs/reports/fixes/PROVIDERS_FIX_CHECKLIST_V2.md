# Providers 跨平台修复清单 V2 - 以可落地为目标

## 项目背景

**当前状态**：Phase 1-7 已完成基础跨平台支持，但实战中发现以下问题：
- 前后端交互失败（启动/停止/重启不响应）
- 可执行文件定位不够健壮
- 进程管理 PID 跟踪不稳定
- LM Studio 等特殊 provider 处理不当
- Models 路径安全性不足

**本次目标**：修复实战中的核心问题，让 Providers 页面真正可用。

---

## 与 V1 的关系

### 已完成（V1 Phase 1-7）
- ✅ platform_utils.py 基础框架
- ✅ process_manager.py 跨平台进程管理
- ✅ 可执行文件检测 API（基础版）
- ✅ Models 目录管理 API（基础版）
- ✅ 统一错误处理（27 个错误码）
- ✅ 前端配置 UI（基础版）

### 本次改进重点（V2）
- 🔧 API 调用链路诊断和日志
- 🔧 可执行文件定位机制加强
- 🔧 PID 持久化和进程生命周期
- 🔧 状态检测和健康检查
- 🔧 路径安全加固
- 🆕 Providers 自检面板

---

## P0 必须修复任务

### Task 1: API 调用链路诊断与日志增强
**优先级**: P0
**目标**: 让每个前后端交互都可追踪、可验证

**验收标准**:
1. ✅ 后端每个 provider 操作都有结构化日志：
   ```json
   {
     "timestamp": "2026-01-29T10:30:00Z",
     "provider": "ollama",
     "action": "start",
     "platform": "macos",
     "resolved_exe": "/usr/local/bin/ollama",
     "pid": 12345,
     "exit_code": 0,
     "elapsed_ms": 1234,
     "error_code": null
   }
   ```
2. ✅ 统一返回协议（所有 Providers API）：
   ```json
   {
     "ok": true/false,
     "error_code": "EXE_NOT_FOUND" | null,
     "message": "Success or error message",
     "details": {
       "pid": 12345,
       "resolved_exe": "/path/to/exe",
       ...
     }
   }
   ```
3. ✅ 所有启动/停止类操作有超时控制（默认 30s，可配置）
4. ✅ 前端 DevTools Network 可见所有请求和响应
5. ✅ 日志级别可配置（DEBUG/INFO/WARNING/ERROR）

---

### Task 2: 可执行文件定位机制加强
**优先级**: P0
**目标**: 三平台可靠找到可执行文件 + 手动指定

**验收标准**:
1. ✅ PATH 探测实现：
   - Windows: `where <cmd>` 或纯 Python 扫描 PATH + .exe/.cmd/.bat
   - macOS/Linux: `which <cmd>` 或纯 Python 扫描 PATH
2. ✅ 标准安装路径探测（多候选，按优先级）：
   - **Ollama**:
     - macOS: `/Applications/Ollama.app/...`, `$(brew --prefix)/bin/ollama`
     - Linux: `/usr/local/bin/ollama`, `/usr/bin/ollama`
     - Windows: `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`, `%PROGRAMFILES%\Ollama\ollama.exe`
   - **llama.cpp** (llama-server):
     - 项目本地 bin、用户指定目录、`/usr/local/bin/llama-server`
   - **LM Studio**:
     - macOS: `/Applications/LM Studio.app`
     - Windows: `%LOCALAPPDATA%\Programs\LM Studio\LM Studio.exe`
     - Linux: AppImage 常见下载目录
3. ✅ 优先级顺序：用户配置 > 标准路径 > PATH
4. ✅ 可执行验证增强：
   - 存在性检查
   - 可执行权限检查（Unix）
   - 版本探测：执行 `<exe> --version` 并解析输出（5s 超时）
5. ✅ 手动指定路径 UI 完善：
   - 每个 provider 显示 "Resolved Executable" 和 "Custom Path"
   - Browse 按钮 + Validate 按钮（实时验证）
   - 保存到配置文件（持久化）

---

### Task 3: 进程管理 PID 持久化与生命周期改进
**优先级**: P0
**目标**: Stop/Restart 跨平台可靠工作

**验收标准**:
1. ✅ PID 持久化：
   - 启动成功后必须记录 PID
   - 存储位置：`~/.agentos/run/<provider>_<instance>.pid`
   - 进程管理器启动时恢复 PID（验证进程仍在运行）
2. ✅ 停止逻辑改进：
   - 优先：按 PID 停止（不是进程名）
   - Windows: `taskkill /PID <pid> /T` → 等待 5s → `taskkill /PID <pid> /T /F`
   - macOS/Linux: `SIGTERM` → 等待 5s → `SIGKILL`
   - 验证进程已停止（psutil.pid_exists）
3. ✅ 重启逻辑：
   - Stop 成功后 → 检查端口是否释放 → Start
   - Start 前检查端口占用、旧进程残留
   - 返回详细信息（旧 PID、新 PID）
4. ✅ 手动启动应用的 provider（LM Studio）特殊处理：
   - 标记为 `manual_lifecycle: true`
   - Start 动作：打开应用（Windows: `start`, macOS: `open -a`, Linux: 执行）
   - Stop/Restart 动作：提示用户手动操作（或尝试关闭应用进程，如果可识别）
5. ✅ UI 显示动作支持矩阵：
   ```
   Ollama: ✅ Start | ✅ Stop | ✅ Restart | ✅ Detect
   LM Studio: ✅ Open App | ❌ Stop (manual) | ❌ Restart (manual) | ✅ Detect
   ```

---

### Task 4: Providers 状态检测与健康检查
**优先级**: P0
**目标**: 状态显示准确，不会"明明没启动却显示 Running"

**验收标准**:
1. ✅ 健康检查实现（每个 provider）：
   - **有 PID**: `psutil.pid_exists(pid)` + 端口监听检查（可选）+ HTTP health endpoint（可选）
   - **无 PID**: 按端口探测或 API endpoint 探测（需可配置）
2. ✅ 状态定义清晰：
   - `UNKNOWN`: 初始状态，未检测
   - `STOPPED`: 确认未运行
   - `STARTING`: 启动中（过渡状态）
   - `RUNNING`: 确认运行中（PID + 健康检查通过）
   - `ERROR`: 启动失败或异常退出
3. ✅ 前端状态刷新：
   - 手动刷新按钮
   - 自动轮询（可配置间隔，默认 5s，可关闭）
   - 操作后自动刷新（启动/停止后立即刷新）
4. ✅ 状态缓存机制：
   - 后端缓存健康检查结果（TTL 3s）
   - 避免频繁探测导致性能问题
   - 缓存键包含 provider + instance

---

### Task 5: Models 路径安全加固
**优先级**: P0
**目标**: 防止路径穿越攻击，Windows 特殊路径处理

**验收标准**:
1. ✅ 默认 Models 目录映射（可覆盖）：
   - **Ollama**:
     - macOS/Linux: `~/.ollama/models`
     - Windows: `%USERPROFILE%\.ollama\models` 或 `%LOCALAPPDATA%\Ollama\models`（检测两者，优先使用存在的）
   - **llama.cpp**: 默认空，鼓励用户配置
   - **LM Studio**: 建议路径 `~/.cache/lm-studio/models`（macOS/Linux）或 `%LOCALAPPDATA%\lm-studio\models`（Windows）
2. ✅ Windows 路径处理：
   - 反斜杠 `\` 转换为正斜杠 `/`（内部统一使用 pathlib.Path）
   - UNC 路径支持：`\\server\share`
   - 驱动器字母处理：`C:\Users\...`
3. ✅ macOS/Linux 路径处理：
   - `~` 展开为用户主目录
   - 符号链接解析（`os.path.realpath`）
4. ✅ 后端目录浏览安全：
   - **允许列表**：只允许用户配置过的目录作为根（存储在配置文件）
   - **路径规范化**：使用 `Path.resolve()` 获取绝对路径
   - **禁止穿越**：检查最终路径是否在允许列表的目录树内
   - 示例代码：
     ```python
     def is_safe_path(base_dir: Path, user_path: str) -> bool:
         try:
             resolved = (base_dir / user_path).resolve()
             return resolved.is_relative_to(base_dir)
         except:
             return False
     ```
5. ✅ UI 目录选择提示：
   - "此目录将被 WebUI 读取（只读访问）"
   - "请勿选择系统敏感目录"

---

## P1 强烈建议任务

### Task 6: Providers 自检面板
**优先级**: P1
**目标**: 用户一眼看出问题所在

**验收标准**:
1. ✅ 每个 provider 显示诊断信息：
   ```
   ┌─ Ollama Diagnostics ──────────────────────┐
   │ Platform: macOS (Darwin 25.2.0)           │
   │ Detected Executable: /usr/local/bin/ollama│
   │ Configured Executable: (auto)             │
   │ Resolved Executable: /usr/local/bin/ollama│
   │ Version: 0.1.26                           │
   │ Supported Actions: ✅ Start, ✅ Stop,     │
   │                    ✅ Restart, ✅ Detect  │
   │ Current Status: RUNNING                   │
   │ PID: 12345                                │
   │ Port: 11434 (listening)                   │
   │ Models Directory: ~/.ollama/models        │
   │   (5 models found)                        │
   │                                           │
   │ [Copy Diagnostics] [Run Health Check]    │
   └───────────────────────────────────────────┘
   ```
2. ✅ "Copy Diagnostics" 按钮：
   - 复制格式化的诊断信息（Markdown 格式）
   - 包含：平台、版本、路径、状态、错误日志（如有）
3. ✅ "Run Health Check" 按钮：
   - 触发完整健康检查（不使用缓存）
   - 显示检查结果（端口、PID、API 响应等）

---

### Task 7: 错误码与可操作提示改进
**优先级**: P1
**目标**: 每个错误都有明确的解决方案

**验收标准**:
1. ✅ 核心错误码及提示（扩展 V1 的 27 个错误码）：

   **EXE_NOT_FOUND**:
   ```
   错误：可执行文件未找到

   Ollama 未安装或路径未配置。

   解决方案：
   1. 安装 Ollama：
      • macOS: brew install ollama 或访问 https://ollama.ai
      • Windows: 下载安装程序：https://ollama.ai
      • Linux: curl -fsSL https://ollama.ai/install.sh | sh
   2. 或手动指定路径：点击 [配置路径] 按钮

   搜索路径：
   • /usr/local/bin/ollama
   • /opt/homebrew/bin/ollama
   • PATH 环境变量
   ```

   **PERMISSION_DENIED**:
   ```
   错误：权限不足

   无法执行 /usr/local/bin/ollama（权限不足）

   解决方案：
   • macOS/Linux: chmod +x /usr/local/bin/ollama
   • Windows: 以管理员权限运行 AgentOS
   ```

   **PORT_IN_USE**:
   ```
   错误：端口被占用

   端口 11434 已被占用（可能是另一个 Ollama 实例）

   解决方案：
   1. 停止占用该端口的进程：
      • macOS/Linux: lsof -ti:11434 | xargs kill
      • Windows: netstat -ano | findstr :11434 然后 taskkill
   2. 或修改此实例的端口号
   ```

   **START_FAILED**:
   ```
   错误：启动失败

   Ollama 启动失败（退出码：1）

   最后 30 行日志：
   [2026-01-29 10:30:00] Error: failed to load model...
   [2026-01-29 10:30:01] Exit with code 1

   解决方案：
   1. 检查日志文件：~/.agentos/logs/ollama.log
   2. 验证模型文件完整性
   3. 查看 Ollama 官方文档：https://ollama.ai/docs
   ```

   **UNSUPPORTED_ACTION**:
   ```
   提示：操作不支持

   LM Studio 不支持通过 CLI 停止/重启。

   说明：
   LM Studio 是独立的 GUI 应用，需要在应用内手动管理。

   操作方法：
   1. 打开 LM Studio 应用（点击 [Open App]）
   2. 在应用内点击 "Stop Server" 停止服务
   3. 关闭应用窗口以完全退出
   ```

2. ✅ 错误提示包含：
   - 错误标题（简短）
   - 错误描述（详细）
   - 解决方案（分步骤，平台特定）
   - 相关资源链接（官网、文档、Issue）

---

### Task 8: 前端交互完善
**优先级**: P1
**目标**: 操作流畅，状态清晰

**验收标准**:
1. ✅ 按钮状态管理：
   - Loading 状态：显示 spinner + "Starting..." 文本
   - 禁用重复点击：操作进行中时禁用按钮
   - 成功/失败反馈：Toast 通知 + 按钮恢复
2. ✅ 自动刷新状态：
   - 启动/停止/重启操作完成后自动刷新状态（1s 延迟）
   - 配置更改后自动刷新可执行文件检测
3. ✅ 配置保存与验证分离：
   - Validate 按钮：仅验证路径有效性，不保存
   - Save 按钮：保存配置到后端（验证通过后才允许保存）
   - 显示验证状态：✓ 有效 | ✗ 无效 | ⏳ 验证中
4. ✅ 操作确认对话框（破坏性操作）：
   - Stop/Restart 操作提示：确认停止 Ollama 实例？
   - 删除配置提示：确认删除自定义路径配置？
5. ✅ 批量操作支持（可选）：
   - "Stop All" 按钮（停止所有运行中的 provider）
   - "Restart All" 按钮

---

## P2 长期治理任务

### Task 9: Provider 抽象层重构
**优先级**: P2
**目标**: 统一接口，易于扩展

**验收标准**:
1. ✅ 统一 Provider 接口：
   ```python
   class Provider(ABC):
       @abstractmethod
       def detect_executable(self) -> Optional[Path]:
           """检测可执行文件"""

       @abstractmethod
       def validate_executable(self, path: Path) -> bool:
           """验证可执行文件"""

       @abstractmethod
       def start(self, config: dict) -> ProcessInfo:
           """启动 provider"""

       @abstractmethod
       def stop(self, pid: int) -> bool:
           """停止 provider"""

       @abstractmethod
       def status(self, pid: Optional[int]) -> ProviderStatus:
           """获取状态"""

       @abstractmethod
       def detect_models_dir(self) -> Optional[Path]:
           """检测模型目录"""
   ```

2. ✅ 抽象 ProcessManager（跨平台）：
   - 统一进程启动/停止/状态检查
   - 平台差异封装在内部

3. ✅ 抽象 PathResolver（跨平台）：
   - 统一路径探测、验证、规范化

---

### Task 10: 测试覆盖增强
**优先级**: P2
**目标**: CI 可运行，覆盖率 > 80%

**验收标准**:
1. ✅ 路径探测纯函数测试：
   - 输入平台 + provider → 输出候选路径列表
   - 使用 fixtures 覆盖 Windows/macOS/Linux
2. ✅ 进程管理 mock 测试：
   - 不在 CI 真开 Ollama/LMS
   - Mock subprocess.Popen, psutil.Process
3. ✅ API 集成测试：
   - TestClient 测试所有端点
   - 模拟不同状态（未安装、已安装、运行中）
4. ✅ 前端单元测试（可选）：
   - Jest 测试 ProvidersView 组件
   - 测试按钮点击、状态更新

---

### Task 11: 配置迁移与兼容
**优先级**: P2
**目标**: 旧配置不崩，平滑升级

**验收标准**:
1. ✅ 配置版本控制：
   ```json
   {
     "version": "2.0",
     "providers": {...}
   }
   ```
2. ✅ 迁移函数：
   ```python
   def migrate_config_v1_to_v2(old_config: dict) -> dict:
       """从 V1 迁移到 V2"""
   ```
3. ✅ 向后兼容：
   - 读取旧配置时自动迁移
   - 保存时使用新格式
   - 保留旧配置备份

---

## 最小根因集合（优先排查）

根据描述"无法重启/无法启动/无法停止"，建议按此顺序排查：

1. **前端未打到正确 API**（Task 1）
   - 检查：DevTools Network 面板
   - 症状：请求 404/405/500，或无请求
   - 修复：确认路由注册、CORS、认证

2. **后端用 POSIX 信号导致 Windows 全挂**（Task 3）
   - 检查：Windows 上查看错误日志
   - 症状：`os.kill` 或 `signal.SIGTERM` 报错
   - 修复：使用 psutil 或 taskkill

3. **没有记录 PID 或 PID 存储不稳定**（Task 3）
   - 检查：`~/.agentos/run/*.pid` 文件是否存在
   - 症状：stop/restart 失败，提示 "进程不存在"
   - 修复：启动时必须写 PID，停止时读取 PID

4. **LM Studio 当成 CLI 服务来 stop/restart**（Task 3）
   - 检查：LM Studio 的 stop 逻辑
   - 症状：stop 操作无效或报错
   - 修复：标记为 manual_lifecycle，提示用户手动操作

---

## 任务优先级和依赖关系

```
P0 阶段（必须全部完成）:
├─ Task 1: API 调用链路诊断（独立）
├─ Task 2: 可执行文件定位（依赖 Task 1）
├─ Task 3: 进程管理改进（依赖 Task 1, 2）
├─ Task 4: 状态检测（依赖 Task 3）
└─ Task 5: Models 路径安全（依赖 Task 2）

P1 阶段（强烈建议完成）:
├─ Task 6: 自检面板（依赖 Task 2, 3, 4）
├─ Task 7: 错误码改进（依赖 Task 1）
└─ Task 8: 前端交互（依赖 Task 4, 7）

P2 阶段（长期优化）:
├─ Task 9: Provider 抽象层（独立）
├─ Task 10: 测试覆盖（依赖所有 P0/P1）
└─ Task 11: 配置迁移（独立）
```

---

## 验收总标准

**P0 阶段验收**:
- [ ] 在 Windows/macOS/Linux 上 Ollama 可以正常启动/停止/重启
- [ ] 在三平台上 llama.cpp 可以正常启动/停止
- [ ] LM Studio 可以打开应用，stop/restart 有明确提示
- [ ] 所有操作都有日志可查
- [ ] 手动指定路径后可以保存和生效
- [ ] Models 目录浏览不会路径穿越

**P1 阶段验收**:
- [ ] 用户能通过自检面板快速定位问题
- [ ] 所有错误都有友好提示和解决方案
- [ ] 操作流畅，无卡顿或重复点击

**P2 阶段验收**:
- [ ] 代码结构清晰，易于扩展新 provider
- [ ] 测试覆盖率 > 80%
- [ ] 旧配置可自动迁移

---

**文档版本**: V2.0
**创建日期**: 2026-01-29
**基于**: PROVIDERS_CROSS_PLATFORM_FIX_CHECKLIST.md (V1)
**状态**: 待实施
