# Providers 跨平台架构设计

## 概述
本文档介绍 AgentOS Providers 跨平台支持的架构设计和实现细节。

## 架构概览

### 模块层次
```
┌─────────────────────────────────────────┐
│           WebUI / API Layer             │
│   (providers_lifecycle, providers_      │
│    instances, providers_models)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Configuration Layer              │
│      (providers_config.py)              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        Cross-Platform Layer             │
│  (platform_utils.py, process_manager)   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        OS / Platform APIs               │
│  (subprocess, psutil, file system)      │
└─────────────────────────────────────────┘
```

### 核心模块

#### 1. platform_utils.py
**职责**: 平台检测、路径管理、可执行文件查找

**关键函数**:
- `get_platform()` - 检测操作系统
- `get_config_dir()` - 获取配置目录（跨平台）
- `find_executable(name)` - 查找可执行文件（跨平台）
- `validate_executable(path)` - 验证可执行文件

**设计要点**:
- 单一职责：只负责平台相关的基础功能
- 无副作用：纯函数，不修改状态
- 易测试：可以 mock platform.system()

**示例代码**:
```python
from agentos.providers.platform_utils import get_platform, find_executable

# 检测平台
platform = get_platform()  # 'windows', 'macos', or 'linux'

# 自动查找可执行文件
ollama_path = find_executable('ollama')
if ollama_path:
    print(f"Found Ollama at: {ollama_path}")
```

#### 2. process_manager.py
**职责**: 跨平台进程管理

**关键功能**:
- 进程启动（Windows: CREATE_NO_WINDOW）
- 进程停止（psutil 统一 API）
- PID 文件管理
- 进程状态监控

**设计要点**:
- 使用 psutil 抽象平台差异
- 统一的错误处理
- 进程生命周期管理

**示例代码**:
```python
from agentos.providers.process_manager import ProcessManager

# 创建进程管理器
pm = ProcessManager()

# 启动进程（自动处理平台差异）
process = await pm.start_process(
    command=['ollama', 'serve'],
    instance_key='ollama:default'
)

# 停止进程（跨平台）
await pm.stop_process('ollama:default', timeout=10)

# 检查进程状态
status = pm.get_process_status('ollama:default')
```

#### 3. providers_config.py
**职责**: Provider 配置管理

**新增功能**:
- `executable_path` 配置
- `models_directories` 配置
- 配置迁移

**设计要点**:
- 优先级：配置 > 自动检测 > 默认值
- 向后兼容
- 原子性保存

**示例代码**:
```python
from agentos.providers.providers_config import ProvidersConfig

config = ProvidersConfig()

# 设置可执行文件路径
config.set_executable_path('ollama', '/custom/path/to/ollama')

# 获取路径（自动回退到检测）
path = config.get_executable_path('ollama')

# 配置 models 目录
config.set_models_directory('llamacpp', '/path/to/models')
```

#### 4. providers_errors.py
**职责**: 统一错误处理

**关键功能**:
- 27 个标准错误码
- 统一错误响应格式
- 平台特定建议
- 结构化日志记录

**设计要点**:
- 一致的错误格式
- 可操作的建议
- 详细的上下文信息

**示例代码**:
```python
from agentos.webui.api import providers_errors

# 构建错误响应
error_info = providers_errors.build_executable_not_found_error(
    provider_id='ollama',
    searched_paths=['/usr/local/bin/ollama', '/usr/bin/ollama']
)

# 抛出 HTTP 异常
providers_errors.raise_provider_error(**error_info)
```

---

## 跨平台策略

### 可执行文件检测
**策略**: 3 级回退
1. 用户配置路径
2. 平台标准路径
3. PATH 环境变量

**标准路径映射**:
```python
{
  'ollama': {
    'windows': [
      Path.home() / 'AppData/Local/Programs/Ollama/ollama.exe',
      Path('C:/Program Files/Ollama/ollama.exe')
    ],
    'macos': [
      Path('/usr/local/bin/ollama'),
      Path('/opt/homebrew/bin/ollama'),
      Path.home() / 'Applications/Ollama.app/Contents/MacOS/ollama'
    ],
    'linux': [
      Path('/usr/local/bin/ollama'),
      Path('/usr/bin/ollama'),
      Path.home() / '.local/bin/ollama'
    ]
  },
  'llama-server': {
    # Similar structure for llamacpp
  },
  'lmstudio': {
    # Similar structure for LM Studio
  }
}
```

