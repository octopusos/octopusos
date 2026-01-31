# Provider 配置功能更新

## 🎯 更新概述

在原有启动检查器的基础上，新增了 **Provider 服务启动、端口配置和连接验证**功能，确保 WebUI 启动后可以直接使用 AI Provider 进行 chat。

## ✨ 新增功能

### 1. Provider 服务自动启动

**Ollama 启动：**
- 检测 Ollama 是否已运行
- 如果未运行，询问是否启动
- 交互式配置端口（默认 11434）
- 自动启动服务并等待就绪

**LM Studio / llama.cpp：**
- 检测运行状态
- 提供手动启动提示
- 更新配置文件

### 2. 端口配置

支持自定义端口配置：

| Provider | 默认端口 | 可配置 |
|----------|---------|--------|
| Ollama | 11434 | ✅ |
| LM Studio | 1234 | ✅ |
| llama.cpp | 8080 | ✅ |

### 3. 连接验证

启动 Provider 后自动验证：
- ✅ API 连接测试
- ✅ 模型列表获取
- ✅ 显示模型数量

### 4. 配置文件更新

自动更新 `~/.agentos/config/providers.json`：
- 保存 base_url
- 启用 instance
- 持久化配置

## 🚀 使用流程

### 场景 1: Ollama 已安装但未运行

```bash
$ uv run agentos webui start

═══ 检查本地 AI Provider ═══
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ 状态          ┃ 信息               ┃
┣━━━━━━━━━━╋━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━┫
┃ Ollama   ┃ ✓ 可用        ┃ v0.15.2            ┃
┗━━━━━━━━━━┻━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━┛

✓ 使用 Provider: Ollama

配置 Ollama...
⚠️  Ollama 服务未运行
请输入 Ollama 服务端口 [11434]:
是否启动 Ollama 服务 (端口 11434)? [Y/n]: y

正在启动 Ollama 服务 (端口 11434)...
✓ Ollama 服务启动成功

验证 Ollama 连接...
✓ 连接成功，发现 3 个模型

更新 Provider 配置...
✓ 已更新配置: ollama -> http://127.0.0.1:11434
配置文件: ~/.agentos/config/providers.json
```

### 场景 2: Ollama 已运行

```bash
$ uv run agentos webui start

═══ 检查本地 AI Provider ═══
✓ 使用 Provider: Ollama

配置 Ollama...
✓ Ollama 服务已运行

验证 Ollama 连接...
✓ 连接成功，发现 3 个模型

更新 Provider 配置...
✓ 已更新配置: ollama -> http://127.0.0.1:11434
```

### 场景 3: 多个 Provider 可用

```bash
═══ 检查本地 AI Provider ═══
┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Provider ┃ 状态          ┃ 信息               ┃
┣━━━━━━━━━━╋━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━┫
┃ Ollama   ┃ ✓ 可用        ┃ v0.15.2            ┃
┃ llama.cpp┃ ✓ 可用        ┃ llama-cli 可用     ┃
┗━━━━━━━━━━┻━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━┛

检测到多个可用的 Provider

请选择默认使用的 Provider:
  1. Ollama
  2. llama.cpp
请输入编号 [1]: 1
✓ 已选择: Ollama

配置 Ollama...
（后续流程同上）
```

### 场景 4: 自定义端口

```bash
配置 Ollama...
⚠️  Ollama 服务未运行
请输入 Ollama 服务端口 [11434]: 9090
是否启动 Ollama 服务 (端口 9090)? [Y/n]: y

正在启动 Ollama 服务 (端口 9090)...
✓ Ollama 服务启动成功

验证 Ollama 连接...
✓ 连接成功，发现 3 个模型

更新 Provider 配置...
✓ 已更新配置: ollama -> http://127.0.0.1:9090
```

### 场景 5: LM Studio（手动启动）

```bash
✓ 使用 Provider: LM Studio

配置 LM Studio...
⚠️  LM Studio 需要手动启动
请启动 LM Studio 应用并加载模型
默认端口: 1234

更新 Provider 配置...
✓ 已更新配置: lmstudio -> http://127.0.0.1:1234
```

## 🔧 技术实现

### 代码结构

```
agentos/cli/
├── provider_checker.py
│   ├── start_ollama(port)           # 启动 Ollama 服务
│   └── verify_ollama_connection()   # 验证连接
│
└── startup_checker.py
    ├── _configure_provider()        # 配置 Provider 入口
    ├── _configure_ollama()          # 配置 Ollama
    ├── _configure_lm_studio()       # 配置 LM Studio
    ├── _configure_llama_cpp()       # 配置 llama.cpp
    └── _update_provider_config()    # 更新配置文件
```

### Ollama 启动流程

```python
def start_ollama(port: int = 11434) -> bool:
    1. 检查服务是否已运行 (GET /api/version)
    2. 如果已运行，直接返回成功
    3. 如果未运行：
       - 设置环境变量 OLLAMA_HOST=127.0.0.1:port
       - 启动: ollama serve
       - 等待最多 15 秒
       - 每秒检查一次 /api/version
       - 返回启动结果
```

### 连接验证流程

```python
def verify_ollama_connection(port: int) -> (bool, str):
    1. 请求 GET http://localhost:{port}/api/tags
    2. 解析返回的模型列表
    3. 返回结果：
       - 成功 + 模型数量
       - 成功 + 未安装模型提示
       - 失败 + 错误信息
```

