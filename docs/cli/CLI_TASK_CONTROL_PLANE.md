# CLI Task Control Plane - 使用指南

## ⚠️ RED LINE: CLI 定位（必读）

**AgentOS CLI 交互模式是控制面，不是新的执行系统。**

```
交互模式（agentos）         = 控制面 UI（人机交互）
命令式 CLI（agentos task） = 脚本 API（稳定接口）
```

### 核心原则

1. **交互模式只是 UI**
   - 所有操作都通过 TaskManager
   - 不绕过任何现有系统
   - 不引入新的执行路径

2. **命令式 CLI 是真正的 API**
   - `agentos task list/show/trace` 是稳定接口
   - 脚本和工具应该用命令式 CLI
   - 交互模式可以内部调用命令式 CLI

3. **共存而非替代**
   - 两种模式永久共存
   - 交互模式是可选的 UX 改进
   - 命令式 CLI 永远是第一公民

## 概述

CLI Task Control Plane 是 AgentOS 的交互式控制台，提供类似 opencode/claude code 的可控、可中断、可恢复的任务执行体验。

### 核心特性

- ✅ **Task-Centric**: 所有操作都是创建/调度/查看/继续/终止 task
- ✅ **后台执行**: Task 在后台运行，CLI 不阻塞
- ✅ **智能暂停**: 在关键点（planning 阶段）自动暂停等待审批
- ✅ **可恢复**: 任务可以随时暂停、恢复、取消
- ✅ **完整审计**: 所有操作都有 lineage 和 audit 记录

## 快速开始

### 1. 进入交互模式

```bash
# 方式 1：直接运行 agentos（无参数）
agentos

# 方式 2：明确指定 interactive 命令
agentos interactive
```

### 2. 主菜单

```
============================================================
  AgentOS CLI - Task Control Plane
============================================================

主菜单
------------------------------------------------------------
1) 创建新任务 (New task)
2) 列出任务 (List tasks)
3) 恢复任务 (Resume task)
4) 查看任务详情 (Inspect task)
5) 设置 (Settings)
q) 退出 (Quit)
------------------------------------------------------------
```

### 3. 创建任务

选择 `1) 创建新任务`，用自然语言描述你的需求：

```
请描述你的任务:
> build a monitoring agent for my system

✅ 任务已创建
   Task ID: 01JAB...
   运行模式: assisted
   状态: created

是否立即启动任务执行? (y/n, 默认: y): y

✅ 后台 Runner 已启动
   任务将在后台执行
   使用选项 2 (List tasks) 或 4 (Inspect task) 查看进度
```

### 4. 查看任务进度

选择 `2) 列出任务`：

```
ID                   状态            标题
---------------------------------------------------------------------------------
01JAB..              planning        build a monitoring agent for my system
```

### 5. 审批任务

当任务状态变为 `awaiting_approval` 时，选择 `3) 恢复任务` 并输入 Task ID：

```
任务等待审批
------------------------------------------------------------
1) 批准并继续 (Approve)
2) 查看计划详情 (View plan)
3) 取消任务 (Abort)
4) 返回 (Back)

选择操作: 1

✅ 任务已批准，状态更新为 executing
重新启动后台 Runner...
✅ 后台 Runner 已启动
```

### 6. 查看任务详情

选择 `4) 查看任务详情`：

```
任务详情:
  ID: 01JAB...
  标题: build a monitoring agent for my system
  状态: succeeded
  运行模式: assisted
  创建时间: 2026-01-26T...
  
自然语言请求:
  build a monitoring agent for my system
  
时间线 (最近 5 条):
  [nl_request] 01JAB... (phase: creation)
  [execution_request] exec_01... (phase: execution)
```

## 运行模式

系统支持三种运行模式（在 Settings 中配置）：

### Interactive（交互式）
- 每个关键阶段都需要人工确认
- 最保守，适合高风险操作

### Assisted（辅助式）⭐ 推荐
- 默认自动执行
- 在 planning 阶段暂停等待审批
- 平衡自动化和控制性

