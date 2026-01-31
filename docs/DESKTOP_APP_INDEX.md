# AgentOS Desktop 项目文档索引

> **项目代号**: AgentOS Desktop
> **版本**: 1.0
> **创建日期**: 2026-01-30
> **状态**: 设计阶段 → 待启动

---

## 📚 文档导航图

```
DESKTOP_APP_INDEX.md (你在这里)
├── 快速入门 ⚡
│   └── DESKTOP_APP_QUICK_START.md ★ 推荐从这里开始
│
├── 完整方案 📋
│   └── architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md
│       ├── 第 1 节：执行概要
│       ├── 第 2 节：总体架构
│       ├── 第 3 节：技术选型
│       ├── 第 4-9 节：Phase 0-6 实施计划
│       ├── 第 10 节：关键风险
│       └── 第 11 节：成功标准
│
├── 技术决策 🔍
│   └── architecture/ADR_001_DESKTOP_APP_TECH_STACK.md
│       ├── 为什么选 Tauri
│       ├── 为什么选 Nuitka
│       ├── 为什么更新要重启生效
│       └── 风险与权衡
│
├── 详细设计 🛠️
│   └── architecture/UPDATE_MECHANISM_DESIGN.md
│       ├── 更新流程（5 个阶段）
│       ├── Updater Helper 实现
│       ├── 失败场景与恢复
│       └── 代码示例（Rust）
│
└── 任务清单 ✅
    └── tasks/DESKTOP_APP_TASK_BREAKDOWN.md
        ├── 137 个具体任务
        ├── 按 Phase 组织
        ├── 工时估算与依赖
        └── 人员分配建议
```

---

## 🚀 如何使用这些文档

### 第一次阅读？

1. **先看这个** → [快速启动指南](./DESKTOP_APP_QUICK_START.md)（5 分钟）
2. 根据你的角色，选择对应的深入阅读

### 按角色导航

#### 👔 决策者 / 产品经理

**你需要回答的问题**：
- 这个项目值得做吗？
- 需要多少资源？
- 风险是什么？

