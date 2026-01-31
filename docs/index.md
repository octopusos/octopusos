# AgentOS 文档索引

欢迎来到 AgentOS 项目文档中心。本索引提供了项目所有文档的导航。

## 📋 文档政策

在阅读或创建文档前，请先阅读：
- [文档管理政策 (DOCS_POLICY.md)](../DOCS_POLICY.md)

## 📁 文档分类

### 1. 📊 报告文档 (reports/)

实现报告、验证报告、修复报告

- [版本报告 (versions/)](./reports/versions/index.md) - V02-V12 版本实现和验证报告
- [功能报告 (features/)](./reports/features/index.md) - TUI、Home Screen、I18N 等功能报告
- [任务报告 (tasks/)](./reports/tasks/index.md) - Task-Driven 任务实现报告
- [修复报告 (fixes/)](./reports/fixes/index.md) - Bug 修复和问题解决报告
- [Gate 报告 (gates/)](./reports/gates/index.md) - Gate 验证和测试报告

### 2. 📖 指南文档 (guides/)

用户指南、开发指南、操作指南

- [用户指南 (user/)](./guides/user/index.md) - 终端用户使用指南
- [开发者指南 (developer/)](./guides/developer/index.md) - 开发者文档和最佳实践
- [运维指南 (operations/)](./guides/operations/index.md) - 运维操作和维护指南

### 3. 🏗️ 架构文档 (architecture/)

系统架构、设计决策、组件设计

- [架构概览](./ARCHITECTURE_DIAGRAMS.md)
- [架构风险](./ARCHITECTURE_RISKS.md)
- [架构决策记录 (adr/)](./adr/)
- [架构铁律](./ARCHITECTURE_IRON_LAWS.md)

### 4. 📦 交付文档 (deliverables/)

阶段交付、完成总结、Closeout 文档

- [阶段交付 (phases/)](./deliverables/phases/index.md)
- [Closeout 文档 (closeouts/)](./deliverables/closeouts/index.md)
- [完成总结 (summaries/)](./deliverables/summaries/index.md)

### 5. 📋 项目管理 (project/)

项目状态、进度跟踪、规划文档

- [项目状态](./project/PROJECT_STATUS.md)
- [项目总结](./project/PROJECT_SUMMARY.md)
- [项目进度](./project/P0_PROGRESS.md)

### 6. ⚙️ 配置文档 (configuration/)

配置说明、策略文档、规范文档

- [Open Plan 架构](./OPEN_PLAN_ARCHITECTURE.md)
- [Open Plan 实现总结](./OPEN_PLAN_IMPLEMENTATION_SUMMARY.md)
- [Open Plan README](./OPEN_PLAN_README.md)
- [Open Plan 主权](./OPEN_PLAN_SOVEREIGNTY.md)

### 7. 📘 运维手册 (runbooks/)

运维脚本说明、操作手册

（待添加内容）

### 8. 🚀 专项文档

#### CLI 文档 (cli/)
- [CLI 架构](./cli/CLI_ARCHITECTURE.md)
- [CLI 实现总结](./cli/CLI_IMPLEMENTATION_SUMMARY.md)
- [更多 CLI 文档...](./cli/)

#### 协调器文档 (coordinator/)
- [协调器 README](./coordinator/README.md)
- [Red Line 强制执行](./coordinator/RED_LINE_ENFORCEMENT.md)

#### 执行器文档 (executor/)
- [执行器 README](./executor/README.md)
- [创作指南](./executor/AUTHORING_GUIDE.md)

#### 评估器文档 (evaluator/)
- [评估器相关文档](./evaluator/)

#### 流水线文档 (pipeline/)
- [流水线 README](./pipeline/README.md)
- [流水线 Runbook](./pipeline/RUNBOOK.md)

#### Demo 文档 (demo/)
- [Demo Landing Runbook](./demo/DEMO_LANDING_RUNBOOK.md)
- [更多 Demo 文档...](./demo/)

## 📚 核心文档

### 白皮书与理论
- [白皮书 V1](./WHITEPAPER_V1.md)
- [为什么 Agent 会失败](./WHY_AGENTS_FAIL.md)
- [V02 不变量](./V02_INVARIANTS.md)

### 发布与演示
- [发布指南](./RELEASE_GUIDE.md)
- [演示脚本](./DEMO_SCRIPT.md)
- [交付检查清单](./DELIVERY_CHECKLIST.md)

### 数据库迁移
- [数据库迁移快速入门](./DATABASE_MIGRATION_QUICKSTART.md)
- [迁移错误处理增强](./MIGRATION_ERROR_HANDLING_ENHANCEMENT.md)

### 其他
- [Python 兼容性修复](./PYTHON_COMPATIBILITY_FIX.md)
- [模型管理指南](./MODEL_MANAGEMENT_GUIDE.md)
- [命令系统实现](./COMMAND_SYSTEM_IMPLEMENTATION.md)
- [TUI 实现报告](./TUI_IMPLEMENTATION_REPORT.md)
- [TUI 开发](./TUI_DEVELOPMENT.md)
- [TUI 用户指南](./TUI_USER_GUIDE.md)
- [Home Screen 增强](./HOME_SCREEN_ENHANCEMENTS.md)
- [Home Screen 用户指南](./HOME_SCREEN_USER_GUIDE.md)

## 🔍 文档导航提示

### 按需求类型查找

- **我想了解如何使用**: → [guides/user/](./guides/user/index.md)
- **我想了解如何开发**: → [guides/developer/](./guides/developer/index.md)
- **我想了解架构设计**: → [architecture/](./ARCHITECTURE_DIAGRAMS.md)
- **我想查看项目进度**: → [project/](./project/PROJECT_STATUS.md)
- **我想查看实现报告**: → [reports/](./reports/versions/index.md)
- **我想查看某个版本**: → [reports/versions/](./reports/versions/index.md)
- **我想查看某个功能**: → [reports/features/](./reports/features/index.md)

### 按角色查找

- **终端用户**: [guides/user/](./guides/user/index.md)
- **开发者**: [guides/developer/](./guides/developer/index.md)
- **运维人员**: [guides/operations/](./guides/operations/index.md)
- **架构师**: [architecture/](./ARCHITECTURE_DIAGRAMS.md)
- **项目经理**: [project/](./project/PROJECT_STATUS.md)

## 📝 贡献文档

创建新文档时，请遵循 [文档管理政策](../DOCS_POLICY.md)：

1. 确定文档类型（报告/指南/架构/交付/项目/配置/运维）
2. 选择正确的子目录
3. 使用规范的命名格式
4. 更新相应的 index.md
5. 禁止在根目录或 docs 根目录创建文档

## 🔗 外部资源

- [项目 README](../README.md)
- [GitHub 仓库](https://github.com/your-org/agentos)（如适用）

---

**最后更新**: 2026-01-26  
**维护**: AgentOS 团队
