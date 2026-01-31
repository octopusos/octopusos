# AgentOS 文档管理政策

**版本**: 1.0  
**生效日期**: 2026-01-26  
**状态**: 🔴 强制执行

## 核心原则

### 红线规则（RED LINE）

1. **所有项目文档必须且只能存放在 `docs/` 的子目录中**
2. **`docs/` 根目录禁止存放文档**（仅允许 `index.md`）
3. **禁止在项目根目录创建任何 .md 文档**（除了 `README.md` 和 `DOCS_POLICY.md`）
4. **禁止在代码目录（`agentos/`、`tests/`、`scripts/` 等）创建项目级文档**

## 文档分类体系

### 1. `docs/reports/` - 报告文档

**用途**: 实现报告、验证报告、修复报告

**子分类**:
- `versions/` - 版本实现报告（V02_*.md, V03_*.md 等）
- `features/` - 功能特性报告（TUI_*.md, HOME_SCREEN_*.md 等）
- `tasks/` - 任务驱动报告（TASK_DRIVEN_*.md）
- `gates/` - Gate 验证报告
- `fixes/` - Bug 修复报告

**命名规范**:
- `FEATURE_IMPLEMENTATION_REPORT.md` - 功能实现报告
- `FEATURE_VERIFICATION_REPORT.md` - 功能验证报告
- `FEATURE_FIX_REPORT.md` - 功能修复报告

### 2. `docs/guides/` - 指南文档

**用途**: 用户指南、开发指南、操作指南

**子分类**:
- `user/` - 用户使用指南
- `developer/` - 开发者指南
- `operations/` - 运维操作指南

**命名规范**:
- `FEATURE_USER_GUIDE.md` - 用户指南
- `FEATURE_DEVELOPER_GUIDE.md` - 开发指南
- `QUICKSTART.md` - 快速开始

### 3. `docs/architecture/` - 架构文档

**用途**: 系统架构、设计决策、组件设计

**子分类**:
- `decisions/` - 架构决策记录（ADR）
- `diagrams/` - 架构图
- `components/` - 组件设计

**命名规范**:
- `COMPONENT_ARCHITECTURE.md` - 组件架构
- `SYSTEM_DESIGN.md` - 系统设计

### 4. `docs/deliverables/` - 交付文档

**用途**: 阶段交付、完成总结、Closeout 文档

**子分类**:
- `phases/` - 阶段交付文档
- `closeouts/` - Closeout 文档
- `summaries/` - 完成总结

**命名规范**:
- `PHASE_X_CLOSEOUT.md` - 阶段关闭文档
- `FEATURE_COMPLETE.md` - 功能完成文档
- `PROJECT_SUMMARY.md` - 项目总结

### 5. `docs/project/` - 项目管理文档

**用途**: 项目状态、进度跟踪、规划文档

**命名规范**:
- `PROJECT_STATUS.md` - 项目状态
- `PROJECT_PROGRESS.md` - 项目进度
- `PROJECT_PLAN.md` - 项目规划

### 6. `docs/configuration/` - 配置文档

**用途**: 配置说明、策略文档、规范文档

**命名规范**:
- `CONFIGURATION_GUIDE.md` - 配置指南
- `POLICY_*.md` - 策略文档

### 7. `docs/runbooks/` - 运维手册

**用途**: 运维脚本说明、操作手册

**命名规范**:
- `OPERATION_RUNBOOK.md` - 运维手册
- `SCRIPT_USAGE.md` - 脚本使用说明

## 文档创建流程

### 步骤 1: 确定文档类型

根据文档内容，选择合适的分类：

```
报告类 → docs/reports/
指南类 → docs/guides/
架构类 → docs/architecture/
交付类 → docs/deliverables/
项目类 → docs/project/
配置类 → docs/configuration/
运维类 → docs/runbooks/
```

### 步骤 2: 选择子目录

在对应的分类下，选择或创建合适的子目录。

### 步骤 3: 创建文档

在正确的子目录中创建文档，使用规范的命名格式。

### 步骤 4: 更新索引

更新该子目录的 `index.md` 文件，添加新文档的链接和简要说明。

## 索引管理

### docs/index.md（必须维护）

每个 `docs` 子目录必须包含 `index.md`，提供：
- 目录概述
- 文档列表
- 文档简要说明
- 相关链接

### 示例结构

