# Providers 跨平台优化修复清单

## 问题概述
WebUI 的 Providers 页面存在跨平台兼容性问题，导致 Ollama、LlamaCpp 和 LM Studio 无法正常启动、停止和重启。需要针对 Windows、macOS 和 Linux 实现不同的命令检测机制，并支持手动指定安装位置。

## 核心问题分析

### 当前实现的局限性
1. **进程管理**: 使用 POSIX 信号（SIGTERM/SIGKILL），Windows 不支持
2. **命令检测**: 使用 `which` 命令，Windows 需要 `where`
3. **路径处理**: 未统一使用 `pathlib.Path`，存在硬编码的 Unix 风格路径
4. **LM Studio 启动**: 使用 `open -a`（macOS 专用），不支持 Windows/Linux
5. **配置目录**: `~/.agentos` 在 Windows 上应使用 `%APPDATA%\agentos`
6. **可执行文件扩展名**: Windows 需要 `.exe` 后缀
7. **默认安装路径**: 未适配各平台的标准安装位置

---

## 修复清单

### Phase 1: 核心基础设施重构 (优先级: P0)

#### 1.1 平台检测和路径管理模块
**新建文件**: `agentos/providers/platform_utils.py`

**功能需求**:
- [ ] 统一平台检测（Windows/macOS/Linux）
- [ ] 统一配置目录获取
  - Windows: `%APPDATA%\agentos`（如 `C:\Users\User\AppData\Roaming\agentos`）
  - macOS/Linux: `~/.agentos`
- [ ] 统一临时目录和日志目录
- [ ] 路径规范化工具（统一使用 `pathlib.Path`）

**实现要点**:
```python
import platform
from pathlib import Path

def get_platform():
    """返回 'windows' | 'macos' | 'linux'"""

def get_config_dir() -> Path:
    """获取配置目录"""

def get_run_dir() -> Path:
    """获取进程 PID 文件目录"""

def get_log_dir() -> Path:
    """获取日志目录"""
```

---

#### 1.2 可执行文件检测模块
**修改文件**: `agentos/providers/platform_utils.py`（扩展）

**功能需求**:
- [ ] 跨平台的可执行文件查找（替代 `which`/`where`）
- [ ] 支持标准安装路径搜索
- [ ] 支持用户自定义路径
- [ ] 验证可执行文件有效性

**各平台默认搜索路径**:

##### Ollama
- **Windows**:
  - `C:\Users\{username}\AppData\Local\Programs\Ollama\ollama.exe`
  - `C:\Program Files\Ollama\ollama.exe`
  - PATH 环境变量
- **macOS**:
  - `/usr/local/bin/ollama`
  - `/opt/homebrew/bin/ollama`
  - `~/Applications/Ollama.app/Contents/MacOS/ollama`
  - PATH 环境变量
- **Linux**:
  - `/usr/local/bin/ollama`
  - `/usr/bin/ollama`
  - `~/.local/bin/ollama`
  - PATH 环境变量

##### LlamaCpp (llama-server)
- **Windows**:
  - `C:\Users\{username}\AppData\Local\llama.cpp\llama-server.exe`
  - `C:\Program Files\llama.cpp\llama-server.exe`
  - PATH 环境变量
- **macOS**:
  - `/usr/local/bin/llama-server`
  - `/opt/homebrew/bin/llama-server`
  - PATH 环境变量
- **Linux**:
  - `/usr/local/bin/llama-server`
  - `/usr/bin/llama-server`
  - `~/.local/bin/llama-server`
  - PATH 环境变量

##### LM Studio
- **Windows**:
  - `C:\Users\{username}\AppData\Local\Programs\LM Studio\LM Studio.exe`
  - `C:\Program Files\LM Studio\LM Studio.exe`
- **macOS**:
  - `/Applications/LM Studio.app`
  - `~/Applications/LM Studio.app`
- **Linux**:
  - `~/.local/share/lm-studio/LM Studio.AppImage`
  - `/opt/lm-studio/lm-studio`
  - `~/lm-studio/lm-studio`

