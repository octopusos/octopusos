# 启动检查器测试文档

## 功能概述

新增的启动检查器会在 `agentos webui start` 时自动执行以下检查：

1. **环境检测** - Python 版本、uv 工具
2. **本地 AI Provider 检测** - Ollama、LM Studio、llama.cpp
3. **Python 依赖检测** - 检查关键依赖包是否安装
4. **数据库准备** - 初始化数据库、执行迁移

## 命令选项

```bash
agentos webui start [OPTIONS]

选项:
  --host TEXT       绑定主机 (默认: 使用配置)
  --port INTEGER    绑定端口 (默认: 使用配置)
  --foreground      前台运行 (不在后台)
  --skip-checks     跳过所有环境检查，直接启动
  --auto-fix        自动修复所有问题 (非交互模式)
```

## 测试场景

### 场景 1: 正常启动（已有环境）

**前提条件:**
- 数据库已存在
- 依赖已安装
- Provider 已安装

**命令:**
```bash
uv run agentos webui start
```

**预期结果:**
```
═══════════════════════════════════════
     AgentOS WebUI 启动检查
═══════════════════════════════════════

═══ 环境检测 ═══
✓ Python 版本: 3.13.x
✓ uv 工具: uv x.x.x

═══ 检查本地 AI Provider ═══
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider           ┃ 状态                           ┃ 信息                           ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Ollama             │ ✓ 可用                        │ v0.x.x                        │
│ LM Studio          │ ✗ 不可用                      │ 未运行                         │
│ llama.cpp          │ ✓ 可用                        │ llama-cli 可用                │
└────────────────────┴────────────────────────────────┴────────────────────────────────┘

检测到多个可用的 Provider
请选择默认使用的 Provider:
  1. Ollama
  2. llama.cpp
请输入编号 [1]: 1
✓ 已选择: Ollama

═══ 检查 Python 依赖 ═══
✓ 已安装 7 个依赖包
✓ 所有依赖包已安装

═══ 检查数据库 ═══
✓ 数据库文件存在: store/registry.sqlite
检查数据库迁移...
✓ 数据库已是最新版本

✓ 所有检查通过，准备启动 WebUI

═══════════════════════════════════════

🚀 Starting WebUI at 127.0.0.1:8080...

✅ WebUI started successfully
🌐 URL: http://127.0.0.1:8080
📋 Logs: ~/.agentos/webui.log

提示: 使用 'agentos webui stop' 停止服务
```

### 场景 2: 首次安装（需要初始化）

**前提条件:**
- 数据库不存在
- 依赖已安装
- 没有 Provider

**命令:**
```bash
uv run agentos webui start
```

**预期交互:**
```
═══ 检查本地 AI Provider ═══
⚠️  未检测到本地 AI Provider
建议安装 Ollama 以使用本地模型
您也可以跳过安装，稍后使用云端 API (OpenAI/Anthropic 等)

是否安装 Ollama? [Y/n]: y

正在安装 Ollama...
✓ Ollama 安装成功

提示: 您可以运行以下命令下载模型:
  ollama pull llama3.2
  ollama pull qwen2.5

═══ 检查数据库 ═══
✗ 数据库文件不存在: store/registry.sqlite
是否创建数据库? [Y/n]: y

正在创建数据库...
✓ 数据库已创建: store/registry.sqlite

检查数据库迁移...
发现 33 个待执行的迁移:
  - v01
  - v02
  ...

是否执行数据库迁移? [Y/n]: y

正在执行迁移...
✓ 成功应用 33 个迁移
```

### 场景 3: 非交互模式（CI/CD）

**命令:**
```bash
uv run agentos webui start --auto-fix
```

**说明:**
- 自动安装 Ollama（如果缺失）
- 自动执行 uv sync（如果缺少依赖）
- 自动创建数据库
- 自动执行迁移
- 默认选择 Ollama 作为 Provider
- 所有步骤失败则立即中止

### 场景 4: 跳过检查（快速启动）

**命令:**
```bash
uv run agentos webui start --skip-checks
```

**说明:**
- 跳过所有环境检查
- 直接启动 WebUI
- 适用于已知环境正常的情况

### 场景 5: 缺少依赖

**前提条件:**
- 缺少某些 Python 依赖包

**预期交互:**
```
═══ 检查 Python 依赖 ═══
✓ 已安装 4 个依赖包
⚠️  发现 3 个缺失的依赖包:
  ✗ fastapi
  ✗ uvicorn
  ✗ websockets

是否执行 'uv sync' 安装依赖? [Y/n]: y

正在安装依赖...
✓ 依赖安装成功
```

## Provider 优先级规则

1. **检测到多个 Provider**: 显示选择菜单，默认选择 Ollama
2. **检测到一个 Provider**: 自动使用该 Provider
3. **未检测到 Provider**: 询问是否安装 Ollama

## 失败处理策略

任何步骤失败都会：
1. 显示错误信息
2. 立即中止启动流程
3. 返回错误退出码

**示例:**
```
✗ Ollama 安装失败
请访问 https://ollama.com 手动安装

✗ 启动检查失败，已中止启动
```

## 技术实现

### 模块结构

```
agentos/cli/
├── provider_checker.py    # Provider 检测和安装
├── startup_checker.py     # 启动检查协调器
└── webui_control.py       # CLI 命令入口
```

### Provider 检测逻辑

**Ollama:**
1. 检查命令: `which ollama`
2. 检查 API: `GET http://localhost:11434/api/version`
3. 检查版本: `ollama --version`

**LM Studio:**
1. 检查 API: `GET http://localhost:1234/v1/models`
2. 检查进程: `pgrep -i lm.studio`

**llama.cpp:**
1. 检查命令: `which llama-server`
2. 检查命令: `which llama-cli`
3. 检查命令: `which llama`

### Ollama 安装方法

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
- 提示用户访问 https://ollama.com/download/windows
- 或使用 winget: `winget install Ollama.Ollama`

## 兼容性说明

- **向后兼容**: 使用 `--skip-checks` 跳过所有检查，保持原有行为
- **数据库迁移**: 自动检测并应用未执行的迁移
- **依赖管理**: 优先使用 uv，如果不可用则提示使用 pip

## 注意事项

1. **安装 Ollama 需要管理员权限**: 在某些系统上可能需要 sudo
2. **安装时间较长**: Ollama 安装可能需要 2-5 分钟
3. **网络连接**: 安装和检测需要网络连接
4. **Provider 选择**: 选择的 Provider 不会保存，下次启动仍需选择

## 后续改进建议

1. 保存用户选择的默认 Provider
2. 支持自动下载推荐的模型（如 llama3.2）
3. 添加 Provider 健康检查（启动后验证）
4. 支持更多 Provider（如 LocalAI、vllm 等）
5. 添加配置文件支持，避免重复选择
