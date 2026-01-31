# Providers 跨平台配置指南

## 概述
AgentOS 现在支持在 Windows、macOS 和 Linux 上自动检测和管理本地 AI Providers（Ollama、LlamaCpp、LM Studio）。

## 支持的平台
- ✅ Windows 10/11
- ✅ macOS 13+
- ✅ Linux (Ubuntu 22.04+, 其他发行版)

---

## Ollama 配置

### 安装 Ollama

#### Windows
1. 访问 [ollama.ai](https://ollama.ai)
2. 下载 Windows 安装包
3. 运行安装程序
4. AgentOS 会自动检测安装位置

#### macOS
```bash
# 方法 1: Homebrew (推荐)
brew install ollama

# 方法 2: 官方安装脚本
curl -fsSL https://ollama.ai/install.sh | sh
```

#### Linux
```bash
# Ubuntu/Debian
curl -fsSL https://ollama.ai/install.sh | sh

# 或手动下载二进制文件
```

### 在 AgentOS 中配置

#### 自动检测（推荐）
1. 打开 AgentOS WebUI
2. 进入 **Providers** 页面
3. 在 Ollama 区域，点击 **[Detect]** 按钮
4. 系统会自动搜索标准安装位置
5. 如果检测成功，会显示版本号和路径

#### 手动配置
1. 如果自动检测失败，点击 **[Browse]** 按钮
2. 选择 Ollama 可执行文件：
   - Windows: `C:\Program Files\Ollama\ollama.exe`
   - macOS: `/usr/local/bin/ollama` 或 `/opt/homebrew/bin/ollama`
   - Linux: `/usr/local/bin/ollama` 或 `/usr/bin/ollama`
3. 点击 **[Save]** 保存配置

### 启动 Ollama
1. 在 Providers 页面，找到 Ollama 实例
2. 点击 **[Start]** 按钮
3. 等待状态变为 **Running**
4. 现在可以在 AgentOS 中使用 Ollama 模型了

---

## LlamaCpp (llama-server) 配置

### 安装 llama.cpp

#### Windows
```powershell
# 使用 Scoop
scoop install llama.cpp

# 或从 GitHub 下载预编译版本
# https://github.com/ggerganov/llama.cpp/releases
```

#### macOS
```bash
# Homebrew
brew install llama.cpp

# 或从源码编译
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make llama-server
```

#### Linux
```bash
# 从包管理器安装（如果可用）
sudo apt install llama.cpp  # Ubuntu

# 或从源码编译
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make llama-server
```

### 配置 Models 目录
1. 在 Providers 页面，找到 **Models Directories** 面板
2. 为 LlamaCpp 设置模型目录：
   - Windows: `C:\Users\<你的用户名>\Documents\AI Models`
   - macOS: `~/Documents/AI Models`
   - Linux: `~/Documents/AI_Models` 或 `~/models`
3. 将 .gguf 模型文件放入该目录
4. 点击 **[Save]** 保存配置

### 添加 LlamaCpp 实例
1. 在 Providers 页面，Llama.cpp 区域点击 **[+ Add Instance]**
2. 配置实例参数：
   - **Instance ID**: 自定义名称（如 `qwen3-30b`）
   - **Port**: 端口号（默认 8080，如果冲突使用其他端口）
   - **Model Path**: 点击 **[Browse]** 选择模型文件
   - **Context Size**: 上下文长度（如 8192）
   - **GPU Layers**: GPU 加速层数（如 99）
3. 点击 **[Save]** 保存实例
4. 点击 **[Start]** 启动实例

---

## LM Studio 配置

### 安装 LM Studio

#### Windows
1. 访问 [lmstudio.ai](https://lmstudio.ai)
2. 下载 Windows 安装包
3. 运行安装程序

#### macOS
1. 访问 [lmstudio.ai](https://lmstudio.ai)
2. 下载 macOS 版本
3. 将 LM Studio.app 拖入 Applications 文件夹

#### Linux
1. 下载 AppImage 版本
2. 赋予执行权限：`chmod +x LM-Studio-*.AppImage`
3. 运行 AppImage

### 在 AgentOS 中使用
1. 在 Providers 页面，LM Studio 区域点击 **[Open App]**
2. LM Studio 应用会自动打开
3. 在 LM Studio 中：
   - 下载模型
   - 点击 "Start Server" 启动服务
   - 配置端口（默认 1234）
4. 返回 AgentOS，LM Studio 实例应该显示为 **Running**

**注意**: LM Studio 是独立的 GUI 应用，需要在应用内手动管理模型和启动服务。

---

## 常见问题排查 (FAQ)

### Q1: 点击 Start 按钮没有反应
**可能原因**:
- 可执行文件未安装或路径未配置

**解决方法**:
1. 点击 **[Detect]** 尝试自动检测
2. 如果失败，点击 **[Browse]** 手动选择可执行文件
3. 检查错误提示中的具体信息

### Q2: 启动失败，提示"端口被占用"
**可能原因**:
- 该端口已被其他程序使用
- 同一 Provider 的另一个实例正在运行

**解决方法**:
1. 检查其他实例的端口配置
2. 修改新实例的端口号
3. 或停止占用该端口的其他程序

### Q3: 模型加载失败
**可能原因**:
- 模型文件路径不正确
- 模型文件损坏
- 权限不足

**解决方法**:
1. 使用 **[Browse]** 按钮重新选择模型文件
2. 检查文件是否存在且完整
3. 确保 AgentOS 有读取权限

### Q4: Windows 提示"权限不足"
**解决方法**:
- 以管理员权限运行 AgentOS
- 或修改安装目录的权限

### Q5: macOS 提示"无法打开应用"
**解决方法**:
```bash
# 移除隔离标志
xattr -d com.apple.quarantine /path/to/app
```

### Q6: Linux 提示"command not found"
**解决方法**:
```bash
# 确保可执行文件在 PATH 中
export PATH=$PATH:/usr/local/bin

# 或使用绝对路径配置
```

---

## 平台差异说明

### 配置目录
| 平台 | 配置目录 |
|------|----------|
| Windows | `%APPDATA%\agentos` |
| macOS | `~/.agentos` |
| Linux | `~/.agentos` |

### 默认 Models 目录
| Provider | Windows | macOS | Linux |
|----------|---------|-------|-------|
| Ollama | `%USERPROFILE%\.ollama\models` | `~/.ollama/models` | `~/.ollama/models` |
| LlamaCpp | `%USERPROFILE%\Documents\AI Models` | `~/Documents/AI Models` | `~/Documents/AI_Models` |
| LM Studio | `%APPDATA%\.cache\lm-studio\models` | `~/.cache/lm-studio/models` | `~/.cache/lm-studio/models` |

---

## 进阶配置

### 配置文件位置
- Windows: `%APPDATA%\agentos\config\providers.json`
- macOS/Linux: `~/.agentos/config/providers.json`

### 手动编辑配置文件
```json
{
  "providers": {
    "ollama": {
      "executable_path": "/custom/path/to/ollama",
      "auto_detect": false,
      "instances": [
        {
          "id": "default",
          "base_url": "http://localhost:11434",
          "enabled": true
        }
      ]
    }
  },
  "global": {
    "models_directories": {
      "global": "/shared/models"
    }
  }
}
```

### 环境变量配置

#### Ollama
```bash
# macOS/Linux
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_MODELS=~/.ollama/models

# Windows (PowerShell)
$env:OLLAMA_HOST = "0.0.0.0:11434"
$env:OLLAMA_MODELS = "$HOME\.ollama\models"
```

---

## 获取帮助

如果遇到问题：
1. 查看日志文件：`~/.agentos/logs/ollama.log`（或对应 provider）
2. 检查进程输出：在 Providers 页面点击实例的 **[View Logs]**
3. 提交 Issue：[GitHub Issues](https://github.com/seacow-technology/agentos/issues)

---

**文档版本**: v1.0
**最后更新**: 2026-01-29
**适用版本**: AgentOS v0.3.x+