### 进程管理
**Windows 特殊处理**:
- `CREATE_NO_WINDOW`: 避免 CMD 窗口
- `subprocess.CREATE_NO_WINDOW` flag
- psutil.Process.terminate() 替代 taskkill

**Unix 特殊处理**:
- `start_new_session`: 进程分离
- SIGTERM → SIGKILL: 优雅关闭
- 信号处理

**统一接口**:
```python
# 跨平台启动
if platform.system() == 'Windows':
    process = subprocess.Popen(
        command,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
else:
    process = subprocess.Popen(
        command,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

# 跨平台停止（使用 psutil）
proc = psutil.Process(pid)
proc.terminate()  # 发送 SIGTERM (Unix) 或 TerminateProcess (Windows)
proc.wait(timeout=5)
```

### 路径处理
**统一使用 pathlib.Path**:
- 自动处理分隔符（/ vs \）
- 跨平台路径拼接
- 路径规范化

**示例**:
```python
from pathlib import Path

# 正确：跨平台
config_dir = Path.home() / '.agentos' / 'config'

# 错误：硬编码分隔符
config_dir = '~/.agentos/config'  # 在 Windows 上会失败
```

---

## API 设计

### 错误处理
**统一错误格式**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {
      "platform": "macos",
      "searched_paths": [...]
    },
    "suggestion": "Action to take"
  }
}
```

**错误码分类**:
- 4xx: 客户端错误（配置问题）
  - 400: INVALID_PATH, INVALID_CONFIG
  - 403: PERMISSION_DENIED
  - 404: EXECUTABLE_NOT_FOUND, FILE_NOT_FOUND
  - 409: PORT_IN_USE, PROCESS_ALREADY_RUNNING
- 5xx: 服务器错误（系统问题）
  - 500: PROCESS_START_FAILED, INTERNAL_ERROR
  - 504: TIMEOUT_ERROR, STARTUP_TIMEOUT

### 平台特定响应
**在 details 中包含 platform 字段**:
```json
{
  "details": {
    "platform": "windows",
    "searched_paths": [
      "C:\\Program Files\\Ollama\\ollama.exe",
      "C:\\Users\\User\\AppData\\Local\\Programs\\Ollama\\ollama.exe"
    ]
  }
}
```

### API 端点示例

#### 检测可执行文件
```http
GET /api/providers/ollama/executable/detect

Response 200:
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

#### 验证可执行文件路径
```http
POST /api/providers/ollama/executable/validate
{
  "path": "/custom/path/to/ollama"
}

Response 200:
{
  "is_valid": true,
  "path": "/custom/path/to/ollama",
  "version": "0.1.26"
}
```

#### 启动实例
```http
POST /api/providers/ollama/instances/start
{
  "instance_id": "default",
  "timeout": 30
}

Response 200:
{
  "status": "running",
  "instance_key": "ollama:default",
  "pid": 12345
}

Error Response 404:
{
  "error": {
    "code": "EXECUTABLE_NOT_FOUND",
    "message": "Ollama executable not found",
    "details": {
      "platform": "macos",
      "searched_paths": [...]
    },
    "suggestion": "Install via Homebrew: brew install ollama"
  }
}
```

---

## 扩展新 Provider

### 步骤
1. **添加标准路径映射** (platform_utils.py)
2. **实现 Provider Controller** (类似 ollama_controller.py)
3. **添加 API 端点** (providers_lifecycle.py)
4. **更新前端 UI** (ProvidersView.js)
5. **添加测试**

### 示例：添加新 Provider "NewProvider"

#### 1. 添加路径映射
```python
# agentos/providers/platform_utils.py

def get_standard_paths(name: str) -> list[Path]:
    """Get standard installation paths for a provider."""
    platform_type = get_platform()

    paths_map = {
        'newprovider': {
            'windows': [
                Path('C:/Program Files/NewProvider/newprovider.exe'),
                Path.home() / 'AppData/Local/Programs/NewProvider/newprovider.exe'
            ],
            'macos': [
                Path('/usr/local/bin/newprovider'),
                Path('/opt/homebrew/bin/newprovider')
            ],
            'linux': [
                Path('/usr/local/bin/newprovider'),
                Path('/usr/bin/newprovider')
            ]
        }
    }

    return paths_map.get(name, {}).get(platform_type, [])
```