**阅读路径**：
1. [快速指南 - 一句话概括](./DESKTOP_APP_QUICK_START.md#-一句话概括)
2. [实施方案 - 执行概要](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-执行概要)
3. [实施方案 - 成功标准](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-成功标准验收标准)
4. [实施方案 - 关键风险](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-关键风险与缓解措施)
5. [任务清单 - 里程碑](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#里程碑与交付)

**关键数据**：
- **工期**: 16-20 周（4-5 个月）
- **团队**: 建议 11 人（最少 5 人）
- **成本**: 约 120-165 人天
- **交付**: macOS/Windows 桌面应用 + 自动更新

---

#### 🏗️ 技术负责人 / 架构师

**你需要回答的问题**：
- 技术选型合理吗？
- 架构是否可扩展？
- 有哪些技术债务？

**阅读路径**：
1. [快速指南 - 技术视角](./DESKTOP_APP_QUICK_START.md#技术视角)
2. [技术决策记录 (ADR)](./architecture/ADR_001_DESKTOP_APP_TECH_STACK.md) ★ 重点
3. [实施方案 - 总体架构](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-总体架构)
4. [更新机制设计](./architecture/UPDATE_MECHANISM_DESIGN.md)
5. [任务清单 - 风险](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#风险与缓解)

**关键决策**：
- **Desktop Framework**: Tauri 2.x（vs Electron）
- **Python 打包**: Nuitka（vs PyInstaller）
- **更新策略**: 重启生效（vs In-place）
- **Sidecar 管理**: 内置 AgentOS + Ollama

---

#### 💻 开发者 / 工程师

**你需要知道的**：
- 我负责哪些任务？
- 技术栈是什么？
- 如何搭建环境？

**阅读路径**：
1. [快速指南 - 如何开始](./DESKTOP_APP_QUICK_START.md#-如何开始)
2. [任务清单 - 你的 Phase](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md)
3. [实施方案 - 对应 Phase 详细说明](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md)
4. （如有疑问）[技术决策 ADR](./architecture/ADR_001_DESKTOP_APP_TECH_STACK.md)

**你的任务在哪**：
- **前端** → Phase 1.3, Phase 4.4, Phase 5, Phase 6.6
- **Rust 后端** → Phase 1.1-1.4, Phase 3
- **Python 后端** → Phase 2
- **DevOps** → Phase 6

**环境准备**：
```bash
# Rust 工具链
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Tauri CLI
cargo install tauri-cli

# Node.js (前端)
nvm install 20
npm install -g pnpm

# Python 3.13 (Runtime 打包)
brew install python@3.13  # macOS
```

---

#### 🚀 DevOps / 发布工程师

**你需要知道的**：
- CI/CD 如何配置？
- 如何签名和公证？
- 如何分发更新？

**阅读路径**：
1. [任务清单 - Phase 6](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#phase-6-打包与签名4-周)
2. [更新机制 - Manifest 设计](./architecture/UPDATE_MECHANISM_DESIGN.md#1-update-manifest远端)
3. [实施方案 - Phase 6 详细](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#phase-6-跨平台打包与签名3-4-周)

**关键任务**：
- **P6.1**: macOS 签名与公证
- **P6.2**: Windows Authenticode 签名
- **P6.3**: CI/CD Pipeline（GitHub Actions）
- **P6.4**: CDN 配置（Cloudflare R2）

**需要的证书**：
- Apple Developer ID Application（macOS）
- Windows Authenticode Certificate（Windows）

---

#### 🧪 QA / 测试工程师

**你需要知道的**：
- 测试什么？
- 验收标准是什么？
- 如何自动化？

**阅读路径**：
1. [实施方案 - 成功标准](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-成功标准验收标准)
2. [任务清单 - 测试任务](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#测试任务贯穿所有阶段)
3. [更新机制 - 测试策略](./architecture/UPDATE_MECHANISM_DESIGN.md#测试策略)

**测试覆盖**：
- **单元测试**: 25 个任务（T1-T5）
- **集成测试**: 3 个任务（T6-T8）
- **E2E 测试**: 3 个平台（T9-T11）

**关键场景**：
- 首次启动流程（3 步）
- 模型下载进度
- 更新完整流程（下载 → 重启 → 验证）
- 失败回滚

---

#### ✍️ 技术写作 / 文档工程师

**你需要写的**：
- 用户文档（4 份）
- 技术文档（4 份）
- 视频教程（2 份）

**阅读路径**：
1. [任务清单 - 文档任务](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#文档任务)
2. [实施方案 - 可交付物](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-可交付物清单)

**待完成文档**：
- [ ] D1: 安装指南
- [ ] D2: 故障排除手册
- [ ] D3: 模型许可证 FAQ
- [ ] D4: 更新 FAQ
- [ ] D5: API 文档（IPC）
- [ ] D8-D9: 视频教程（安装 + FTU）

---

## 📂 完整文档清单

### ✅ 已完成

| 文档 | 路径 | 大小 | 用途 |
|------|------|------|------|
| **快速启动** | [DESKTOP_APP_QUICK_START.md](./DESKTOP_APP_QUICK_START.md) | ~15 KB | 5 分钟快速理解 |
| **实施方案** | [architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md) | ~75 KB | 完整分阶段计划 |
| **技术决策** | [architecture/ADR_001_DESKTOP_APP_TECH_STACK.md](./architecture/ADR_001_DESKTOP_APP_TECH_STACK.md) | ~12 KB | 技术选型理由 |
| **更新机制** | [architecture/UPDATE_MECHANISM_DESIGN.md](./architecture/UPDATE_MECHANISM_DESIGN.md) | ~35 KB | 更新流程详细设计 |
| **任务清单** | [tasks/DESKTOP_APP_TASK_BREAKDOWN.md](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md) | ~25 KB | 137 个具体任务 |

### ⏳ 待完成（Phase 0）

| 文档 | 负责人 | 截止日期 | 用途 |
|------|-------|---------|------|
| `DIRECTORY_STRUCTURE.md` | 架构师 | Week 1 | 目录结构冻结 |
| `VERSION_PROTOCOL.md` | 架构师 | Week 1 | 版本管理协议 |
| `UPDATE_BOUNDARIES.md` | 架构师 | Week 1 | 更新边界声明 |
| `SIDECAR_LIFECYCLE.md` | 后端 | Week 3 | Sidecar 生命周期 |

### 📝 待完成（用户文档）

| 文档 | 负责人 | 时机 | 用途 |
|------|-------|------|------|
| `INSTALLATION_GUIDE.md` | 技术写作 | Week 18 | 用户安装指南 |
| `TROUBLESHOOTING.md` | 技术写作 | Week 19 | 故障排除 |
| `MODEL_LICENSE_FAQ.md` | 法务 + 技术写作 | Week 16 | 模型许可证 FAQ |
| `UPDATE_FAQ.md` | 技术写作 | Week 19 | 更新常见问题 |

---

## 🎯 关键里程碑

| 里程碑 | 日期（相对） | 关键产出 | Go/No-Go 标准 |
|--------|------------|---------|--------------|
| **M0: 文档完成** | Week 0 | ✅ 本索引 + 5 份文档 | 团队理解方案 |
| **M1: 基础设施** | Week 2 | 架构文档 + 骨架代码 | 文档签字确认 |
| **M2: Sidecar 可用** | Week 5 | 两个 sidecar 正常运行 | 健康检查通过 |
| **M3: Runtime 打包** | Week 8 | 3 平台可执行文件 | 独立启动成功 |
| **M4: 更新机制** | Week 12 | 端到端更新成功 | 3 平台测试通过 |
| **M5: 模型管理** | Week 15 | 可下载模型 | 进度实时显示 |
| **M6: FTU 完成** | Week 17 | 3 步完成配置 | 用户测试通过 |
| **M7: Beta 发布** | Week 20 | 可分发安装包 | 10 用户 0 P0 bug |

---

## 📊 项目统计

### 工作量

- **总任务数**: 137 个
- **总工时**: 120-165 人天
- **工期**: 16-20 周
- **建议团队**: 11 人

### 文档

- **已完成**: 5 份（~162 KB）
- **待完成**: 8 份（技术文档）+ 4 份（用户文档）
- **总文档量**: 预计 ~300 KB

### 代码

- **新仓库**: `agentos-desktop`
- **主要语言**: Rust (Tauri), TypeScript (React), Python (Runtime)
- **预计代码量**: ~15,000 行

---

## 🔄 文档更新流程

### 如何更新文档

1. **修改文档**: 直接编辑对应 Markdown 文件
2. **更新索引**: 如果新增文档，更新本索引
3. **提交 PR**: 包含变更说明
4. **评审**: 至少 1 个 reviewer 批准

### 版本控制

- **主版本**: 重大架构变更（如替换技术栈）
- **次版本**: 增加新阶段或模块
- **修订版本**: 修正错误或补充细节

**当前版本**: 1.0（初始设计）

---

## 💡 使用建议

### 打印版本

推荐打印以下文档用于会议讨论：
- ✅ 快速启动指南（10 页）
- ✅ 技术决策记录（8 页）
- ⚠️ 实施方案（太长，选择性打印）

### 在线协作

- **架构评审**: 使用 Figma/Miro 将架构图可视化
- **任务跟踪**: 导入任务清单到 Jira/Linear
- **进度同步**: 每周更新 README 的里程碑状态

### 搜索技巧

所有文档支持关键词搜索：
```
Sidecar        → 找生命周期管理相关
Update         → 找更新机制相关
Phase 3        → 找第 3 阶段任务
DoD            → 找验收标准
Risk           → 找风险相关
```

---

## 🤝 贡献指南

### 反馈问题

- **技术问题**: 在对应文档提 Issue
- **任务问题**: 在任务清单中标注
- **流程问题**: 联系项目经理

### 提出改进

1. Fork 文档仓库
2. 创建分支（如 `improve-update-mechanism`）
3. 提交 PR，说明改进理由
4. 等待评审

---

## 📞 联系方式

### 项目团队（待建立）

- **项目发起人**: TBD
- **技术负责人**: TBD
- **产品经理**: TBD

### 沟通渠道

- **文档问题**: GitHub Issues
- **技术讨论**: [Discord/Slack TBD]
- **任务管理**: [Jira/Linear TBD]

---

## 🎉 下一步行动

### 如果你是项目负责人

1. [ ] 召开 Kickoff 会议，过一遍快速启动指南
2. [ ] 建立项目团队，分配角色
3. [ ] 配置项目管理工具（Jira/Linear）
4. [ ] 创建 `agentos-desktop` 仓库
5. [ ] 启动 Phase 0

### 如果你是团队成员

1. [ ] 阅读快速启动指南
2. [ ] 阅读你角色对应的深入文档
3. [ ] 准备开发环境
4. [ ] 等待任务分配

---

## 📚 扩展阅读

### 相关技术文档

- [Tauri 官方文档](https://tauri.app/v2/guide/)
- [Nuitka 用户手册](https://nuitka.net/doc/user-manual.html)
- [Ollama API 文档](https://github.com/ollama/ollama/blob/main/docs/api.md)

### 参考项目

- [Cursor](https://cursor.sh/) - 类似的桌面应用形态
- [Electron Forge](https://www.electronforge.io/) - 桌面应用打包
- [Sparkle Framework](https://sparkle-project.org/) - macOS 更新机制

---

**索引版本**: 1.0
**最后更新**: 2026-01-30
**维护者**: Claude (Anthropic)

---

祝项目成功！🚀

如有疑问，请从[快速启动指南](./DESKTOP_APP_QUICK_START.md)开始。