**实现要点**:
```python
def find_executable(name: str, custom_paths: list = None) -> Path | None:
    """
    跨平台查找可执行文件

    Args:
        name: 'ollama' | 'llama-server' | 'lmstudio'
        custom_paths: 用户自定义搜索路径列表

    Returns:
        可执行文件路径或 None
    """

def validate_executable(path: Path) -> bool:
    """验证可执行文件是否有效（存在、可执行、版本检查）"""
```

---

#### 1.3 跨平台进程管理模块
**修改文件**: `agentos/providers/process_manager.py`

**功能需求**:
- [ ] 统一进程启动接口（Windows/Unix）
- [ ] 统一进程停止接口（SIGTERM vs taskkill）
- [ ] 进程存活检测（跨平台）
- [ ] 输出流捕获（UTF-8 编码处理）
- [ ] 进程恢复（从 PID 文件）

**关键差异处理**:

| 功能 | Unix (macOS/Linux) | Windows |
|------|-------------------|---------|
| 启动进程 | `subprocess.Popen` | `subprocess.Popen` + `CREATE_NO_WINDOW` |
| 停止进程 | `os.kill(pid, SIGTERM)` | `taskkill /PID {pid} /T /F` |
| 强制杀死 | `os.kill(pid, SIGKILL)` | 已被 `/F` 覆盖 |
| 检查进程 | `os.kill(pid, 0)` | `tasklist /FI "PID eq {pid}"` 或 psutil |
| PID 文件 | `~/.agentos/run/*.pid` | `%APPDATA%\agentos\run\*.pid` |

**实现要点**:
```python
def start_process_cross_platform(
    command: list,
    cwd: Path = None,
    env: dict = None
) -> subprocess.Popen:
    """跨平台启动进程"""
    if platform.system() == 'Windows':
        # 使用 CREATE_NO_WINDOW 标志，防止弹出 CMD 窗口
        return subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    else:
        return subprocess.Popen(command, cwd=cwd, env=env, ...)

def stop_process_cross_platform(pid: int, timeout: int = 5) -> bool:
    """跨平台停止进程"""
    if platform.system() == 'Windows':
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'])
    else:
        os.kill(pid, signal.SIGTERM)
        # 等待优雅关闭...
        os.kill(pid, signal.SIGKILL)

def is_process_running(pid: int) -> bool:
    """跨平台检查进程是否运行"""
    # 推荐使用 psutil.pid_exists(pid)
```

**依赖新增**:
- [ ] 添加 `psutil` 到 `pyproject.toml`（跨平台进程管理）

---

#### 1.4 LM Studio 跨平台启动
**修改文件**: `agentos/webui/api/providers_lifecycle.py`

**功能需求**:
- [ ] Windows: 使用 `start "" "LM Studio.exe"`
- [ ] macOS: 使用 `open -a "LM Studio"`
- [ ] Linux: 使用 `gtk-launch` 或直接执行 AppImage/可执行文件

**实现要点**:
```python
async def open_lmstudio_app():
    """跨平台打开 LM Studio 应用"""
    system = platform.system()

    if system == 'Darwin':  # macOS
        subprocess.Popen(['open', '-a', 'LM Studio'])
    elif system == 'Windows':
        lmstudio_path = find_executable('lmstudio')
        if lmstudio_path:
            subprocess.Popen(['start', '', str(lmstudio_path)], shell=True)
    elif system == 'Linux':
        lmstudio_path = find_executable('lmstudio')
        if lmstudio_path:
            subprocess.Popen([str(lmstudio_path)], start_new_session=True)
```

---

### Phase 2: 配置管理增强 (优先级: P0)

#### 2.1 可执行文件路径配置
**修改文件**: `agentos/providers/providers_config.py`

**配置结构扩展**:
```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "executable_path": "/usr/local/bin/ollama",  // 新增：可执行文件路径
      "auto_detect": true,  // 新增：是否自动检测路径
      "instances": [...]
    },
    "llamacpp": {
      "enabled": true,
      "executable_path": "/opt/homebrew/bin/llama-server",
      "auto_detect": true,
      "instances": [...]
    },
    "lmstudio": {
      "enabled": true,
      "executable_path": "/Applications/LM Studio.app",
      "auto_detect": true,
      "instances": [...]
    }
  }
}
```

**功能需求**:
- [ ] 新增 `executable_path` 字段存储用户自定义路径
- [ ] 新增 `auto_detect` 字段控制自动检测
- [ ] 配置验证：保存时检查路径有效性
- [ ] 配置迁移：自动从旧配置升级

