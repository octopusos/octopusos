# Model Management Guide

AgentOS 模型管理完整指南

## 概述

AgentOS 提供了完整的模型管理系统，支持：
- 🖥️ **本地模型**: Ollama, LM Studio, llama.cpp
- ☁️ **云端模型**: OpenAI, Anthropic, Codex, Claude-Code-CLI
- 🔄 **调用方式**: CLI 命令行或 API 接口
- 🔐 **授权管理**: 交互式配置和安全存储
- 🎯 **智能绑定**: Mode 和 Stage 级别的模型绑定
- ✅ **连通性测试**: 实时测试模型可用性

---

## 快速开始

### 1. 访问模型管理

启动 TUI 后，在 Home 屏幕选择：

```
Home → Model Management
```

您将看到以下选项：
- **Select Model** - 三级菜单选择模型
- **Test Model Connectivity** - 测试模型连通性
- **Bind Mode to Model** - 为 mode 绑定模型
- **Bind Stage to Model** - 为 stage 绑定模型
- **Configure Invocation** - 配置调用方式（CLI/API）
- **Setup Credentials** - 配置授权信息

---

## 三级模型选择

### Level 1: 选择来源

- **🖥️ Local Models** - 在本地运行的模型
- **☁️ Cloud Models** - 云端 API 服务

### Level 2: 选择品牌

**本地品牌**:
- **Ollama** - 易用的本地 LLM 运行环境
- **LM Studio** - 图形化本地模型管理
- **llamacpp** - 高性能 C++ 实现

**云端品牌**:
- **OpenAI** - GPT-4, GPT-4o 等
- **Anthropic** - Claude 系列
- **Codex** - Cursor 的代码模型
- **Claude-Code-CLI** - Claude 的命令行工具

### Level 3: 选择具体模型

显示该品牌下的所有可用模型，带状态标识：
- 🟢 **可用且已授权**
- 🔴 **缺少授权**
- ⚠️ **模型未安装**

每个模型还会显示调用方式标签：`(CLI)` 或 `(API)`

---

## 模型调用方式

### CLI 方式

通过命令行工具调用模型。

**适用场景**:
- 本地开发和调试
- 脚本自动化
- 无需服务器的简单调用

**示例配置**:
```bash
# Codex
codex {prompt}

# Claude Code CLI
claude-code-cli {prompt}

# llama.cpp
llama-cpp-cli --model {model_id} --prompt {prompt}
```

### API 方式

通过 HTTP API 调用模型。

**适用场景**:
- 生产环境
- 高性能要求
- 需要细粒度控制

**示例配置**:
```json
{
  "Ollama": {
    "method": "api",
    "api_endpoint": "http://localhost:11434",
    "requires_auth": false
  },
  "OpenAI": {
    "method": "api",
    "api_endpoint": "https://api.openai.com/v1",
    "requires_auth": true,
    "auth_env_vars": ["OPENAI_API_KEY"]
  }
}
```

---

## 授权配置

### 检查授权状态

运行 "Test Model Connectivity" 查看授权状态：
- 🟢 已配置且有效
- 🔴 缺少 API Key → 点击 `[Setup Credentials]`

### 配置授权信息

#### 方法 1: 通过 TUI（推荐）

1. Home → Model Management → Setup Credentials
2. 选择模型
3. 输入授权信息（如 API Key）
4. 选择存储位置：
   - **Environment Variable** - 临时（当前会话）
   - **Config File** - 持久（加密存储到 `~/.agentos/settings.json`）

#### 方法 2: 手动配置环境变量

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Ollama（不需要授权）
export OLLAMA_HOST="http://localhost:11434"
```

#### 方法 3: 编辑配置文件

```bash
vi ~/.agentos/settings.json
```

添加：
```json
{
  "model_credentials": {
    "gpt-4@OpenAI": {
      "api_key": "sk-..."
    },
    "claude-3@Anthropic": {
      "api_key": "sk-ant-..."
    }
  }
}
```

⚠️ **安全提示**: 生产环境应使用加密存储或密钥管理服务！

---

## Mode 和 Stage 绑定

### 模型选择优先级

AgentOS 按以下优先级选择模型：

```
1️⃣ Mode 绑定（细粒度）
    ↓ 未配置
2️⃣ Stage 绑定（全局策略）
    ↓ 未配置
3️⃣ Codex（默认 fallback）
```

### Mode 绑定

为特定的执行模式绑定模型。

**使用场景**:
- `debug` mode 使用本地 `llama3`（隐私调试）
- `planning` mode 使用快速的 `gpt-4o-mini`
- `implementation` mode 使用强大的 `gpt-4o`

**配置步骤**:
1. Home → Model Management → Bind Mode to Model
2. 选择 Mode（如 `debug`）
3. 选择模型（如 `llama3@Ollama`）
4. 选择调用方式（CLI/API）
5. Save

**结果**:
```json
{
  "mode_model_bindings": {
    "debug": "llama3@Ollama",
    "planning": "gpt-4o-mini@OpenAI",
    "implementation": "gpt-4o@OpenAI"
  }
}
```

### Stage 绑定（ModelPolicy）

为执行阶段配置统一的模型策略。

**执行阶段**:
- `intent` - 意图理解
- `planning` - 规划阶段
- `implementation` - 实施阶段

**配置步骤**:
1. Home → Model Management → Bind Stage to Model
2. 选择 Stage（如 `planning`）
3. 选择模型
4. Save

**结果**:
```json
{
  "default_model_policy": {
    "default": "gpt-4.1",
    "intent": "gpt-4.1-mini",
    "planning": "gpt-4o",
    "implementation": "gpt-4o"
  }
}
```

### 选择逻辑示例

```python
# 场景 1: debug mode，已配置 mode 绑定
mode_id = "debug"
stage = "implementation"
→ 使用 "llama3@Ollama" (来自 mode 绑定)