```
docs/
├── index.md                          # 总索引
├── reports/
│   ├── index.md                      # 报告索引
│   ├── versions/
│   │   ├── index.md
│   │   ├── V02_IMPLEMENTATION_COMPLETE.md
│   │   └── V03_FINAL_REPORT.md
│   ├── features/
│   │   ├── index.md
│   │   ├── TUI_IMPLEMENTATION_REPORT.md
│   │   └── HOME_SCREEN_REPORT.md
│   └── tasks/
│       └── index.md
├── guides/
│   ├── index.md
│   ├── user/
│   │   └── index.md
│   └── developer/
│       └── index.md
├── architecture/
│   └── index.md
└── project/
    └── index.md
```

## 禁止行为（RED LINE）

### ❌ 禁止 1: 根目录文档

```bash
# 错误示例
/PROJECT_STATUS.md          # ❌ 禁止
/IMPLEMENTATION_REPORT.md   # ❌ 禁止
/USER_GUIDE.md              # ❌ 禁止

# 正确示例
/docs/project/PROJECT_STATUS.md           # ✅ 正确
/docs/reports/IMPLEMENTATION_REPORT.md    # ✅ 正确
/docs/guides/user/USER_GUIDE.md           # ✅ 正确
```

### ❌ 禁止 2: docs 根目录文档

```bash
# 错误示例
/docs/SOME_REPORT.md        # ❌ 禁止

# 正确示例
/docs/reports/SOME_REPORT.md              # ✅ 正确
```

### ❌ 禁止 3: 代码目录项目文档

```bash
# 错误示例
/agentos/ARCHITECTURE.md    # ❌ 禁止
/scripts/USAGE_GUIDE.md     # ❌ 禁止

# 正确示例
/docs/architecture/AGENTOS_ARCHITECTURE.md  # ✅ 正确
/docs/guides/SCRIPTS_USAGE_GUIDE.md         # ✅ 正确
```

### ✅ 允许例外

以下文档可以在特定目录：

1. **模块级 README.md**: 代码模块可以有 `README.md` 说明模块功能
   - `/agentos/core/README.md` ✅
   - `/agentos/i18n/README.md` ✅

2. **根目录必需文档**: 只允许以下文档
   - `/README.md` ✅
   - `/DOCS_POLICY.md` ✅
   - `/LICENSE` ✅

## 文档迁移规则

### 迁移旧文档

如果发现根目录或不当位置的文档：

1. 确定文档类型和正确位置
2. 移动到正确的 docs 子目录
3. 更新相关索引
4. 检查是否有引用该文档的链接，更新链接

### 迁移脚本

```bash
# 检查根目录的 md 文件（除允许的例外）
find . -maxdepth 1 -name "*.md" ! -name "README.md" ! -name "DOCS_POLICY.md"

# 检查 docs 根目录的 md 文件（除 index.md）
find ./docs -maxdepth 1 -name "*.md" ! -name "index.md"
```

## AI Agent 规则

### AI Agent 必须遵守

在处理任何 .md 文件任务前：

1. **必须先阅读** `/DOCS_POLICY.md`
2. **必须检查**文档类型和正确位置
3. **必须遵守**文档分类和命名规范
4. **禁止**在根目录或不当位置创建文档
5. **必须更新**相关的 index.md

### 检查清单

```
[ ] 已阅读 DOCS_POLICY.md
[ ] 确定了文档类型（7 选 1）
[ ] 选择了正确的子目录
[ ] 使用了规范的命名
[ ] 更新了相关 index.md
[ ] 没有在禁止位置创建文档
```

## 演进规则

### 允许的变更

- 添加新的文档子分类
- 优化命名规范
- 改进索引结构

### 需要审批的变更

- 修改核心分类体系（7 大分类）
- 修改红线规则
- 大规模重构文档结构

### 禁止的变更

- 放宽红线规则
- 允许根目录文档
- 绕过分类体系

## 维护责任

- **文档创建者**: 负责放在正确位置，更新索引
- **Code Review**: 检查文档位置是否符合政策
- **CI 检查**: 自动检查根目录和 docs 根目录的非法文档

## 参考

- 文档分类灵感来自 [C4 Model](https://c4model.com/)
- 命名规范参考 [Conventional Commits](https://www.conventionalcommits.org/)

---

**最后更新**: 2026-01-26  
**维护**: AgentOS 团队  
**状态**: 🔴 强制执行
