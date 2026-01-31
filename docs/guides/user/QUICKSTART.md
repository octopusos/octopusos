# AgentOS CLI 快速开始

## 概述

AgentOS CLI 是一个**任务控制平面**（Task Control Plane），让您能够创建、监控、批准和恢复 AI Agent 任务。

**核心特性**:
- 🎯 任务中心化：所有操作都是创建/管理 task
- ⏸️  可中断：任务在关键点暂停，等待人工审批
- 🔄 可恢复：批准后继续执行，完整追溯
- 📊 可审计：每个动作都有 lineage 和 audit 记录

---

## 前置要求

- **Python 3.13+**
- **uv** (推荐) 或 **pip**

### 安装 uv（如果尚未安装）

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

---

## 方式 1: 使用 uv（推荐 ⭐）

**一键运行，无需预装依赖！**

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/AgentOS.git
cd AgentOS

# 2. 验证 CLI 可用（uv 自动安装依赖）
uv run agentos --help

# 3. 初始化数据库（首次运行，必需）
uv run agentos init

# 4. 启动交互式 CLI
uv run agentos
```

**就这么简单！** uv 会自动：
- 创建虚拟环境
- 安装所有依赖（click, rich 等）
- 运行命令

**⚠️  重要**: 
- 使用 `uv run agentos` 而非直接 `agentos`（避免 `command not found`）
- 首次运行必须执行 `uv run agentos init` 初始化数据库

---

## 方式 2: 使用 pip

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/AgentOS.git
cd AgentOS

# 2. 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安装依赖
pip install -e .

# 4. 初始化数据库
agentos init

# 5. 启动 CLI
agentos
# 或显式使用 interactive 子命令
agentos interactive
```

---

## 30 秒验证（Smoke Test）

确认基础功能正常：

```bash
# 1. 验证 CLI 可用
uv run agentos --help

# 2. 初始化数据库
uv run agentos init

# 3. 列出任务（初始为空）
uv run agentos task list
# 输出: 空表格或 "No tasks found"

# 4. 检查数据库文件
ls -lh store/registry.sqlite
# 输出: 应该存在此文件

# ✅ 如果以上都成功，基础设施已就绪！
```

---

## 验证安装

### 检查 CLI 可用性

```bash
# 查看帮助
uv run agentos --help

# 输出示例：
# Usage: agentos [OPTIONS] COMMAND [ARGS]...
#   AgentOS - System-level AI Agent orchestration system
# 
# Commands:
#   init         Initialize AgentOS store
#   interactive  Enter interactive mode (Task Control Plane)
#   task         Task management and tracing commands
#   ...
```

### 检查数据库

```bash
# 初始化数据库（如果尚未执行）
uv run agentos init

# 验证数据库文件存在
ls -lh store/registry.sqlite
# 输出: -rw-r--r-- ... store/registry.sqlite

# 列出任务（初始为空）
uv run agentos task list
# 输出: 空表格或 "Tasks (showing 0)"
```

---

## 快速开始：创建第一个任务

### 方式 1: 交互式模式（推荐）

```bash
# 启动交互式 CLI
uv run agentos
# 或显式使用 interactive 子命令
uv run agentos interactive

# 你会看到主菜单：
# ============================================================
# AgentOS CLI - Task Control Plane
# ============================================================
# 
# 1) 创建新任务 (New task)
# 2) 列出任务 (List tasks)
# 3) 恢复任务 (Resume task)
# 4) 查看任务详情 (Inspect task)
# 5) 设置 (Settings)
# q) 退出 (Quit)
```

**操作流程**:
1. 选择 `1) 创建新任务`
2. 输入任务描述（自然语言）：
   ```
   Create a Python script that prints 'Hello, AgentOS!'
   ```
3. 选择运行模式：
   - `interactive`: 每个阶段需要确认
   - `assisted`: 默认自动，关键点暂停（**推荐**）
   - `autonomous`: 全自动
4. 任务在后台运行，返回主菜单
5. 选择 `2) 列出任务` 查看状态
6. 当状态变为 `awaiting_approval` 时：
   - 选择 `4) 查看任务详情` 查看计划
   - 批准后任务继续执行

### 方式 2: 命令行模式

```bash
# 列出所有任务
uv run agentos task list

# 查看任务详情（需要有已存在的 task_id）
uv run agentos task show <task_id>

# 查看任务执行轨迹
uv run agentos task trace <task_id>

# 恢复暂停的任务
uv run agentos task resume <task_id>
```

**⚠️  注意**: 
- 命令行模式主要用于查看和管理现有任务
- 创建新任务推荐使用交互式模式

---

## 核心概念

### 运行模式（Run Mode）

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `interactive` | 每个阶段都需要人工确认 | 学习、敏感操作 |
| `assisted` | 默认自动，关键点（open_plan）暂停 | 日常使用（推荐） |
| `autonomous` | 全自动执行，无需人工干预 | 批量任务、CI/CD |

### 任务状态

```
created → intent_processing → planning → awaiting_approval → executing → succeeded
                                              ↑
                                         (pause point)
```

### 关键暂停点

- **open_plan**: 任务生成执行计划后，在执行前暂停
- 此时可以：
  - 查看计划（`Inspect task`）
  - 批准继续（`Approve`）
  - 修改计划（未来支持）
  - 终止任务（`Abort`）

---

## 配置

### 全局配置

配置文件: `~/.agentos/settings.json`

```json
{
  "default_run_mode": "assisted",
  "default_model_policy": {
    "default": "gpt-4.1",
    "intent": "gpt-4.1-mini",
    "planning": "gpt-4.1",
    "implementation": "gpt-4.1"
  }
}
```

