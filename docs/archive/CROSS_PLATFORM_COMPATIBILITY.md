# 跨平台兼容性实现

## 🌍 支持的平台

- ✅ **Linux** (Ubuntu, Debian, CentOS, Fedora, etc.)
- ✅ **macOS** (10.15+)
- ✅ **Windows** (10/11)

## 🔧 关键跨平台问题和解决方案

### 1. 进程管理

#### 问题
后台进程启动在不同平台上有不同的 API：
- Unix: `start_new_session=True`
- Windows: `creationflags` 需要特殊标志

#### 解决方案

```python
def _start_background_service(self, command: list) -> subprocess.Popen:
    """跨平台启动后台服务"""
    system = platform.system()

    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if system == "Windows":
        # Windows 使用 creationflags
        try:
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP |
                subprocess.DETACHED_PROCESS
            )
        except AttributeError:
            # 旧版本 Python 使用数值
            kwargs["creationflags"] = 0x00000200 | 0x00000008
    else:
        # Unix-like 系统
        kwargs["start_new_session"] = True

    return subprocess.Popen(command, **kwargs)
```

**适用于：**
- `provider_checker.py:_start_background_service()`
- `provider_checker.py:start_ollama()`

### 2. Ollama 安装

#### 问题
不同平台有不同的安装方法：
- Linux/macOS: Shell 脚本
- Windows: winget 或手动安装

#### 解决方案

**Linux/macOS:**
```python
if system in ("Linux", "Darwin"):
    # 下载安装脚本
    result = subprocess.run(
        ["curl", "-fsSL", "https://ollama.com/install.sh"],
        capture_output=True,
        text=True,
        timeout=30
    )

    # 执行脚本
    install_result = subprocess.run(
        ["sh", "-c", result.stdout],
        capture_output=True,
        text=True,
        timeout=300
    )
```

**Windows:**
```python
elif system == "Windows":
    # 检查 winget 是否可用
    if shutil.which("winget") is None:
        logger.warning("winget 不可用，请手动安装")
        return False

    # 使用 winget 安装
    install_result = subprocess.run(
        ["winget", "install", "--id", "Ollama.Ollama",
         "--silent", "--accept-source-agreements"],
        capture_output=True,
        text=True,
        timeout=300
    )
```

### 3. 进程检测

#### 问题
进程检测命令在不同平台上不同：
- Linux/macOS: `pgrep`
- Windows: `tasklist`

#### 解决方案

```python
def check_lm_studio(self) -> Tuple[bool, Optional[str]]:
    """检测 LM Studio 是否运行"""
    # 先尝试 API 检测（跨平台）
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        if response.status_code == 200:
            return True, "运行中"
    except:
        pass

    # 进程检测（平台特定）
    try:
        if platform.system() != "Windows":
            cmd = ["pgrep", "-i", "lm.studio"]
        else:
            cmd = ["tasklist", "/FI", "IMAGENAME eq LM Studio.exe"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            return True, "进程运行中"
    except:
        pass

    return False, "未运行"
```

### 4. 命令可用性检测

#### 问题
不同平台的可执行文件扩展名不同：
- Linux/macOS: 无扩展名
- Windows: `.exe`

#### 解决方案

使用 `shutil.which()` 自动处理：

```python
# 跨平台检测命令是否可用
if shutil.which("ollama") is None:
    return False, "命令不存在"

# shutil.which 会自动:
# - Linux/macOS: 查找 "ollama"
# - Windows: 查找 "ollama.exe"
```

### 5. 路径处理

#### 问题
不同平台的路径分隔符不同：
- Linux/macOS: `/`
- Windows: `\`

#### 解决方案

使用 `pathlib.Path` 自动处理：

```python
from pathlib import Path

# 跨平台路径处理
config_dir = Path.home() / ".agentos" / "config"
config_file = config_dir / "providers.json"

# Path 自动使用正确的分隔符
```

### 6. 环境变量

#### 问题
环境变量名称在 Windows 上不区分大小写，但在 Unix 上区分。

#### 解决方案

```python
import os

# 设置环境变量（跨平台）
env = os.environ.copy()
env["OLLAMA_HOST"] = f"127.0.0.1:{port}"

# os.environ 在所有平台上都工作
```

## 📊 平台特性对比

| 特性 | Linux | macOS | Windows |
|------|-------|-------|---------|
| **Ollama 安装** | ✅ curl 脚本 | ✅ curl 脚本 | ✅ winget |
| **自动启动** | ✅ start_new_session | ✅ start_new_session | ✅ creationflags |
| **进程检测** | ✅ pgrep | ✅ pgrep | ✅ tasklist |
| **命令检测** | ✅ which | ✅ which | ✅ where |
| **路径处理** | ✅ Path | ✅ Path | ✅ Path |
| **API 连接** | ✅ requests | ✅ requests | ✅ requests |

## 🧪 测试覆盖

### Linux 测试
```bash
# Ubuntu 22.04
python3 -c "from agentos.cli.provider_checker import ProviderChecker; pc = ProviderChecker(); print(pc.check_ollama())"

