# Command Catalog - README

## 概述

Command Catalog (v0.8) 是 AgentOS 的组织常规操作目录，用于定义团队在软件开发生命周期（SDLC）中的标准操作。

**核心定位**：
- ✅ 定义"团队通常会做哪些操作"
- ✅ 记录"何时做、输入输出是什么、风险是什么"
- ❌ 不提供任何执行入口（not executable）
- ❌ 不绑定 Agent 执行权（only recommend roles）

---

## 🚨 四条红线（RED LINES）

### 🟥 红线 C1：Command ≠ 可执行脚本

**禁止**：
- ❌ 包含 `shell`, `bash`, `powershell`, `python`, `code` 字段
- ❌ 包含 `run`, `execute`, `invoke`, `payload` 字段
- ❌ 任何"直接可运行"的内容

**原因**：Command 是"操作定义"，不是"自动化脚本"。执行权在 v0.9+ 引入，且需要人工审批。

**Schema 强制**：通过 `additionalProperties: false` 排除未定义字段。

---

### 🟥 红线 C2：Command 不能绑定 Agent 执行

**允许**：
- ✅ `recommended_roles: [frontend_engineer, backend_engineer]` - 推荐哪些角色常用

**禁止**：
- ❌ `assigned_agent_id` - 指定执行 Agent
- ❌ `executor` - 绑定执行器
- ❌ `tool_binding` - 工具绑定
- ❌ `agent_binding` - Agent 绑定

**原因**：v0.8 只建立目录，不涉及执行逻辑。Agent-Command 绑定在 v0.10+。

---

### 🟥 红线 C3：Command 必须声明副作用与风险

**必须字段**：

```yaml
effects:
  - scope: repo           # 影响范围：repo/environment/docs/network
    kind: write           # 操作类型：read/write/network
    description: "Creates a new branch reference."

risk_level: medium        # 风险级别：low/medium/high

evidence_required: true   # 是否需要证据（日志/截图）
```

**原因**：明确每个操作的影响范围和风险，支持审计和治理。

**常见 scope**：
- `repo` - 代码仓库
- `environment` - 部署环境（staging/production）
- `docs` - 文档系统
- `network` - 网络调用（API/服务）
- `vcs_platform` - VCS 平台（GitHub/GitLab）
- `design_system` - 设计系统

**常见 kind**：
- `read` - 只读操作
- `write` - 写入操作
- `network` - 网络调用

---

### 🟥 红线 C4：Command 必须可追溯 lineage

**必须字段**：

```yaml
lineage:
  introduced_in: v0.8          # 首次引入版本（必需）
  derived_from: null           # 父 Command ID（root 为 null）
  supersedes: []               # 替代的旧 Command IDs（可空数组）
```

**原因**：支持 Command 演进、版本管理、影响分析。

**示例**（演进场景）：
```yaml
# 新版本 Command
id: cmd_git_create_branch_v2
lineage:
  introduced_in: v0.9
  derived_from: cmd_git_create_branch  # 从 v0.8 版本演进
  supersedes: [cmd_git_create_branch]  # 替代旧版本
```

---

## 📋 Command 定义模板

### 最小模板

```yaml
id: cmd_<category>_<action>
type: command
version: 0.8.0
category: git  # 对应目录名
title: "Create Feature Branch"
description: "Create a new feature branch following project naming conventions."

recommended_roles:
  - frontend_engineer
  - backend_engineer

workflow_links:
  - workflow: feature_implementation
    phases: [setup]

inputs:
  - name: branch_name
    type: string
    required: true
    description: "Branch name following naming conventions."

outputs:
  - name: branch_ref
    type: string
    description: "Created branch reference."

preconditions:
  - "repository_accessible"
  - "working_tree_clean"

effects:
  - scope: repo
    kind: write
    description: "Creates a new branch reference."

risk_level: low
evidence_required: false

constraints:
  executable_payload: forbidden
  agent_binding: forbidden

lineage:
  introduced_in: v0.8
  derived_from: null
  supersedes: []
```

---

## 🗂️ 目录结构

```
docs/content/commands/
├── README.md                    # 本文件
├── git/                         # Git / 变更管理 (8)
│   ├── cmd_git_create_branch.yaml
│   ├── cmd_git_sync_main_rebase.yaml
│   ├── cmd_git_commit_with_intent.yaml
│   ├── cmd_git_create_pr.yaml
│   ├── cmd_git_update_pr_description.yaml
│   ├── cmd_git_tag_release.yaml
│   ├── cmd_git_revert_commit.yaml
│   └── cmd_git_cherry_pick.yaml
├── product/                     # 需求/产品 (4)
│   ├── cmd_prd_create.yaml
│   ├── cmd_prd_update_scope.yaml
│   ├── cmd_define_acceptance_criteria.yaml
│   └── cmd_release_notes_draft.yaml
├── design/                      # 设计 (3)
│   ├── cmd_design_token_update.yaml
│   ├── cmd_component_spec_create.yaml
│   └── cmd_design_review_checklist.yaml
├── architecture/                # 架构 (3)
│   ├── cmd_adr_create.yaml
│   ├── cmd_architecture_review_checklist.yaml
│   └── cmd_dependency_audit.yaml
├── engineering/                 # 实现 (5)
│   ├── cmd_run_lint.yaml
│   ├── cmd_run_typecheck.yaml
│   ├── cmd_run_unit_tests.yaml
│   ├── cmd_generate_api_client.yaml
│   └── cmd_db_migration_create.yaml
├── quality/                     # 测试 (3)
│   ├── cmd_test_plan_create.yaml
│   ├── cmd_regression_suite_run.yaml
│   └── cmd_test_report_generate.yaml
├── security/                    # 安全 (3)
│   ├── cmd_security_scan_dependency.yaml
│   ├── cmd_secret_scan.yaml
│   └── cmd_threat_model_template.yaml
├── operations/                  # 部署/运行 (6)
│   ├── cmd_build_artifact.yaml
│   ├── cmd_deploy_staging.yaml
│   ├── cmd_deploy_production.yaml
│   ├── cmd_rollback_release.yaml
│   ├── cmd_health_check.yaml
│   └── cmd_observability_dashboard_check.yaml
├── incident/                    # 事故响应 (3)
│   ├── cmd_incident_create_ticket.yaml
│   ├── cmd_incident_collect_logs.yaml
│   └── cmd_incident_postmortem.yaml
└── documentation/               # 文档 (2)
    ├── cmd_docs_update_index.yaml
    └── cmd_docs_publish.yaml
```