### 配置更新流程

```python
def _update_provider_config(provider_id, port):
    1. 创建 ProvidersConfigManager 实例
    2. 映射 provider_id:
       - ollama -> ollama
       - lm_studio -> lmstudio
       - llama_cpp -> llamacpp
    3. 构建 base_url: http://127.0.0.1:{port}
    4. 调用 update_instance() 更新配置
    5. 保存到 ~/.agentos/config/providers.json
```

## 📋 配置文件示例

`~/.agentos/config/providers.json`:

```json
{
  "providers": {
    "ollama": {
      "enabled": true,
      "executable_path": null,
      "auto_detect": true,
      "instances": [
        {
          "id": "default",
          "base_url": "http://127.0.0.1:11434",
          "enabled": true,
          "metadata": {
            "note": "Auto-configured by startup checker"
          }
        }
      ]
    },
    "lmstudio": {
      "enabled": true,
      "executable_path": null,
      "auto_detect": true,
      "manual_lifecycle": true,
      "supported_actions": ["open_app", "detect"],
      "instances": [
        {
          "id": "default",
          "base_url": "http://127.0.0.1:1234",
          "enabled": true
        }
      ]
    },
    "llamacpp": {
      "enabled": true,
      "executable_path": null,
      "auto_detect": true,
      "instances": [
        {
          "id": "default",
          "base_url": "http://127.0.0.1:8080",
          "enabled": true
        }
      ]
    }
  }
}
```

## 🧪 测试验证

### 测试脚本

创建了 `test_provider_config.py` 用于验证：
- ✅ 配置文件读取
- ✅ Provider 配置获取
- ✅ 连接验证功能

### 测试结果

```bash
$ python3 test_provider_config.py

==================================================
测试 Provider 配置管理
==================================================

1. 读取 Ollama 配置:
   Provider ID: ollama
   Enabled: True
   Instances: 1
     - default: http://127.0.0.1:11434 (enabled: True)

2. 读取 LM Studio 配置:
   Provider ID: lmstudio
   Enabled: True
   Instances: 1
     - default: http://127.0.0.1:1234 (enabled: True)

3. 读取 llama.cpp 配置:
   Provider ID: llamacpp
   Enabled: True
   Instances: 1
     - default: http://127.0.0.1:8080 (enabled: True)

✓ 配置读取成功
✓ 连接验证功能正常
```

## 🎯 使用效果

### 启动前

```
WebUI 启动 → 进入 Chat → 报错: Provider 未配置
```

### 启动后

```
uv run agentos webui start
↓
自动检测 Provider
↓
启动 Ollama 服务
↓
验证连接 (发现 3 个模型)
↓
更新配置文件
↓
WebUI 启动
↓
进入 Chat → 直接可用！✅
```

## 🔍 故障排除

### 问题 1: Ollama 启动失败

**可能原因：**
- 端口被占用
- 没有安装模型

**解决方案：**
```bash
# 检查端口占用
lsof -i :11434

# 更换端口启动
uv run agentos webui start
# 然后输入自定义端口如 9090

# 下载模型
ollama pull llama3.2
```

### 问题 2: 连接验证失败

**可能原因：**
- 服务未完全启动
- 防火墙阻止

**解决方案：**
```bash
# 手动启动 Ollama
ollama serve

# 验证服务
curl http://localhost:11434/api/version

# 检查防火墙
# macOS: 系统设置 -> 安全性与隐私 -> 防火墙
# Linux: sudo ufw status
```

### 问题 3: 配置未生效

**可能原因：**
- 配置文件损坏
- 权限问题

**解决方案：**
```bash
# 查看配置文件
cat ~/.agentos/config/providers.json

# 备份并重新生成
cp ~/.agentos/config/providers.json ~/.agentos/config/providers.json.bak
rm ~/.agentos/config/providers.json
uv run agentos webui start  # 会自动创建默认配置
```

## 📊 与原实现的对比

| 功能 | 原实现 | 新实现 |
|------|--------|--------|
| Provider 检测 | ✅ | ✅ |
| Provider 安装 | ✅ Ollama | ✅ Ollama |
| 服务启动 | ❌ | ✅ 自动/手动 |
| 端口配置 | ❌ | ✅ 交互式 |
| 连接验证 | ❌ | ✅ 模型检测 |
| 配置持久化 | ❌ | ✅ providers.json |
| WebUI 可用性 | ⚠️ 需手动配置 | ✅ 开箱即用 |

## 🎉 总结

### 新增内容

1. **自动服务启动** - Ollama 可自动启动
2. **端口配置** - 支持自定义端口
3. **连接验证** - 验证服务可用性和模型
4. **配置持久化** - 自动更新配置文件
5. **多 Provider 支持** - Ollama、LM Studio、llama.cpp

### 用户体验提升

- ✅ **零配置** - 启动即可用
- ✅ **自动化** - 服务自动启动和配置
- ✅ **可视化** - 清晰的状态提示
- ✅ **灵活性** - 支持自定义端口

### 完整流程

```
uv run agentos webui start
↓
检测 Provider → 启动服务 → 配置端口 → 验证连接 → 更新配置 → WebUI 就绪
↓
进入 Chat 页面 → 直接可用！🎉
```

**真正实现了一键启动，开箱即用！** 🚀