#### 2. 实现 Provider Controller
```python
# agentos/providers/newprovider_controller.py

from agentos.providers.platform_utils import find_executable
from agentos.providers.process_manager import ProcessManager

class NewProviderController:
    def __init__(self):
        self.pm = ProcessManager()

    async def start_instance(self, instance_id: str, config: dict):
        """Start a NewProvider instance."""
        # 查找可执行文件
        executable = find_executable('newprovider')
        if not executable:
            raise FileNotFoundError("NewProvider executable not found")

        # 构建命令
        command = [str(executable), 'serve', '--port', str(config['port'])]

        # 启动进程
        instance_key = f'newprovider:{instance_id}'
        process = await self.pm.start_process(command, instance_key)

        return process

    async def stop_instance(self, instance_id: str, force: bool = False):
        """Stop a NewProvider instance."""
        instance_key = f'newprovider:{instance_id}'
        await self.pm.stop_process(instance_key, force=force)
```

#### 3. 添加 API 端点
```python
# agentos/webui/api/providers_lifecycle.py

from agentos.providers.newprovider_controller import NewProviderController

newprovider_controller = NewProviderController()

@router.post("/providers/newprovider/instances/start")
async def start_newprovider_instance(request: StartInstanceRequest):
    """Start a NewProvider instance."""
    try:
        process = await newprovider_controller.start_instance(
            request.instance_id,
            request.config
        )
        return {"status": "running", "pid": process.pid}
    except FileNotFoundError:
        error_info = providers_errors.build_executable_not_found_error(
            provider_id='newprovider'
        )
        providers_errors.raise_provider_error(**error_info)
```

#### 4. 更新配置 schema
```python
# agentos/providers/providers_config.py

DEFAULT_CONFIG = {
    "providers": {
        "newprovider": {
            "enabled": True,
            "executable_path": None,
            "auto_detect": True,
            "instances": []
        }
    }
}
```

---

## 测试策略

### 单元测试
- Mock `platform.system()` 测试不同平台
- Mock `subprocess.Popen` 测试进程管理
- Mock 文件系统测试路径查找

**示例**:
```python
import pytest
from unittest.mock import patch, MagicMock
from agentos.providers.platform_utils import find_executable

@patch('platform.system')
@patch('pathlib.Path.exists')
def test_find_executable_windows(mock_exists, mock_system):
    """Test executable detection on Windows."""
    mock_system.return_value = 'Windows'
    mock_exists.return_value = True

    result = find_executable('ollama')

    assert result is not None
    assert str(result).endswith('ollama.exe')
```

### 集成测试
- 使用 TestClient 测试 API
- 模拟不同平台的响应

**示例**:
```python
from fastapi.testclient import TestClient

def test_detect_executable_api():
    """Test executable detection API."""
    response = client.get("/api/providers/ollama/executable/detect")

    assert response.status_code == 200
    data = response.json()
    assert 'detected' in data
    assert 'platform' in data
```

### 跨平台测试
- CI/CD 在三个平台运行测试
- GitHub Actions matrix strategy

**示例 .github/workflows/test.yml**:
```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v2
      - name: Run cross-platform tests
        run: pytest tests/providers/
```

---

## 最佳实践

### DO's
- ✅ 使用 pathlib.Path 处理路径
- ✅ 使用 psutil 进行进程管理
- ✅ 提供平台特定的帮助信息
- ✅ 日志记录平台信息
- ✅ 使用 asyncio 进行异步操作
- ✅ 添加超时控制
- ✅ 提供详细的错误信息

### DON'Ts
- ❌ 不要硬编码路径
- ❌ 不要直接使用 os.kill（POSIX only）
- ❌ 不要假设路径分隔符
- ❌ 不要忽略 Windows 的特殊性
- ❌ 不要使用 shell=True（安全风险）
- ❌ 不要阻塞异步函数

### 代码示例