### 环境变量

```bash
# 数据库路径
export AGENTOS_DB_PATH=/path/to/registry.sqlite

# Debug 模式（显示详细日志）
export AGENTOS_DEBUG=1

# API Keys（如需使用 LLM）
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## 常见问题

### Q: 如何查看任务执行的详细过程？

```bash
# 查看完整 trace（包含所有 lineage 和 audit）
uv run agentos task trace <task_id>

# 输出包含：
# - nl_request: 用户输入
# - runner_spawn/exit: runner 生命周期
# - pipeline: 管道执行
# - execution_request: 执行请求
# - pause_checkpoint: 暂停点
# - approval: 批准记录
```

### Q: 任务卡在 `awaiting_approval` 怎么办？

```bash
# 1. 查看任务详情
uv run agentos task show <task_id>

# 2. 查看计划（通过交互式 CLI）
uv run agentos
# → 选择 "4) 查看任务详情" → 输入 task_id

# 3. 批准任务
# 方式 1: 交互式 CLI（推荐）
uv run agentos
# → "4) 查看任务详情" → 批准

# 方式 2: 命令行
uv run agentos task resume <task_id>
```

### Q: 如何中止任务？

```bash
# 交互式 CLI
uv run agentos
# → "4) 查看任务详情" → 输入 task_id → 选择"终止任务"

# 注意：命令行模式暂不支持直接终止，需使用交互式 CLI
```

### Q: `ModuleNotFoundError: No module named 'click'`？

**原因**: 依赖未安装

**解决**:
```bash
# 方式 1: 使用 uv（推荐）
uv run agentos --help  # uv 会自动安装

# 方式 2: 使用 pip
pip install -e .
```

**如果 `agentos: command not found`**:
- 使用 `uv run agentos` 替代 `agentos`
- 或确保虚拟环境已激活（pip 安装方式）

### Q: 数据库未初始化错误？

**症状**: `sqlite3.OperationalError: no such table: tasks`

**解决**:

```bash
# 如果是新安装，运行初始化命令
uv run agentos init

# 如果是从旧版本升级，运行迁移命令
uv run agentos migrate

# 或者重新初始化（⚠️ 会删除现有数据）
rm store/registry.sqlite
uv run agentos init

# 验证
uv run agentos task list  # 应该显示 "No tasks found"
```

**说明**: `agentos init` 会创建包含所有必需表的完整数据库。如果您从旧版本升级，请运行 `agentos migrate` 来更新 schema。

---

## 高级用法

### 使用真实 Pipeline（P1+）

默认情况下，CLI 使用模拟 pipeline（快速演示）。要使用真实 pipeline：

```bash
# 交互式 CLI 中选择 "Use real pipeline" 选项
# 或通过环境变量
export AGENTOS_USE_REAL_PIPELINE=1
uv run agentos
```

### 查看 Open Plan Artifact（P2+）

```bash
# Open plan 保存为 JSON 文件
ls store/artifacts/<task_id>/open_plan.json

# 查看内容
cat store/artifacts/<task_id>/open_plan.json | jq
```

### 多任务并行

CLI 支持多个任务同时后台运行：

```bash
# 1. 创建任务 A
uv run agentos
# → New task → "Task A"

# 2. 创建任务 B（任务 A 仍在后台运行）
# → New task → "Task B"

# 3. 列出所有任务
# → List tasks

# 4. 分别处理
# → Inspect task → 选择任务 ID
```

---

## 故障排查

### 日志位置

```bash
# 应用日志（如果启用）
tail -f logs/agentos.log

# Runner 日志（后台任务）
# （当前输出到 DEVNULL，可修改 interactive.py 中的 Popen 参数）
```

### Debug 模式

```bash
# 启用详细日志
export AGENTOS_DEBUG=1
uv run agentos
```

### 重置数据库

```bash
# ⚠️  警告：会删除所有任务数据
rm store/registry.sqlite
uv run python -m agentos.store.migrations migrate
```

---

## 下一步

### 学习更多

- 📖 [架构文档](docs/cli/CLI_TASK_CONTROL_PLANE.md) - 核心概念和设计
- 📖 [P0-P2 完成报告](docs/cli/CLI_P2_CLOSEOUT.md) - 实现历程
- 📖 [架构契约](docs/cli/CLI_ARCHITECTURE_CONTRACTS.md) - 核心铁律

### 参与贡献

- 🐛 [报告问题](https://github.com/your-org/AgentOS/issues)
- 💡 [功能建议](https://github.com/your-org/AgentOS/discussions)
- 🔧 [提交 PR](https://github.com/your-org/AgentOS/pulls)

### 社区

- 💬 Discord: [加入讨论](https://discord.gg/agentos)
- 🐦 Twitter: [@AgentOS](https://twitter.com/agentos)

---

## 附录：完整命令参考

### 交互式 CLI

```bash
uv run agentos
```

**菜单选项**:
- `1) New task` - 创建新任务
- `2) List tasks` - 列出所有任务
- `3) Resume task` - 恢复暂停的任务
- `4) Inspect task` - 查看任务详情
- `5) Settings` - 配置管理
- `q) Quit` - 退出

### 任务管理命令

```bash
# 列出任务
uv run agentos task list

# 查看任务
uv run agentos task show <task_id>

# 查看轨迹
uv run agentos task trace <task_id>

# 恢复任务
uv run agentos task resume <task_id>

# 强制恢复（跳过检查，危险）
uv run agentos task resume <task_id> --force
```

---

**版本**: 0.3.0 (P2 Complete)  
**最后更新**: 2026-01-26  
**维护者**: AgentOS Team

**🎉 享受使用 AgentOS CLI！**
