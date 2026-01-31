# Command Catalog (v0.8)

AgentOS Command Catalog - 组织常规操作的可治理目录

---

## 📖 概述

Command Catalog 定义了软件团队在完整开发生命周期（SDLC）中的 **40 条标准操作**。

**核心原则**：
- ✅ 只定义操作（输入/输出/风险/前置条件）
- ❌ 不提供执行入口（not executable）
- ❌ 不绑定 Agent 执行权（only recommend roles）
- ✅ 可追溯 lineage（演进历史）

**文档导航**：
- [README](commands/README.md) - 红线说明 + 使用指南
- [Schema](../../agentos/schemas/content/command.schema.json) - Command Schema 定义

---

## 🗂️ Commands 分类索引

### 1. Git / 变更管理 (8)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_git_create_branch` | Create Feature Branch | Low | FE, BE, DevOps |
| `cmd_git_sync_main_rebase` | Sync Main and Rebase | Medium | FE, BE |
| `cmd_git_commit_with_intent` | Commit with Intent | Low | FE, BE, DevOps |
| `cmd_git_create_pr` | Create Pull Request | Low | FE, BE, DevOps |
| `cmd_git_update_pr_description` | Update PR Description | Low | FE, BE, PM |
| `cmd_git_tag_release` | Tag Release | Medium | DevOps, EM |
| `cmd_git_revert_commit` | Revert Commit | Medium | FE, BE, DevOps |
| `cmd_git_cherry_pick` | Cherry-pick Commit | Medium | FE, BE |

**关联 Workflows**: `feature_implementation`, `code_review`, `refactoring`, `release_management`, `incident_response`, `maintenance_planning`

---

### 2. 需求/产品 (4)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_prd_create` | Create PRD | Low | PM |
| `cmd_prd_update_scope` | Update PRD Scope | Low | PM, PjM |
| `cmd_define_acceptance_criteria` | Define Acceptance Criteria | Low | PM, QA |
| `cmd_release_notes_draft` | Draft Release Notes | Low | PM, TW |

**关联 Workflows**: `requirements_definition`, `release_management`

---

### 3. 设计 (3)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_design_token_update` | Update Design Tokens | Medium | UX |
| `cmd_component_spec_create` | Create Component Spec | Low | UX |
| `cmd_design_review_checklist` | Run Design Review | Low | UX, FE |

**关联 Workflows**: `detailed_design`, `code_review`

---

### 4. 架构 (3)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_adr_create` | Create ADR | Low | Architect, EM |
| `cmd_architecture_review_checklist` | Run Architecture Review | Medium | Architect, SRE, Security |
| `cmd_dependency_audit` | Audit Dependencies | Medium | Architect, Security, DevOps |

**关联 Workflows**: `system_design`, `security_review`, `architectural_evolution`

---

### 5. 实现 (5)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_run_lint` | Run Lint Checks | Low | FE, BE |
| `cmd_run_typecheck` | Run Typecheck | Low | FE, BE |
| `cmd_run_unit_tests` | Run Unit Tests | Low | FE, BE, QA |
| `cmd_generate_api_client` | Generate API Client | Medium | FE, BE |
| `cmd_db_migration_create` | Create DB Migration | High | DBA, BE |

**关联 Workflows**: `feature_implementation`, `refactoring`, `test_implementation`, `detailed_design`, `deployment_planning`

---

### 6. 测试 (3)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_test_plan_create` | Create Test Plan | Low | QA, PM |
| `cmd_regression_suite_run` | Run Regression Suite | Medium | QA, DevOps |
| `cmd_test_report_generate` | Generate Test Report | Low | QA, TW |

**关联 Workflows**: `testing_strategy`, `test_implementation`, `release_management`

---

### 7. 安全 (3)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_security_scan_dependency` | Security Scan Dependencies | Medium | Security, DevOps |
| `cmd_secret_scan` | Secret Scan | High | Security, DevOps |
| `cmd_threat_model_template` | Create Threat Model | Medium | Security, Architect |

**关联 Workflows**: `security_review`

---

### 8. 部署/运行 (6)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_build_artifact` | Build Artifact | Low | DevOps |
| `cmd_deploy_staging` | Deploy to Staging | Medium | DevOps, SRE |
| `cmd_deploy_production` | Deploy to Production | High | DevOps, SRE, EM |
| `cmd_rollback_release` | Rollback Release | High | SRE, DevOps |
| `cmd_health_check` | Run Health Check | Low | SRE, DevOps |
| `cmd_observability_dashboard_check` | Observability Dashboard Check | Medium | SRE |

**关联 Workflows**: `deployment_planning`, `release_management`, `incident_response`, `performance_analysis`

---

### 9. 事故响应 (3)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_incident_create_ticket` | Create Incident Ticket | Medium | SRE, DevOps, PjM |
| `cmd_incident_collect_logs` | Collect Incident Logs | High | SRE, DevOps |
| `cmd_incident_postmortem` | Write Incident Postmortem | Low | SRE, EM, TW |