**新增方法**:
```python
def set_executable_path(provider_id: str, path: str | None):
    """设置可执行文件路径"""

def get_executable_path(provider_id: str) -> Path | None:
    """获取可执行文件路径（优先级：配置 > 自动检测）"""
```

---

#### 2.2 Models 目录配置
**修改文件**: `agentos/providers/providers_config.py`

**配置结构扩展**:
```json
{
  "global": {
    "models_directories": {
      "ollama": "/path/to/ollama/models",
      "llamacpp": "/path/to/llamacpp/models",
      "global": "/path/to/shared/models"
    }
  }
}
```

**各平台默认 Models 路径**:

##### Ollama Models
- **Windows**: `C:\Users\{username}\.ollama\models`
- **macOS**: `~/.ollama/models`
- **Linux**: `~/.ollama/models`

##### LlamaCpp Models (用户自定义)
- **建议位置 (Windows)**: `C:\Users\{username}\Documents\AI Models`
- **建议位置 (macOS)**: `~/Documents/AI Models`
- **建议位置 (Linux)**: `~/Documents/AI_Models` 或 `~/models`

##### LM Studio Models
- **Windows**: `C:\Users\{username}\.cache\lm-studio\models`
- **macOS**: `~/.cache/lm-studio/models`
- **Linux**: `~/.cache/lm-studio/models`

**功能需求**:
- [ ] 支持全局 models 目录配置
- [ ] 支持每个 provider 独立配置
- [ ] 自动检测默认 models 目录
- [ ] 模型文件浏览器（API 端点）

---

### Phase 3: API 层改进 (优先级: P1)

#### 3.1 可执行文件检测 API 增强
**修改文件**: `agentos/webui/api/providers_lifecycle.py`

**新增/修改端点**:
- [ ] `GET /api/providers/{provider_id}/executable/detect` - 自动检测可执行文件
- [ ] `POST /api/providers/{provider_id}/executable/validate` - 验证用户提供的路径
- [ ] `PUT /api/providers/{provider_id}/executable` - 设置可执行文件路径

**响应示例**:
```json
{
  "detected": true,
  "path": "/usr/local/bin/ollama",
  "version": "0.1.26",
  "platform": "macos",
  "search_paths": [
    "/usr/local/bin/ollama",
    "/opt/homebrew/bin/ollama"
  ],
  "is_valid": true
}
```

---

#### 3.2 Models 目录管理 API
**新建文件**: `agentos/webui/api/providers_models.py`

**新增端点**:
- [ ] `GET /api/providers/models/directories` - 获取 models 目录配置
- [ ] `PUT /api/providers/models/directories` - 设置 models 目录
- [ ] `GET /api/providers/models/directories/detect` - 自动检测 models 目录
- [ ] `GET /api/providers/models/files` - 浏览 models 目录文件

**功能需求**:
- [ ] 支持按 provider 过滤
- [ ] 支持文件系统浏览（列出 .gguf 等模型文件）
- [ ] 支持模型信息解析（文件大小、量化类型等）

---

#### 3.3 进程管理 API 错误处理
**修改文件**: `agentos/webui/api/providers_lifecycle.py`

**改进点**:
- [ ] 启动失败时返回详细错误信息（可执行文件未找到、端口被占用等）
- [ ] 停止失败时区分错误类型（进程不存在、权限不足、无响应等）
- [ ] 添加超时控制（防止启动/停止操作卡死）
- [ ] 统一错误码和消息格式

**错误响应示例**:
```json
{
  "error": {
    "code": "EXECUTABLE_NOT_FOUND",
    "message": "Ollama executable not found. Please configure the installation path.",
    "details": {
      "searched_paths": ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"],
      "platform": "macos"
    },
    "suggestion": "Install Ollama or specify custom path in settings."
  }
}
```

---

### Phase 4: 前端 UI 改进 (优先级: P1)

#### 4.1 可执行文件配置界面
**修改文件**: `agentos/webui/static/js/views/ProvidersView.js`

