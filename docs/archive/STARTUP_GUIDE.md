# AgentOS WebUI 一键启动指南

## 🚀 快速开始

当 uv 存在时，只需一条命令即可启动 AgentOS WebUI：

```bash
uv run agentos webui start
```

系统会自动执行以下操作：

✅ 检查 Python 环境和工具
✅ 检测本地 AI Provider（Ollama/LM Studio/llama.cpp）
✅ 检查并安装缺失的依赖
✅ 初始化数据库
✅ 执行数据库迁移
✅ 启动 WebUI 服务

## 📋 使用场景

### 场景 1: 首次安装（全新环境）

**命令：**
```bash
uv run agentos webui start
```

**系统会提示：**
- 是否安装 Ollama（推荐）
- 是否创建数据库
- 是否执行数据库迁移

**只需按回车接受默认选项，系统会自动完成所有设置！**

---

### 场景 2: 日常使用（环境已就绪）

**命令：**
```bash
uv run agentos webui start
```

**系统会：**
- 快速检查环境
- 确认数据库最新
- 直接启动服务

**预计耗时：2-3 秒**

---

### 场景 3: CI/CD 自动化部署

**命令：**
```bash
uv run agentos webui start --auto-fix
```

**特点：**
- 完全非交互
- 自动修复所有问题
- 默认选择 Ollama
- 失败立即中止

---

### 场景 4: 跳过检查（高级用户）

**命令：**
```bash
uv run agentos webui start --skip-checks
```

**适用于：**
- 确认环境正常
- 需要快速启动
- 调试和测试

---

## 🎯 Provider 选择和配置

### 自动检测的 Provider

1. **Ollama** ⭐️ 推荐
   - 开源免费
   - 支持多种模型
   - 易于安装和使用
   - **支持自动启动** ✨

2. **LM Studio**
   - 图形界面
   - 模型管理方便
   - 需要手动启动

3. **llama.cpp**
   - 轻量级
   - 命令行工具
   - 需要手动启动

### Provider 优先级

- 检测到**多个** Provider → 让您选择（默认 Ollama）
- 检测到**一个** Provider → 自动使用
- 检测到**零个** Provider → 询问是否安装 Ollama

### Provider 自动配置 ✨ 新增

选择 Provider 后，系统会自动：

1. **检查服务状态**
   - Ollama: 检查是否运行
   - LM Studio: 检测应用状态
   - llama.cpp: 检测服务状态

2. **启动服务**（Ollama）
   - 询问端口配置（默认 11434）
   - 自动启动 `ollama serve`
   - 等待服务就绪（最多 15 秒）

3. **验证连接**
   - 测试 API 连接
   - 获取模型列表
   - 显示模型数量

4. **更新配置**
   - 保存到 `~/.agentos/config/providers.json`
   - 配置 base_url 和端口
   - 启用 instance

**完成后，WebUI 的 Chat 功能可以直接使用！** 🎉

---

## 🛠️ 命令选项

```bash
agentos webui start [OPTIONS]
```

### 选项说明

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--host TEXT` | 绑定主机地址 | 127.0.0.1 |
| `--port INTEGER` | 绑定端口 | 8080 |
| `--foreground` | 前台运行（不后台） | 后台运行 |
| `--skip-checks` | 跳过所有检查 | 执行检查 |
| `--auto-fix` | 自动修复（非交互） | 交互模式 |

### 示例

```bash
# 使用自定义端口
uv run agentos webui start --port 9090

# 前台运行（查看实时日志）
uv run agentos webui start --foreground

# 完全自动化（CI/CD）
uv run agentos webui start --auto-fix

# 跳过检查快速启动
uv run agentos webui start --skip-checks
```

---

## 📦 依赖管理

### 自动安装依赖

检测到缺失的依赖时，系统会提示：

```
⚠️  发现 3 个缺失的依赖包:
  ✗ fastapi
  ✗ uvicorn
  ✗ websockets

是否执行 'uv sync' 安装依赖? [Y/n]:
```

按 `Y` 或直接回车，系统会自动安装。

### 手动安装依赖

```bash
# 使用 uv
uv sync

# 或使用 pip
pip install -e .
```

---

## 💾 数据库管理

### 自动初始化

首次启动时，系统会自动：

1. 创建数据库文件：`store/registry.sqlite`
2. 创建版本追踪表
3. 执行所有迁移脚本

### 自动迁移

每次启动时，系统会：

1. 检查当前数据库版本
2. 检测待执行的迁移
3. 询问是否执行（或自动执行）

**完全透明，零配置！**

---

## 🐛 故障排除

### 问题 1: Ollama 安装失败

**解决方案：**
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS (Homebrew)
brew install ollama

# Windows
# 访问 https://ollama.com/download/windows
```

### 问题 2: 依赖安装失败

**解决方案：**
```bash
# 清理并重新安装
uv sync --reinstall

# 或使用 pip
pip install -e . --force-reinstall
```

### 问题 3: 数据库迁移失败

**解决方案：**
```bash
# 查看迁移状态
uv run agentos migrate status

# 备份数据库
cp store/registry.sqlite store/registry.sqlite.backup

# 重新初始化
rm store/registry.sqlite
uv run agentos init
```

### 问题 4: 端口被占用

**解决方案：**
```bash
# 使用不同端口
uv run agentos webui start --port 9090

# 或查看占用端口的进程
lsof -i :8080
```

---

## 📊 检查流程详解

### Phase 1: 环境检测
- ✅ Python 版本
- ✅ uv 工具

### Phase 2: Provider 检测
- 🔍 检测 Ollama
- 🔍 检测 LM Studio
- 🔍 检测 llama.cpp
- 💬 用户选择或自动安装

### Phase 3: 依赖检测
- 📦 检查关键依赖包
- 💬 询问是否安装
- ⚡ 执行 uv sync

### Phase 4: 数据库准备
- 📂 检查数据库文件
- 💬 询问是否创建
- 🔄 检查迁移状态
- 💬 询问是否执行迁移

### Phase 5: 启动服务
- 🚀 启动 WebUI
- 🌐 显示访问地址
- 📋 显示日志路径

**每个阶段失败都会立即中止，确保环境完整性！**

---

## 🎓 最佳实践

### 推荐工作流

1. **首次安装**
   ```bash
   uv run agentos webui start
   # 按提示安装 Ollama 和依赖
   ```

2. **下载模型**（可选）
   ```bash
   ollama pull llama3.2
   ollama pull qwen2.5
   ```

3. **日常使用**
   ```bash
   uv run agentos webui start
   # 快速启动，2-3 秒
   ```

4. **停止服务**
   ```bash
   uv run agentos webui stop
   ```

5. **查看状态**
   ```bash
   uv run agentos webui status
   ```

---

## 🔗 相关命令

```bash
# 查看所有 WebUI 命令
uv run agentos webui --help

# 停止 WebUI
uv run agentos webui stop

# 重启 WebUI
uv run agentos webui restart

# 查看状态
uv run agentos webui status

# 配置管理
uv run agentos webui config --show
```

---

## 📝 注意事项

1. **安装时间**：Ollama 安装可能需要 2-5 分钟
2. **网络需求**：首次安装需要网络连接
3. **管理员权限**：某些系统安装 Ollama 需要 sudo
4. **Provider 选择**：选择不会保存，下次启动仍需选择（后续改进）

---

## 🎉 享受 AgentOS！

启动成功后，访问：

**http://127.0.0.1:8080**

开始您的 AI Agent 之旅！