# 场景 2: planning mode，未配置 mode 绑定
mode_id = "planning"
stage = "planning"
→ 使用 "gpt-4o" (来自 stage 绑定)

# 场景 3: custom mode，都未配置
mode_id = "custom"
stage = "intent"
→ 使用 "codex" (默认 fallback)
```

---

## 连通性测试

### 测试单个模型

1. Home → Model Management → Test Model
2. 输入模型 key（格式: `model_id@brand`）
   - 示例: `gpt-4@OpenAI`
3. 查看结果：
   - 🟢 **Connected** - 正常
   - 🔴 **Auth Failed** - 授权失败 → 点击 Setup Credentials
   - ⚠️ **Unreachable** - 服务不可达

### 测试品牌下所有模型

1. Home → Model Management → Test Brand Models
2. 选择品牌（如 Ollama）
3. 查看每个模型的测试结果和响应时间

### 测试所有模型

1. Home → Model Management → Test All Models
2. 等待批量测试完成
3. 查看汇总报告：
   - 总数
   - 连接成功数
   - 失败详情

---

## 配置文件

### 位置

```
~/.agentos/settings.json
```

### 完整示例

```json
{
  "default_run_mode": "assisted",
  "default_model_policy": {
    "default": "gpt-4.1",
    "intent": "gpt-4.1-mini",
    "planning": "gpt-4o",
    "implementation": "gpt-4o"
  },
  "mode_model_bindings": {
    "debug": "llama3@Ollama",
    "test": "gpt-4o-mini@OpenAI"
  },
  "model_invocation_configs": {
    "llama3@Ollama": {
      "method": "api",
      "api_endpoint": "http://localhost:11434"
    },
    "codex": {
      "method": "cli",
      "cli_command": "codex {prompt}"
    }
  },
  "model_credentials": {
    "gpt-4@OpenAI": {
      "api_key": "sk-..."
    }
  }
}
```

---

## 常见问题

### Q: 如何添加新的本地模型？

**A**: 
1. 在本地服务（如 Ollama）中安装模型
2. 刷新 AgentOS 的模型列表（会自动检测）
3. 测试连通性确保可用

### Q: 模型测试失败怎么办？

**A**: 检查以下几点：
1. 服务是否运行？（如 Ollama: `ollama serve`）
2. 授权是否配置？（运行 Setup Credentials）
3. 网络是否可达？（检查防火墙/代理）
4. 模型是否已下载？（如 Ollama: `ollama pull llama3`）

### Q: Mode 绑定和 Stage 绑定有什么区别？

**A**:
- **Mode 绑定**: 细粒度控制，针对特定执行模式
- **Stage 绑定**: 全局策略，适用于所有任务的相应阶段
- **推荐**: 常规使用 Stage 绑定，特殊场景用 Mode 绑定

### Q: Codex 是什么？为什么是默认？

**A**: 
- Codex 是 Cursor 的代码生成模型
- 适合代码任务（AgentOS 的主要场景）
- 如果 Cursor 已登录，Codex 通常可直接使用
- 未配置其他模型时的合理 fallback

### Q: 如何切换调用方式（CLI ↔ API）？

**A**:
1. Home → Model Management → Configure Invocation
2. 选择模型
3. 选择调用方式（CLI/API）
4. 配置对应的命令或端点
5. Save

### Q: 授权信息安全吗？

**A**:
- 当前版本存储在 `~/.agentos/settings.json`（明文）
- 生产环境建议：
  - 使用环境变量
  - 集成密钥管理服务（如 AWS Secrets Manager）
  - 文件系统加密

---

## 最佳实践

### 1. 分层配置策略

```
全局默认 (Stage 绑定)
└── 快速模型用于 planning（如 gpt-4o-mini）
└── 强大模型用于 implementation（如 gpt-4o）

特殊场景 (Mode 绑定)
└── 本地模型用于 debug（隐私）
└── 云端模型用于 production
```

### 2. 定期测试连通性

```bash
# 每周运行一次完整测试
Home → Model Management → Test All Models
```

### 3. 监控成本

- 云端模型按使用量计费
- 使用 Mode 绑定将测试/开发流量导向本地模型
- 生产流量使用云端模型

### 4. 版本控制配置

```bash
# 将配置加入版本控制（去除敏感信息）
cp ~/.agentos/settings.json ./agentos-config.example.json
# 手动移除 model_credentials 部分
git add agentos-config.example.json
```

---

## 技术架构

### 核心组件

```
ModelRegistry
├── 品牌管理（Local/Cloud）
├── 模型列表查询（动态 API）
├── 调用配置管理
├── 授权检查
└── 连通性测试

ModelInvoker
├── CLI 调用器
├── API 调用器
└── 统一接口

ModelSelector (执行引擎)
├── 优先级逻辑
├── Mode 绑定
├── Stage 绑定
└── Codex fallback
```

### 数据流

```
1. 用户选择模型 (TUI)
   ↓
2. 保存到配置文件 (~/.agentos/settings.json)
   ↓
3. 执行任务时，ModelSelector 读取配置
   ↓
4. 按优先级选择模型
   ↓
5. ModelInvoker 执行调用 (CLI/API)
   ↓
6. 记录到 Audit Log
```

---

## 参考

- [Architecture White Paper](WHITEPAPER_FULL_EN.md)
- [TUI User Guide](TUI_USER_GUIDE.md)
- [Quick Start](../QUICKSTART.md)

---

**最后更新**: 2026-01-26  
**维护者**: AgentOS Team