**新增功能**:
- [ ] 可执行文件路径配置表单
  - 自动检测按钮（调用 `/api/providers/{id}/executable/detect`）
  - 手动输入路径 + 文件选择器
  - 路径验证（实时）
  - 显示检测到的版本号
- [ ] 安装状态指示器
  - ✅ 已安装并检测到
  - ⚠️ 已安装但路径未配置
  - ❌ 未安装
  - 🔧 配置中（用户自定义路径）

**UI 布局示例**:
```
┌─ Ollama ──────────────────────────────────┐
│ Status: ✅ Ready                          │
│                                            │
│ Executable Path:                           │
│ [/usr/local/bin/ollama] [Detect] [Browse] │
│ Version: 0.1.26 | Platform: macOS         │
│                                            │
│ Instances: [+ Add Instance]                │
│ ...                                        │
└────────────────────────────────────────────┘
```

---

#### 4.2 Models 目录配置界面
**修改文件**: `agentos/webui/static/js/views/ProvidersView.js`

**新增功能**:
- [ ] Models 目录配置面板
  - 全局 models 目录
  - 每个 provider 的独立目录
  - 自动检测默认位置
  - 文件浏览器（显示 .gguf 文件列表）
- [ ] 模型文件选择器
  - 在添加 LlamaCpp 实例时，从 models 目录选择文件
  - 显示文件信息（大小、路径）

**UI 布局示例**:
```
┌─ Models Directories ──────────────────────┐
│ Global Models Directory:                   │
│ [~/Documents/AI Models] [Detect] [Browse] │
│                                            │
│ Provider-specific:                         │
│ • Ollama:   [~/.ollama/models] (auto)     │
│ • LlamaCpp: [Use global ▼] [Browse]       │
│ • LM Studio: [~/.cache/lm-studio] (auto)  │
└────────────────────────────────────────────┘
```

---

#### 4.3 错误提示优化
**修改文件**: `agentos/webui/static/js/views/ProvidersView.js`

**改进点**:
- [ ] 启动失败时显示友好的错误信息
  - "Ollama 未安装，请先安装或配置路径"
  - "端口 11434 已被占用"
  - "模型文件不存在: /path/to/model.gguf"
- [ ] 添加操作指引
  - 提供安装链接（官网下载）
  - 提供配置入口（"点击配置路径"）
- [ ] 平台特定提示
  - Windows: 提示以管理员权限运行
  - macOS: 提示安装 Homebrew
  - Linux: 提示使用包管理器

---

### Phase 5: 核心文件重构清单 (优先级: P0)

#### 5.1 必须修改的文件

| 文件路径 | 修改内容 | 优先级 |
|---------|----------|--------|
| `agentos/providers/platform_utils.py` | **新建**：平台检测、路径管理、可执行文件检测 | P0 |
| `agentos/providers/process_manager.py` | 重构进程启停逻辑，使用 psutil，跨平台兼容 | P0 |
| `agentos/providers/providers_config.py` | 添加 executable_path、models_directories 配置 | P0 |
| `agentos/providers/ollama_controller.py` | 使用 platform_utils 和新的 process_manager | P0 |
| `agentos/webui/api/providers_lifecycle.py` | 添加可执行文件检测/验证 API，LM Studio 跨平台启动 | P0 |
| `agentos/webui/api/providers_models.py` | **新建**：Models 目录管理 API | P1 |
| `agentos/webui/static/js/views/ProvidersView.js` | 添加可执行文件配置 UI、Models 目录配置 UI | P1 |
| `pyproject.toml` | 添加 psutil 依赖 | P0 |

---

### Phase 6: 测试计划 (优先级: P1)

#### 6.1 单元测试
- [ ] `test_platform_utils.py`
  - 测试平台检测
  - 测试可执行文件查找（模拟各平台）
  - 测试路径规范化
- [ ] `test_process_manager_cross_platform.py`
  - 测试进程启动/停止（Windows/Unix）
  - 测试 PID 文件管理
  - 测试进程恢复

#### 6.2 集成测试
- [ ] `test_providers_lifecycle_integration.py`
  - 测试 Ollama 启动/停止/重启（跨平台）
  - 测试 LlamaCpp 启动/停止（跨平台）
  - 测试 LM Studio 应用打开（跨平台）
  - 测试配置保存和加载

