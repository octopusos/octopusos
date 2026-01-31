# Ollama 模型下载功能

## 🎯 功能概述

在配置 Ollama 时，如果检测到没有安装任何模型，系统会自动提示用户下载推荐的模型，确保 WebUI Chat 功能可以立即使用。

## ✨ 新增功能

### 1. 模型检测
- ✅ 自动检测已安装的模型
- ✅ 如果没有模型，提示用户下载

### 2. 推荐模型列表
```
1. llama3.2:3b - Llama 3.2 (3B) - 快速，适合日常对话 (~2GB)
2. qwen2.5:7b - Qwen 2.5 (7B) - 中文优化，推荐 (~4.7GB)
3. llama3.2:1b - Llama 3.2 (1B) - 超轻量，快速响应 (~1.3GB)
4. gemma2:2b - Gemma 2 (2B) - Google 开源模型 (~1.6GB)
5. qwen2.5-coder:7b - Qwen 2.5 Coder (7B) - 代码专用 (~4.7GB)
0. 跳过，稍后手动下载
```

### 3. 交互式下载
- ✅ 用户可选择要下载的模型
- ✅ 实时显示下载进度
- ✅ 下载完成后自动验证

### 4. 非交互模式
- ✅ `--auto-fix` 模式自动下载 qwen2.5:7b

## 🚀 使用演示

### 场景 1: 首次安装（无模型）

```bash
$ uv run agentos webui start

═══ 检查本地 AI Provider ═══
✓ 使用 Provider: Ollama

配置 Ollama...
⚠️  Ollama 服务未运行
是否启动 Ollama 服务 (端口 11434)? [Y/n]: y

正在启动 Ollama 服务 (端口 11434)...
✓ Ollama 服务启动成功

验证 Ollama 连接...
✓ 连接成功，但未安装模型

⚠️  Ollama 未安装任何模型
没有模型，Chat 功能将无法使用

推荐的模型:
  1. llama3.2:3b - Llama 3.2 (3B) - 快速，适合日常对话 (~2GB)
  2. qwen2.5:7b - Qwen 2.5 (7B) - 中文优化，推荐 (~4.7GB)
  3. llama3.2:1b - Llama 3.2 (1B) - 超轻量，快速响应 (~1.3GB)
  4. gemma2:2b - Gemma 2 (2B) - Google 开源模型 (~1.6GB)
  5. qwen2.5-coder:7b - Qwen 2.5 Coder (7B) - 代码专用 (~4.7GB)
  0. 跳过，稍后手动下载

请选择要下载的模型 [0/1/2/3/4/5] (2): 2

正在下载模型 qwen2.5:7b...
这可能需要几分钟，取决于网络速度
  pulling manifest
  pulling 8cf9f86d2c17... 100%
  pulling 8eee52b40072... 100%
  pulling 11ce4ee3e170... 100%
  verifying sha256 digest
  writing manifest
  success
✓ 模型 qwen2.5:7b 下载成功

更新 Provider 配置...
✓ 已更新配置: ollama -> http://127.0.0.1:11434

🚀 Starting WebUI...
✅ WebUI started successfully
```

### 场景 2: 跳过下载

```bash
推荐的模型:
  1. llama3.2:3b - Llama 3.2 (3B) - 快速，适合日常对话 (~2GB)
  2. qwen2.5:7b - Qwen 2.5 (7B) - 中文优化，推荐 (~4.7GB)
  ...
  0. 跳过，稍后手动下载

请选择要下载的模型 [0/1/2/3/4/5] (2): 0

⚠️  跳过模型下载
您可以稍后使用以下命令下载:
  ollama pull llama3.2
  ollama pull qwen2.5

是否仍要继续启动 WebUI? (稍后可手动下载模型) [Y/n]: y

⚠️  跳过 Ollama 配置，继续启动 WebUI
提示: 启动 Ollama 后需手动在 WebUI 中配置

🚀 Starting WebUI...
```

### 场景 3: 自动模式

```bash
$ uv run agentos webui start --auto-fix

# 自动选择 qwen2.5:7b 下载
自动下载推荐模型: qwen2.5:7b

正在下载模型 qwen2.5:7b...
这可能需要几分钟，取决于网络速度
  ...
✓ 模型 qwen2.5:7b 下载成功
```

### 场景 4: 已有模型

```bash
验证 Ollama 连接...
✓ 连接成功，发现 3 个模型

更新 Provider 配置...
✓ 已更新配置: ollama -> http://127.0.0.1:11434

# 不会提示下载，直接继续
```

## 🔧 技术实现

### 1. 模型列表获取

**provider_checker.py:**
```python
def get_ollama_models(self, port: int = 11434) -> list:
    """获取已安装的 Ollama 模型列表"""
    endpoint = f"http://localhost:{port}"
    response = requests.get(f"{endpoint}/api/tags", timeout=5)

    if response.status_code == 200:
        data = response.json()
        models = data.get("models", [])
        return [model.get("name", "") for model in models]

    return []
```

### 2. 模型下载

