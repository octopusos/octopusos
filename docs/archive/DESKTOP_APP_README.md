# AgentOS Desktop 桌面应用实施方案

> **状态**: 📝 设计完成，待启动
> **版本**: 1.0
> **日期**: 2026-01-30

---

## 🎯 这是什么

将 AgentOS 从"需要配置 Python 环境的开发工具"升级为**"开箱即用的桌面应用"**（像 VS Code、Cursor 那样）。

### 用户体验目标

```
安装 → 3 步配置 → 开始对话
────────────────────────────
  5 分钟内完成
```

---

## 📚 快速导航

| 我想... | 看这个 |
|--------|--------|
| **5 分钟了解整个项目** | [快速启动指南](./docs/DESKTOP_APP_QUICK_START.md) ⚡ |
| **查看所有文档** | [文档索引](./docs/DESKTOP_APP_INDEX.md) 📋 |
| **了解技术选型理由** | [技术决策记录 ADR](./docs/architecture/ADR_001_DESKTOP_APP_TECH_STACK.md) 🔍 |
| **看完整实施计划** | [实施方案](./docs/architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md) 📖 |
| **找我的开发任务** | [任务清单](./docs/tasks/DESKTOP_APP_TASK_BREAKDOWN.md) ✅ |

---

## 🚀 核心特性

### 对用户

- ✅ **真正开箱即用**：无需安装 Python、Ollama，一键启动
- ✅ **模型可视化管理**：应用内下载模型，实时进度条
- ✅ **自动更新**：重启后自动应用新版本，无感知升级
- ✅ **简化界面**：专注聊天，高级功能通过"Open WebUI"访问

### 对开发者

- ✅ **技术栈现代化**：Tauri + Rust + React
- ✅ **架构清晰**：Sidecar 模式，组件解耦
- ✅ **可维护性高**：组件级更新，失败可回滚
- ✅ **跨平台**：macOS (Intel/ARM) + Windows 一次构建

---

## 📊 项目概况

| 维度 | 数据 |
|------|------|
| **工期** | 16-20 周（4-5 个月）|
| **团队** | 建议 11 人，最少 5 人 |
| **总任务** | 137 个 |
| **总工时** | 120-165 人天 |
| **代码量** | 预计 ~15,000 行 |
| **文档** | 5 份已完成（~162 KB），12 份待编写 |

---

## 🏗️ 架构一览

```
┌─────────────────────────────────────┐
│     Tauri Desktop Shell             │
│  ┌───────────────────────────────┐  │
│  │   Chat UI (React)             │  │
│  │   + Open WebUI Button         │  │
│  └───────────────────────────────┘  │
│              ↕ IPC                  │
│  ┌─────────────┐  ┌──────────────┐ │
│  │ AgentOS     │  │ Ollama       │ │
│  │ Runtime     │  │ Server       │ │
│  │ (Sidecar)   │  │ (Sidecar)    │ │
│  └─────────────┘  └──────────────┘ │
└─────────────────────────────────────┘
           ↓
   ~/.agentos/
   ├── models/   (AI 模型)
   ├── config/   (用户配置)
   └── logs/     (运行日志)
```

---

## 🛠️ 技术栈

| 组件 | 技术选型 | 理由 |
|------|---------|------|
| Desktop Shell | **Tauri 2.x** | 包体积小 90%，原生 sidecar 支持 |
| 前端 | **React + Vite** | 复用现有 WebUI，团队熟悉 |
| Runtime 打包 | **Nuitka** | 真正编译，性能提升 10-15% |
| Ollama | **官方二进制** | MIT 许可证，可随包分发 |
| 更新机制 | **重启生效** | 最稳定，避免平台差异 |

详细对比见 → [技术决策记录 ADR](./docs/architecture/ADR_001_DESKTOP_APP_TECH_STACK.md)

---

## 📅 时间线

```
Phase 0 (Week 1-2)  : 基础设施（目录、版本协议）
Phase 1 (Week 2-5)  : Sidecar 管理（启动、监控、日志）
Phase 2 (Week 5-8)  : Runtime 打包（Nuitka 配置、跨平台）
Phase 3 (Week 8-12) : 热更新（下载、校验、重启生效）★ 最复杂
Phase 4 (Week 12-15): 模型管理（下载进度、许可证确认）
Phase 5 (Week 15-17): 首次启动（FTU 3 步流程）
Phase 6 (Week 17-20): 打包签名（macOS 公证、Windows 签名）
```

---

## ✅ 验收标准

### 核心体验

- [ ] macOS 拖拽安装，Windows 双击安装，< 2 分钟
- [ ] 首次启动 3 步内完成配置
- [ ] 聊天首次响应 < 5 秒
- [ ] 更新检测到重启，用户无感知

### 性能

- [ ] App 启动 < 3 秒
- [ ] 内存占用（空闲）< 500 MB
- [ ] 安装包大小 < 200 MB

### 安全

- [ ] macOS 通过 Gatekeeper + Notarization
- [ ] Windows 通过 SmartScreen
- [ ] 无主流杀毒软件误报

---

## 🚨 主要风险