#### 6.3 手动测试清单
- [ ] **Windows 10/11**
  - Ollama 启动/停止/重启
  - LlamaCpp 启动/停止（使用 .exe）
  - LM Studio 启动
  - 自动检测安装路径
  - 手动指定自定义路径
  - Models 目录浏览
- [ ] **macOS 13+**
  - 相同测试清单
- [ ] **Linux (Ubuntu 22.04)**
  - 相同测试清单

---

### Phase 7: 文档更新 (优先级: P2)

#### 7.1 用户文档
- [ ] 创建 `docs/providers_setup_guide.md`
  - 各平台安装指南（Ollama、LlamaCpp、LM Studio）
  - 配置可执行文件路径的步骤
  - 配置 models 目录的步骤
  - 常见问题排查（FAQ）

#### 7.2 开发者文档
- [ ] 更新 `docs/architecture/providers.md`
  - 跨平台架构设计
  - platform_utils 模块说明
  - 进程管理机制
- [ ] 添加代码注释
  - 关键跨平台逻辑的注释
  - 平台差异处理的说明

---

## 实现优先级总结

### 🔴 P0 - 立即实施（阻塞问题）
1. 创建 `platform_utils.py`（平台检测、可执行文件查找）
2. 重构 `process_manager.py`（跨平台进程管理）
3. 更新 `ollama_controller.py`（使用新的跨平台 API）
4. 更新 `providers_config.py`（添加 executable_path 配置）
5. 更新 `providers_lifecycle.py` API（可执行文件检测、LM Studio 启动）
6. 添加 `psutil` 依赖

### 🟡 P1 - 高优先级（用户体验）
1. 创建 `providers_models.py` API（Models 目录管理）
2. 更新前端 `ProvidersView.js`（可执行文件配置 UI）
3. 添加 Models 目录配置 UI
4. 优化错误提示和指引
5. 集成测试和手动测试

### 🟢 P2 - 中优先级（完善性）
1. 用户文档编写
2. 开发者文档更新
3. 性能优化（可执行文件检测缓存等）

---

## 预期成果

### 功能改进
✅ Ollama、LlamaCpp、LM Studio 在 Windows/macOS/Linux 上都能正常启动/停止/重启
✅ 自动检测各平台的标准安装路径
✅ 支持用户手动指定自定义安装路径
✅ 统一的 Models 目录管理
✅ 友好的错误提示和操作指引

### 技术改进
✅ 统一的跨平台抽象层（platform_utils）
✅ 可靠的进程管理（使用 psutil）
✅ 清晰的配置结构
✅ 完善的错误处理

### 用户体验改进
✅ 零配置：自动检测安装路径
✅ 灵活配置：支持自定义路径
✅ 清晰反馈：详细的状态和错误信息
✅ 平台一致性：三个平台体验一致

---

## 风险和注意事项

### 技术风险
1. **Windows 权限问题**: 某些操作可能需要管理员权限，需要友好提示
2. **路径编码问题**: Windows 中文路径可能导致编码问题，需要统一使用 UTF-8
3. **进程孤儿问题**: 进程管理失败可能导致孤儿进程，需要清理机制
4. **端口冲突**: 多实例情况下可能端口冲突，需要智能检测和提示

### 兼容性风险
1. **旧版本 LM Studio**: 不同版本的 LM Studio 可能路径不同
2. **第三方发行版**: 通过 Chocolatey、Scoop（Windows）等安装的位置可能不同
3. **容器环境**: Docker 等容器环境下的行为可能不同

### 迁移风险
1. **配置迁移**: 需要向后兼容旧的配置格式
2. **PID 文件迁移**: 已运行的进程需要平滑过渡

---

## 时间估算

| 阶段 | 工作量 | 依赖 |
|------|--------|------|
| Phase 1: 基础设施重构 | 5-7 天 | - |
| Phase 2: 配置管理 | 2-3 天 | Phase 1 |
| Phase 3: API 改进 | 3-4 天 | Phase 1, 2 |
| Phase 4: 前端 UI | 3-4 天 | Phase 3 |
| Phase 5: 文件重构 | 并行于上述阶段 | - |
| Phase 6: 测试 | 3-5 天 | 所有阶段 |
| Phase 7: 文档 | 1-2 天 | 所有阶段 |

