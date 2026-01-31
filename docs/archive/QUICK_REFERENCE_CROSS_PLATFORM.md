# 跨平台兼容性 - 快速参考

## 🌍 支持的平台

✅ **Linux** (Ubuntu, Debian, CentOS, Fedora, etc.)
✅ **macOS** (10.15+)
✅ **Windows** (10/11)

---

## 🚀 快速开始

### Linux
```bash
uv run agentos webui start
```

### macOS
```bash
uv run agentos webui start
```

### Windows
```powershell
uv run agentos webui start
```

**相同的命令，在所有平台上都能工作！** 🎉

---

## 📋 平台差异（自动处理）

| 功能 | Linux | macOS | Windows |
|------|-------|-------|---------|
| Ollama 安装 | curl 脚本 | curl 脚本 | winget |
| 进程启动 | start_new_session | start_new_session | creationflags |
| 进程检测 | pgrep | pgrep | tasklist |
| 路径分隔符 | / | / | \ |
| 命令后缀 | - | - | .exe |

**所有差异都由代码自动处理，无需用户操心！** ✨

---

## 🔧 关键改进

### 1. 后台进程启动
```python
# 自动检测平台并使用正确的方法
if platform.system() == "Windows":
    kwargs["creationflags"] = subprocess.DETACHED_PROCESS
else:
    kwargs["start_new_session"] = True
```

### 2. Ollama 安装
```python
# Linux/macOS: curl 脚本
curl -fsSL https://ollama.com/install.sh | sh

# Windows: winget
winget install --id Ollama.Ollama
```

### 3. 路径处理
```python
# 自动使用正确的分隔符
config_file = Path.home() / ".agentos" / "config.json"
# Linux/macOS: ~/.agentos/config.json
# Windows: C:\Users\user\.agentos\config.json
```

---

## 🧪 测试

### 运行测试脚本
```bash
python3 test_cross_platform.py
```

### 预期输出
```
✓ 平台检测正常
✓ Provider 检测正常
✓ 路径处理正确
✓ subprocess 常量可用
```

---

## 📚 详细文档

- **CROSS_PLATFORM_COMPATIBILITY.md** - 技术细节
- **CROSS_PLATFORM_SUMMARY.md** - 更新总结
- **test_cross_platform.py** - 测试脚本

---

## ⚠️ 注意事项

### Windows
- 需要 winget（Windows 10 1809+ 或 Windows 11）
- 首次运行可能有防火墙提示

### macOS
- 首次运行可能需要在系统设置中允许

### Linux
- 安装可能需要 sudo 权限

---

## ✅ 验证安装

```bash
# 检查 Ollama 是否可用
ollama --version

# 检查服务是否运行
curl http://localhost:11434/api/version

# 启动 WebUI
uv run agentos webui start
```

---

**所有平台都已完全支持！** 🚀