### Autonomous（自主式）
- 全自动执行，不暂停
- 适合已验证的稳定流程

## 设置管理

选择 `5) 设置` 进入设置菜单：

```
当前设置:
1) 默认运行模式: assisted
2) 默认模型策略
3) 执行器限制
4) 返回主菜单
```

### 修改运行模式

```
运行模式:
1) interactive - 每个阶段需要人确认
2) assisted - 默认自动，但关键点可打断 (推荐)
3) autonomous - 全自动执行

选择运行模式 (1-3): 2

✅ 运行模式已更新为: assisted
```

### 配置文件位置

全局配置存储在：`~/.agentos/settings.json`

```json
{
  "default_run_mode": "assisted",
  "default_model_policy": {
    "default": "gpt-4.1",
    "intent": "gpt-4.1-mini",
    "planning": "gpt-4.1",
    "implementation": "gpt-4.1"
  },
  "executor_limits": {
    "max_parallel_tasks": 5,
    "max_retries": 3,
    "timeout_seconds": 3600
  }
}
```

## 命令式 CLI（兼容模式）

现有的命令式 CLI 保持不变，可以直接使用：

```bash
# 列出任务
agentos task list

# 查看任务详情
agentos task show <task_id>

# 查看任务追踪
agentos task trace <task_id>
```

## 架构设计

### 三层模型

1. **运行模式（Run Mode）** - 人机关系
   - Interactive / Assisted / Autonomous
   - 存储在 `task.metadata.run_mode`

2. **执行模式（Mode）** - 系统阶段
   - Implementation / Planning / Design 等
   - Pipeline 内部状态，不可直接跳转

3. **模型策略（Model Policy）** - 算力选择
   - 不同阶段使用不同模型
   - 存储在 `task.metadata.model_policy`

### 状态转换

```
created → intent_processing → planning → awaiting_approval →
executing → succeeded / failed / canceled
```

### 后台执行

- CLI 创建 task 后 fork subprocess 运行 TaskRunner
- Runner 通过数据库与 CLI 通信
- CLI 定期查询 task.status 显示进度
- 无需额外的 IPC 机制

## 端到端测试

运行测试验证整个流程：

```bash
cd /Users/pangge/PycharmProjects/AgentOS
PYTHONPATH=$PWD python3 tests/test_cli_e2e.py
```

测试涵盖：
1. 创建任务
2. 后台执行
3. Planning 阶段暂停
4. 批准继续
5. 成功完成

## 与 opencode/claude code 的区别

| 特性 | opencode | AgentOS CLI |
|------|----------|-------------|
| 状态中心 | session-centric | **task-centric** |
| 中断能力 | 弱 | **强（task 可暂停）** |
| 追溯能力 | 不完整 | **task lineage** |
| 后台执行 | 不清晰 | **明确支持** |
| 审计能力 | 无 | **原生支持** |
| 可恢复性 | 有限 | **完全支持** |

## 核心优势

AgentOS CLI 不是"另一个 opencode"，而是：

> **可治理的 Agent 执行平台的 CLI**

- 不只是"让 AI 多跑几步"
- 而是"让人随时能接管 AI 跑的每一步"
- 工程级 Agent 控制面

## 故障排除

### 数据库未初始化

如果遇到 `no such table: tasks` 错误：

```bash
# 应用 schema
sqlite3 store/registry.sqlite < agentos/store/schema_v06.sql
```

### 后台 Runner 未响应

检查后台进程：

```bash
ps aux | grep task_runner
```

手动启动 Runner：

```bash
python -m agentos.core.runner.task_runner <task_id>
```

## 下一步

- [ ] 集成真实的 Coordinator/Executor pipeline
- [ ] 实现 open_plan 详情查看
- [ ] 支持多任务并行执行
- [ ] 添加任务依赖管理
- [ ] 实现 daemon 模式（独立 Runner 进程）
- [ ] 添加 WebUI（可选）

## 参与贡献

欢迎提交 Issue 和 PR！

## License

[Your License Here]