**provider_checker.py:**
```python
def pull_ollama_model(self, model_name: str, port: int = 11434) -> bool:
    """下载 Ollama 模型"""
    env = os.environ.copy()
    env["OLLAMA_HOST"] = f"127.0.0.1:{port}"

    process = subprocess.Popen(
        ["ollama", "pull", model_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env
    )

    # 实时读取输出
    for line in process.stdout:
        logger.info(line.strip())

    process.wait()
    return process.returncode == 0
```

### 3. 交互式选择

**startup_checker.py:**
```python
def _download_ollama_models(self, port: int = 11434) -> bool:
    """交互式下载 Ollama 模型"""

    recommended_models = [
        ("llama3.2:3b", "Llama 3.2 (3B) - 快速，适合日常对话", "~2GB"),
        ("qwen2.5:7b", "Qwen 2.5 (7B) - 中文优化，推荐", "~4.7GB"),
        # ...
    ]

    # 显示选项
    for i, (name, desc, size) in enumerate(recommended_models, 1):
        rprint(f"  {i}. [bold]{name}[/bold] - {desc} ([dim]{size}[/dim])")

    # 用户选择
    choice = Prompt.ask("请选择要下载的模型", choices=["0",...,"5"], default="2")

    # 下载模型
    if choice != "0":
        selected_model = recommended_models[int(choice) - 1][0]
        return self._pull_model_with_progress(selected_model, port)
```

### 4. 进度显示

**startup_checker.py:**
```python
def _pull_model_with_progress(self, model_name: str, port: int) -> bool:
    """下载模型并显示进度"""

    process = subprocess.Popen(
        ["ollama", "pull", model_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    # 实时显示输出
    for line in process.stdout:
        line = line.strip()
        if line and ("pulling" in line.lower() or "success" in line.lower()):
            rprint(f"  [dim]{line}[/dim]")

    return process.returncode == 0
```

## 📊 推荐模型说明

| 模型 | 大小 | 特点 | 适用场景 |
|------|------|------|----------|
| **llama3.2:3b** | ~2GB | 快速响应 | 日常对话、问答 |
| **qwen2.5:7b** | ~4.7GB | 中文优化 | 中文对话、写作（推荐） |
| **llama3.2:1b** | ~1.3GB | 超轻量 | 低配设备、快速响应 |
| **gemma2:2b** | ~1.6GB | Google 开源 | 通用对话 |
| **qwen2.5-coder:7b** | ~4.7GB | 代码专用 | 代码生成、调试 |

### 默认推荐: qwen2.5:7b

**理由：**
1. ✅ 中文支持优秀
2. ✅ 性能和质量平衡好
3. ✅ 大小适中（4.7GB）
4. ✅ 通用性强

## 🔄 完整流程

```
启动 Ollama 服务
    ↓
验证连接
    ↓
检测模型数量
    ↓
┌─────────────┐
│ 是否有模型？│
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
   ✓       ✗
   │       │
   │   显示推荐列表
   │       │
   │   用户选择
   │       │
   │   下载模型
   │       │
   │   验证成功
   │       │
   └───┬───┘
       │
   更新配置
       │
   启动 WebUI
```

## 💡 手动下载模型

如果跳过了自动下载，用户可以稍后手动下载：

```bash
# 下载推荐模型
ollama pull qwen2.5:7b

# 下载其他模型
ollama pull llama3.2
ollama pull mistral
ollama pull codellama

# 查看已安装的模型
ollama list

# 删除模型
ollama rm model_name
```

## 🎯 用户价值

### 1. 零配置体验
- ✅ 不需要手动下载模型
- ✅ 系统自动推荐合适的模型
- ✅ 一次性完成所有设置

### 2. 智能推荐
- ✅ 根据模型特点推荐
- ✅ 显示模型大小，便于选择
- ✅ 默认选择最优模型

### 3. 即时可用
- ✅ 下载完成后立即可用
- ✅ 无需额外配置
- ✅ WebUI Chat 直接能用

### 4. 灵活性
- ✅ 可以选择跳过
- ✅ 可以稍后手动下载
- ✅ 支持非交互模式

## 🐛 错误处理

### 1. 下载失败
```
✗ 模型 qwen2.5:7b 下载失败
是否仍要继续启动 WebUI? (稍后可手动下载模型) [Y/n]:
```

### 2. 网络问题
```
✗ 下载过程出错: Connection timeout
您可以稍后使用以下命令重试:
  ollama pull qwen2.5:7b
```

### 3. 磁盘空间不足
```
✗ 下载失败: No space left on device
请确保有足够的磁盘空间 (~5GB)
```

## 📝 注意事项

1. **网络要求**
   - 需要稳定的网络连接
   - 下载时间取决于网速
   - 建议使用有线网络或稳定的 WiFi

2. **磁盘空间**
   - 确保有足够空间（至少 5-10GB）
   - 模型存储在 `~/.ollama/models`

3. **系统资源**
   - 运行模型需要足够内存
   - 推荐 8GB+ RAM
   - 大模型可能需要更多资源

## ✅ 完成功能

- [x] 模型检测
- [x] 推荐模型列表
- [x] 交互式选择
- [x] 自动下载
- [x] 进度显示
- [x] 下载验证
- [x] 错误处理
- [x] 非交互模式支持
- [x] 跳过选项

**模型下载功能已完全实现！** 🎉

---

**更新时间:** 2026-01-30
**版本:** v1.2
**状态:** ✅ 已完成