#### ✅ 正确: 跨平台路径处理
```python
from pathlib import Path

config_dir = Path.home() / '.agentos' / 'config'
config_file = config_dir / 'providers.json'
```

#### ❌ 错误: 硬编码路径
```python
config_file = '~/.agentos/config/providers.json'  # Windows 会失败
```

#### ✅ 正确: 跨平台进程管理
```python
import psutil

proc = psutil.Process(pid)
proc.terminate()
proc.wait(timeout=5)
```

#### ❌ 错误: 平台特定代码
```python
import os
import signal

os.kill(pid, signal.SIGTERM)  # Windows 不支持
```

---

## 性能考虑

### 可执行文件查找
**缓存策略**:
```python
_executable_cache = {}

def find_executable(name: str) -> Optional[Path]:
    """Find executable with caching."""
    if name in _executable_cache:
        path = _executable_cache[name]
        if path.exists():
            return path

    # 执行查找
    path = _do_find_executable(name)

    if path:
        _executable_cache[name] = path

    return path
```

### 配置加载
**懒加载 + 缓存**:
```python
class ProvidersConfig:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_config(self):
        """Load config with caching."""
        if self._config is None:
            self._config = self._load_from_disk()
        return self._config
```

### 进程状态检查
**节流**:
```python
import time

class ProcessManager:
    def __init__(self):
        self._last_check = {}
        self._check_interval = 1.0  # 1 second

    def get_process_status(self, instance_key: str):
        """Get process status with throttling."""
        now = time.time()
        last = self._last_check.get(instance_key, 0)

        if now - last < self._check_interval:
            return self._cached_status.get(instance_key)

        # 执行检查
        status = self._check_status(instance_key)
        self._last_check[instance_key] = now
        self._cached_status[instance_key] = status

        return status
```

---

## 安全考虑

### 路径遍历防护
**验证用户输入路径**:
```python
from pathlib import Path

def validate_path(user_path: str, base_dir: Path) -> Path:
    """Validate path to prevent traversal attacks."""
    path = Path(user_path).resolve()

    # 确保路径在允许的基础目录内
    if not str(path).startswith(str(base_dir)):
        raise ValueError("Path traversal detected")

    return path
```

### 权限检查
**确保可执行权限**:
```python
import os
from pathlib import Path

def validate_executable(path: Path) -> bool:
    """Validate executable permissions."""
    if not path.exists():
        return False

    if get_platform() == 'windows':
        # Windows: 检查 .exe 后缀
        return path.suffix.lower() in ['.exe', '.bat', '.cmd']
    else:
        # Unix: 检查可执行权限
        return os.access(path, os.X_OK)
```

### 命令注入防护
**使用列表而非字符串**:
```python
# ✅ 正确: 使用列表
subprocess.Popen(['ollama', 'serve', '--port', '11434'])

# ❌ 错误: 使用字符串（shell=True）
subprocess.Popen('ollama serve --port 11434', shell=True)
```

---

## 参考资料

### 内部文档
- [API Error Handling Guide](../api_error_handling_guide.md)
- [Provider Configuration Guide](../guides/provider-configuration.md)
- [Providers Cross-Platform Setup Guide](../guides/providers_cross_platform_setup.md)

### 实施报告
- [TASK2: Process Manager Refactor Report](../../TASK2_PROCESS_MANAGER_REFACTOR_REPORT.md)
- [TASK4: LM Studio Cross-Platform Report](../../TASK4_LMSTUDIO_CROSS_PLATFORM_REPORT.md)
- [TASK8: API Error Handling Report](../../TASK8_API_ERROR_HANDLING_REPORT.md)

### 源代码
- `agentos/providers/platform_utils.py` - 平台工具模块
- `agentos/providers/process_manager.py` - 进程管理
- `agentos/providers/providers_config.py` - 配置管理
- `agentos/webui/api/providers_errors.py` - 错误处理

### 外部资源
- [psutil Documentation](https://psutil.readthedocs.io/)
- [pathlib Documentation](https://docs.python.org/3/library/pathlib.html)
- [Windows Process Creation Flags](https://docs.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)

---

**文档版本**: v1.0
**最后更新**: 2026-01-29
**适用版本**: AgentOS v0.3.x+
**维护者**: AgentOS Development Team