| 风险 | 缓解措施 |
|------|---------|
| **杀毒软件误报** | 签名所有二进制 + 提交白名单 |
| **模型许可合规** | 下载前强制确认 + 记录时间戳 |
| **更新失败** | 强制备份 + 自动回滚 + Safe Mode |

---

## 👥 团队配置

| 角色 | 人数 | 关键职责 |
|------|------|---------|
| 架构师 | 1 | 技术决策、评审 |
| Rust 后端 | 2 | Sidecar、更新机制 |
| Python 后端 | 1 | Runtime 适配、打包 |
| 前端 | 2 | UI、IPC |
| DevOps | 1 | CI/CD、签名 |
| QA | 2 | 测试、自动化 |
| 技术写作 | 1 | 文档 |
| 产品经理 | 1 | 需求、验收 |

---

## 📦 可交付物

### 已完成（设计阶段）

- ✅ 完整实施方案（75 KB）
- ✅ 技术决策记录（12 KB）
- ✅ 更新机制设计（35 KB）
- ✅ 任务拆解清单（25 KB，137 个任务）
- ✅ 快速启动指南（15 KB）

### 待交付（开发阶段）

- [ ] `agentos-desktop` 仓库（完整 Tauri 项目）
- [ ] macOS/Windows 安装包（< 200 MB）
- [ ] 自动更新 CDN（Cloudflare R2）
- [ ] 用户文档（安装、故障排除、FAQ）
- [ ] 视频教程（安装 + FTU）

---

## 🎯 下一步行动

### 如果你要启动这个项目

1. **召开 Kickoff 会议**
   - 议程：过一遍[快速启动指南](./docs/DESKTOP_APP_QUICK_START.md)
   - 时长：1-2 小时
   - 输出：团队理解目标，确认时间线

2. **架构评审会议**
   - 议程：审阅[技术决策记录](./docs/architecture/ADR_001_DESKTOP_APP_TECH_STACK.md)
   - 输出：签字确认技术选型

3. **建立项目基础**
   - 创建 `agentos-desktop` 仓库
   - 配置 Jira/Linear
   - 分配任务

4. **启动 Phase 0**
   - 工期：2 周
   - 产出：架构文档 + 骨架代码

### 如果你要参与开发

1. 阅读 → [快速启动指南](./docs/DESKTOP_APP_QUICK_START.md)
2. 找任务 → [任务清单](./docs/tasks/DESKTOP_APP_TASK_BREAKDOWN.md)
3. 准备环境 → 安装 Rust + Tauri + Node.js
4. 等待启动 🚀

---

## ❓ 常见问题

<details>
<summary><strong>Q: 为什么不用 Electron？</strong></summary>

A: Tauri 包体积小 90%（~5 MB vs ~70 MB），内存占用少 60%，且原生支持 sidecar 管理（这是关键需求）。学习 Rust 的成本被这些优势抵消。
</details>

<details>
<summary><strong>Q: 用户必须重启才能更新吗？</strong></summary>

A: 是的。这是最稳定的方案，避免跨平台文件锁、签名验证等问题。这也是行业标准（VS Code、Chrome 等都这么做）。用户体验上，提示很清晰："Update ready. Restart to apply."
</details>

<details>
<summary><strong>Q: 为什么要集成 Ollama？</strong></summary>

A: "开箱即用"的核心目标。如果用户需要单独安装 Ollama，就违背了这个目标。Ollama 是 MIT 许可证，可以合法随包分发。
</details>

<details>
<summary><strong>Q: 16-20 周是否太长？</strong></summary>

A: 这是包含所有阶段（测试、文档、签名、Beta）的完整周期。如果只做 MVP（Phase 0-2），可以压缩到 8-10 周。
</details>

<details>
<summary><strong>Q: 需要多少人？</strong></summary>

A: 建议 11 人。如果资源受限，核心团队至少：2 Rust 后端 + 1 前端 + 1 DevOps + 1 QA = 5 人。
</details>

更多问题 → [快速指南 FAQ](./docs/DESKTOP_APP_QUICK_START.md#-常见问题)

---

## 📞 联系方式

### 项目关键角色（待指定）

- **项目发起人**: TBD
- **技术负责人**: TBD
- **产品经理**: TBD

### 反馈渠道

- **文档问题**: 在对应文档提 Issue
- **技术讨论**: [Discord/Slack TBD]
- **任务管理**: [Jira/Linear TBD]

---

## 📖 扩展阅读

- [Tauri 官方文档](https://tauri.app/v2/guide/)
- [Nuitka 用户手册](https://nuitka.net/doc/user-manual.html)
- [Ollama API 文档](https://github.com/ollama/ollama/blob/main/docs/api.md)

---

## 🎉 致谢

本方案基于以下原则设计：

- **用户至上**：每个决策都围绕"降低用户心智负担"
- **工程优先**：选择技术稳定性而非最新潮流
- **风险可控**：所有关键风险都有明确缓解措施
- **可交付**：137 个任务，每个都有明确 DoD

---

**方案作者**: Claude (Anthropic)
**版本**: 1.0
**状态**: 设计完成，待启动

---

**祝项目成功！** 🚀

> 有任何疑问，请从[快速启动指南](./docs/DESKTOP_APP_QUICK_START.md)开始。