# CentOS 8
python3 -c "from agentos.cli.provider_checker import ProviderChecker; pc = ProviderChecker(); print(pc.check_ollama())"
```

### macOS 测试
```bash
# macOS 12+ (Monterey)
python3 -c "from agentos.cli.provider_checker import ProviderChecker; pc = ProviderChecker(); print(pc.check_ollama())"
```

### Windows 测试
```powershell
# Windows 10/11
python -c "from agentos.cli.provider_checker import ProviderChecker; pc = ProviderChecker(); print(pc.check_ollama())"
```

## 🔍 平台检测代码

```python
import platform

# 获取平台信息
system = platform.system()
# 返回: "Linux", "Darwin" (macOS), "Windows"

# 示例使用
if system == "Windows":
    # Windows 特定代码
    pass
elif system == "Darwin":
    # macOS 特定代码
    pass
elif system == "Linux":
    # Linux 特定代码
    pass
```

## 📝 最佳实践

### 1. 优先使用跨平台 API

```python
# ✅ 好的做法 - 使用跨平台 API
response = requests.get("http://localhost:11434/api/version")

# ❌ 避免 - 使用平台特定命令
subprocess.run(["curl", "http://localhost:11434/api/version"])
```

### 2. 使用 pathlib.Path

```python
# ✅ 好的做法
from pathlib import Path
config_file = Path.home() / ".agentos" / "config.json"

# ❌ 避免
config_file = os.path.expanduser("~/.agentos/config.json")
```

### 3. 条件导入

```python
# ✅ 好的做法 - 处理平台特定功能
import platform

if platform.system() == "Windows":
    import ctypes
    # Windows 特定功能
```

### 4. 异常处理

```python
# ✅ 好的做法 - 捕获平台特定异常
try:
    if platform.system() == "Windows":
        # Windows 代码
        pass
    else:
        # Unix 代码
        pass
except Exception as e:
    logger.error(f"平台特定操作失败: {e}")
```

## 🚨 常见陷阱

### 1. ❌ 硬编码路径分隔符

```python
# ❌ 错误
config_path = home + "/.agentos/config.json"  # Windows 上会失败

# ✅ 正确
config_path = Path.home() / ".agentos" / "config.json"
```

### 2. ❌ 假设 Shell 可用

```python
# ❌ 错误 - Windows 可能没有 sh
subprocess.run("ollama serve", shell=True)

# ✅ 正确
subprocess.run(["ollama", "serve"])
```

### 3. ❌ 使用平台特定进程管理

```python
# ❌ 错误 - 只在 Unix 上工作
subprocess.Popen(cmd, start_new_session=True)

# ✅ 正确 - 使用跨平台方法
if platform.system() == "Windows":
    kwargs["creationflags"] = subprocess.DETACHED_PROCESS
else:
    kwargs["start_new_session"] = True
subprocess.Popen(cmd, **kwargs)
```

## 🔄 Windows 特殊注意事项

### 1. winget 可用性

```python
# 检查 winget 是否可用
if shutil.which("winget") is None:
    # 提供手动下载链接
    print("请访问: https://ollama.com/download/windows")
```

### 2. 管理员权限

某些安装可能需要管理员权限：

```python
# Windows 检测是否有管理员权限
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
```

### 3. 防火墙提示

Windows 首次运行服务时会弹出防火墙提示，需要告知用户。

## ✅ 兼容性检查清单

- [x] 进程启动（Unix vs Windows）
- [x] Ollama 安装（curl vs winget）
- [x] 进程检测（pgrep vs tasklist）
- [x] 命令检测（shutil.which）
- [x] 路径处理（pathlib.Path）
- [x] 环境变量（os.environ）
- [x] API 连接（requests，跨平台）
- [x] 异常处理（所有平台）

## 📚 参考资源

### Python 文档
- [subprocess](https://docs.python.org/3/library/subprocess.html)
- [platform](https://docs.python.org/3/library/platform.html)
- [pathlib](https://docs.python.org/3/library/pathlib.html)
- [shutil](https://docs.python.org/3/library/shutil.html)

### Ollama 文档
- [Linux/macOS 安装](https://ollama.com/download/linux)
- [Windows 安装](https://ollama.com/download/windows)

## 🎉 总结

通过以下措施实现了完整的跨平台支持：

1. ✅ **条件编译** - 根据平台选择不同代码路径
2. ✅ **跨平台 API** - 优先使用跨平台库和 API
3. ✅ **路径处理** - 使用 pathlib.Path
4. ✅ **异常处理** - 处理平台特定异常
5. ✅ **测试覆盖** - 在所有平台上测试

**代码现在可以在 Linux、macOS 和 Windows 上无缝运行！** 🚀