**关联 Workflows**: `incident_response`, `knowledge_consolidation`

---

### 10. 文档 (2)

| Command ID | Title | Risk | Roles |
|-----------|-------|------|-------|
| `cmd_docs_update_index` | Update Documentation Index | Low | TW, EM |
| `cmd_docs_publish` | Publish Documentation | Medium | TW, DevOps |

**关联 Workflows**: `knowledge_consolidation`, `release_management`

---

## 📊 统计总览

### 按 Category 聚合

| Category | Commands | Risk (L/M/H) |
|----------|----------|--------------|
| Git | 8 | 4 / 3 / 0 |
| Product | 4 | 4 / 0 / 0 |
| Design | 3 | 2 / 1 / 0 |
| Architecture | 3 | 1 / 2 / 0 |
| Engineering | 5 | 3 / 1 / 1 |
| Quality | 3 | 1 / 1 / 0 |
| Security | 3 | 0 / 2 / 1 |
| Operations | 6 | 1 / 2 / 2 |
| Incident | 3 | 1 / 1 / 1 |
| Documentation | 2 | 1 / 1 / 0 |
| **总计** | **40** | **18 / 14 / 5** |

### 按 Risk Level 聚合

- **Low (18)**: 基础操作，影响范围小，可快速回滚
- **Medium (14)**: 中等影响，需要验证和测试
- **High (5)**: 高风险操作，需要审批和证据

**High Risk Commands**:
1. `cmd_db_migration_create` (数据变更)
2. `cmd_secret_scan` (安全扫描)
3. `cmd_deploy_production` (生产部署)
4. `cmd_rollback_release` (生产回滚)
5. `cmd_incident_collect_logs` (事故日志收集)

### 按 Effects 聚合

| Effect Kind | Count |
|-------------|-------|
| Write | 32 |
| Read | 5 |
| Network | 3 |

### 角色缩写

- **PM** = Product Manager
- **PjM** = Project Manager
- **UX** = UI/UX Designer
- **FE** = Frontend Engineer
- **BE** = Backend Engineer
- **DBA** = Database Engineer
- **Architect** = System Architect
- **QA** = QA Engineer
- **Security** = Security Engineer
- **DevOps** = DevOps Engineer
- **SRE** = SRE Engineer
- **TW** = Technical Writer
- **EM** = Engineering Manager

---

## 🔗 与 Workflows / Agents 的连接

### Command → Workflow 映射

每个 Command 通过 `workflow_links` 声明在哪些 Workflow phases 中常用：

```yaml
workflow_links:
  - workflow: feature_implementation
    phases: [setup, commit]
```

**查询示例**：
```bash
# 查看某个 Workflow 推荐的 Commands
uv run agentos content explain feature_implementation
# 输出包含: Recommended Commands by Phase
```

### Command → Agent 映射

每个 Command 通过 `recommended_roles` 推荐哪些 Agent 角色常用：

```yaml
recommended_roles:
  - frontend_engineer
  - backend_engineer
```

**注意**：这只是"推荐"，不是"绑定"。v0.8 不涉及执行逻辑。

---

## 🚨 红线提醒

Command Catalog 遵循 4 条红线（详见 [README](commands/README.md)）：

1. **C1**: Command ≠ 可执行脚本（禁止 shell/bash/python code）
2. **C2**: Command 不能绑定 Agent 执行（只推荐角色）
3. **C3**: Command 必须声明副作用与风险（effects/risk_level/evidence_required）
4. **C4**: Command 必须可追溯 lineage（introduced_in/derived_from/supersedes）

**所有 Commands 在注册前都会进行红线验证**。

---

## 🛠️ 使用指南

### 查看 Command 详情

```bash
# 查看单个 Command
uv run agentos content explain cmd_git_create_branch

# 按 category 列出
uv run agentos content list --type command --category git

# 搜索
uv run agentos content search "deploy"
```

### 注册 Commands

```bash
# 1. 验证 YAML 文件（Schema + 红线）
uv run python scripts/convert_commands.py --validate

# 2. 注册到数据库
uv run python scripts/register_commands.py --auto-activate

# 3. 验证注册成功
uv run agentos content list --type command
```

### 查看统计

```bash
# 查看 Catalog 统计报告
uv run agentos content catalog-summary
```

---

## 📚 参考文档

- [Command README](commands/README.md) - 红线说明 + 使用指南
- [Command Schema](../../agentos/schemas/content/command.schema.json) - Schema 定义
- [Workflow Catalog](workflow-catalog.md) - Workflow 定义
- [Agent Catalog](agent-catalog.md) - Agent 定义
- [v0.8 实施报告](../../V08_IMPLEMENTATION_COMPLETE.md) - v0.8 交付详情

---

**最后更新**: 2026-01-25  
**版本**: 0.8.0  
**Commands 总数**: 40  
**状态**: ✅ ACTIVE