**总计**: 40 条 Commands

---

## 🎯 命名规范

### Command ID 格式

```
cmd_<category>_<action>
```

**示例**：
- `cmd_git_create_branch` - Git 类别，创建分支动作
- `cmd_prd_create` - 产品类别，创建 PRD 动作
- `cmd_deploy_production` - 运维类别，部署生产动作

### Category 对应目录

- `category: git` → `docs/content/commands/git/`
- `category: product` → `docs/content/commands/product/`
- `category: operations` → `docs/content/commands/operations/`

---

## 🔄 审批流程

### 新增 Command

1. 创建 YAML 文件（遵循模板）
2. 确保 4 条红线全部满足
3. 运行 Schema 验证：
   ```bash
   uv run python scripts/convert_commands.py --validate
   ```
4. 运行红线检查：
   ```bash
   uv run python scripts/register_commands.py --validate-only
   ```
5. 提交 PR（必须包含 YAML + 更新 catalog）

### 修改现有 Command

**禁止**：直接修改已有 Command（破坏 lineage）

**正确方式**：
1. 创建新版本 Command（`<id>_v2`）
2. 设置 `lineage.derived_from` 指向旧版本
3. 设置 `lineage.supersedes` 包含旧版本 ID
4. 旧版本标记为 `deprecated`（通过 ContentRegistry）

---

## 🔍 CLI 使用

### 列出所有 Commands

```bash
# 列出所有 Command
uv run agentos content list --type command

# 按 category 过滤
uv run agentos content list --type command --category git

# 搜索
uv run agentos content search "rollback"
```

### 查看 Command 详情

```bash
# 显示 Command 完整定义
uv run agentos content explain cmd_git_create_branch

# 输出包含：
# - 标题/描述
# - 推荐角色
# - 关联 Workflows
# - 输入/输出
# - 前置条件
# - 副作用（effects）
# - 风险级别
# - 红线约束
# - Lineage 追溯
```

### 注册 Commands

```bash
# 验证红线（不注册）
uv run python scripts/register_commands.py --validate-only

# 注册所有 Commands
uv run python scripts/register_commands.py

# 注册并自动激活
uv run python scripts/register_commands.py --auto-activate
```

### 生成统计报告

```bash
# 查看 Catalog 统计
uv run agentos content catalog-summary

# 输出：
# - 总 Commands 数
# - 按 category 聚合
# - 按 risk_level 聚合
# - 按 effects.kind 聚合
```

---

## ⚠️ 常见错误

### 错误 1：包含可执行代码

```yaml
# ❌ 错误
shell: "git checkout -b $branch_name"
execute: |
  git checkout -b feature-branch
  git push origin feature-branch
```

**违反**：红线 C1

**修复**：移除所有可执行字段，只保留"操作定义"。

---

### 错误 2：绑定 Agent

```yaml
# ❌ 错误
assigned_agent_id: frontend_engineer
executor: agent_bot_001
```

**违反**：红线 C2

**修复**：改用 `recommended_roles`。

---

### 错误 3：缺少 effects

```yaml
# ❌ 错误
effects: []  # 空数组
```

**违反**：红线 C3

**修复**：明确声明副作用：

```yaml
effects:
  - scope: repo
    kind: write
    description: "Updates main branch reference."
```

---

### 错误 4：缺少 lineage

```yaml
# ❌ 错误
lineage: {}  # 空对象
```

**违反**：红线 C4

**修复**：明确声明 lineage：

```yaml
lineage:
  introduced_in: v0.8
  derived_from: null
  supersedes: []
```

---

## 📚 相关文档

- [Command Catalog 索引](../command-catalog.md) - 所有 Commands 的分类导航
- [v0.8 实施报告](../../V08_IMPLEMENTATION_COMPLETE.md) - v0.8 交付详情
- [Workflow Catalog](../workflow-catalog.md) - Workflow 定义
- [Agent Catalog](../agent-catalog.md) - Agent 定义

---

## 🚀 下一步（v0.9+）

v0.8 Command Catalog 只提供"目录和治理"，不涉及执行。

**未来版本**：
- **v0.9**: Command 执行器（需人工审批）
- **v0.10**: Agent-Command 绑定（Agent 可推荐 Command）
- **v1.0**: Command 编排（组合成 Runbook）

---

**最后更新**: 2026-01-25  
**版本**: 0.8.0  
**状态**: ✅ ACTIVE