**总计**: 约 17-25 天（假设单人全职开发）

---

## 下一步行动

1. **审查清单**: 确认需求和优先级
2. **技术验证**: 在 Windows 环境验证关键技术点（process_manager 重构）
3. **创建开发分支**: `feature/providers-cross-platform`
4. **Phase 1 实施**: 从 `platform_utils.py` 开始
5. **增量发布**: 每完成一个 Phase 发布一个 alpha 版本测试

---

## 附录：关键代码片段预览

### A.1 platform_utils.py 核心接口
```python
"""跨平台工具模块"""
import platform
import shutil
from pathlib import Path

def get_platform() -> str:
    """获取平台标识"""
    system = platform.system()
    if system == 'Windows':
        return 'windows'
    elif system == 'Darwin':
        return 'macos'
    else:
        return 'linux'

def get_config_dir() -> Path:
    """获取配置目录"""
    if get_platform() == 'windows':
        return Path.home() / 'AppData' / 'Roaming' / 'agentos'
    else:
        return Path.home() / '.agentos'

def find_executable(name: str, custom_paths: list[str] = None) -> Path | None:
    """
    跨平台查找可执行文件

    查找顺序:
    1. 用户自定义路径
    2. 平台标准安装路径
    3. PATH 环境变量
    """
    # 1. 检查自定义路径
    if custom_paths:
        for path_str in custom_paths:
            path = Path(path_str)
            if path.exists() and validate_executable(path):
                return path

    # 2. 检查平台标准路径
    standard_paths = get_standard_paths(name)
    for path in standard_paths:
        if path.exists() and validate_executable(path):
            return path

    # 3. 检查 PATH 环境变量
    exe_name = f"{name}.exe" if get_platform() == 'windows' else name
    path_str = shutil.which(exe_name)
    if path_str:
        return Path(path_str)

    return None

def get_standard_paths(name: str) -> list[Path]:
    """获取各平台的标准安装路径"""
    platform_type = get_platform()

    if name == 'ollama':
        if platform_type == 'windows':
            return [
                Path.home() / 'AppData/Local/Programs/Ollama/ollama.exe',
                Path('C:/Program Files/Ollama/ollama.exe'),
            ]
        elif platform_type == 'macos':
            return [
                Path('/usr/local/bin/ollama'),
                Path('/opt/homebrew/bin/ollama'),
                Path.home() / 'Applications/Ollama.app/Contents/MacOS/ollama',
            ]
        else:  # linux
            return [
                Path('/usr/local/bin/ollama'),
                Path('/usr/bin/ollama'),
                Path.home() / '.local/bin/ollama',
            ]

    # ... 其他 provider 的路径映射

def validate_executable(path: Path) -> bool:
    """验证可执行文件是否有效"""
    if not path.exists():
        return False

    # Windows 检查 .exe 后缀
    if get_platform() == 'windows' and path.suffix != '.exe':
        return False

    # Unix 检查可执行权限
    if get_platform() in ['macos', 'linux']:
        import os
        if not os.access(path, os.X_OK):
            return False

    return True
```

### A.2 跨平台进程管理
```python
"""跨平台进程管理"""
import psutil
import subprocess
import platform
from pathlib import Path

def start_process_safe(command: list[str], **kwargs) -> subprocess.Popen:
    """跨平台安全启动进程"""
    if platform.system() == 'Windows':
        # 防止弹出 CMD 窗口
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    return subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs
    )

def stop_process_safe(pid: int, timeout: int = 5) -> bool:
    """跨平台安全停止进程"""
    try:
        proc = psutil.Process(pid)

        # 尝试优雅关闭
        proc.terminate()
        proc.wait(timeout=timeout)
        return True
    except psutil.TimeoutExpired:
        # 强制杀死
        proc.kill()
        proc.wait(timeout=2)
        return True
    except psutil.NoSuchProcess:
        return True  # 进程已不存在
    except Exception as e:
        logger.error(f"Failed to stop process {pid}: {e}")
        return False

def is_process_running(pid: int) -> bool:
    """检查进程是否运行"""
    return psutil.pid_exists(pid)
```

---

**文档版本**: v1.0
**创建日期**: 2026-01-29
**最后更新**: 2026-01-29
**负责人**: AgentOS Team
