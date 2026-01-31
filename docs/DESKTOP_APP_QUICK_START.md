# AgentOS Desktop 快速启动指南

> **这是什么**: AgentOS 桌面应用实施方案的快速参考
> **适合人群**: 项目决策者、新加入团队成员
> **阅读时间**: 5 分钟

---

## 🎯 一句话概括

将 AgentOS 从"需要配置的开发工具"打包成"开箱即用的桌面应用"（像 VS Code / Cursor 那样）。

---

## 💡 核心理念

### 用户视角

```
安装 → 拖拽到 Applications → 打开
  ↓
选择模型存储位置
  ↓
下载一个推荐模型（可选）
  ↓
开始聊天
```

**3 步，5 分钟内完成**。

### 技术视角

```
Tauri Desktop Shell
  ↓
启动两个 Sidecar 进程：
  - AgentOS Runtime (Python → Nuitka 打包)
  - Ollama Server (官方二进制)
  ↓
用户通过简化的聊天 UI 使用
需要高级功能 → 点击"Open WebUI"
```

---

## 📚 文档导航

### 如果你是...

#### **决策者 / 产品经理**
👉 先读：[实施方案总览](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md)
- 第 1-3 节：执行概要、架构、技术选型
- 第 7 节：成功标准
- 第 6 节：风险与缓解

#### **技术负责人 / 架构师**
👉 先读：[技术决策记录 (ADR)](./architecture/ADR_001_DESKTOP_APP_TECH_STACK.md)
- 为什么选 Tauri 而不是 Electron
- 为什么选 Nuitka 打包
- 为什么更新要"重启生效"

#### **开发者 / 工程师**
👉 先读：[任务拆解清单](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md)
- 137 个具体任务
- 你的角色对应的任务
- 每个任务的 DoD（完成定义）

#### **DevOps / 发布工程师**
👉 先读：
1. [更新机制设计](./architecture/UPDATE_MECHANISM_DESIGN.md) - 了解更新流程
2. [任务清单 Phase 6](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#phase-6-打包与签名4-周) - 打包签名任务

#### **QA / 测试工程师**
👉 先读：
1. [实施方案 - 成功标准](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-成功标准验收标准)
2. [任务清单 - 测试任务](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#测试任务贯穿所有阶段)

---

## 🗺️ 时间线概览

```
总工期：16-20 周（4-5 个月）

Week 1-2   : Phase 0 - 基础设施（目录结构、版本协议）
Week 2-5   : Phase 1 - Sidecar 管理（启动、监控、日志）
Week 5-8   : Phase 2 - Runtime 打包（Nuitka 配置、跨平台）
Week 8-12  : Phase 3 - 热更新（下载、校验、重启生效）★ 最复杂
Week 12-15 : Phase 4 - 模型管理（下载进度、许可证确认）
Week 15-17 : Phase 5 - 首次启动（FTU 3 步流程）
Week 17-20 : Phase 6 - 打包签名（macOS 公证、Windows 签名）
```

**关键决策点（Go/No-Go）**：
- Week 2 结束：架构文档签字确认
- Week 12 结束：更新机制在 3 个平台通过测试
- Week 20 结束：Beta 测试（10 个用户，0 个 P0 bug）

---

## 🔑 关键技术决策

### 为什么选 Tauri？

| 对比项 | Tauri | Electron |
|--------|-------|----------|
| 包体积 | **✅ ~5 MB** | ❌ ~70 MB |
| 内存占用 | **✅ ~100 MB** | ❌ ~300 MB |
| Sidecar 支持 | **✅ 原生** | ⚠️ 手动实现 |
| 安全性 | **✅ Rust** | ⚠️ Node.js |

**决策**：Tauri 2.x

---

### 为什么更新要"重启生效"？

**对比方案**：
1. ✅ **重启生效**（选中）
   - 技术简单（避免文件锁问题）
   - 用户心智清晰（"下载 → 重启"是行业标准）
   - 风险低（失败可回滚）

2. ❌ In-place 替换
   - Windows 文件锁无法解决
   - macOS 签名验证复杂
   - 风险高（失败可能无法启动）

**用户体验**：
```
"Update ready. Restart to apply." [Restart Now] [Later]
```

---

### 为什么不预装模型？

1. **许可证合规**：不同模型有不同许可证，必须用户明确同意
2. **包体积**：模型动辄 5-10 GB，会让安装包膨胀
3. **用户选择**：让用户根据需求选择模型（代码 vs 通用）

**方案**：
- 首次启动时推荐 2-3 个模型
- 用户可选择下载或跳过
- 下载前展示许可证并要求确认

---

## 🚨 主要风险

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| **杀毒软件误报** | 高 | • 签名所有二进制<br>• 提交白名单<br>• 提供手动添加指南 |
| **模型许可合规** | 中 | • 下载前强制确认<br>• 记录同意时间戳<br>• 不预装模型 |
| **更新失败** | 低 | • 强制备份<br>• 自动回滚<br>• Safe Mode 启动 |

---

## 📦 可交付物

### 技术文档（8 份）

- [x] ✅ 实施方案总览
- [x] ✅ 技术决策记录 (ADR)
- [x] ✅ 更新机制设计
- [x] ✅ 任务拆解清单
- [ ] 目录结构与约束
- [ ] Sidecar 生命周期管理
- [ ] 打包与签名指南
- [ ] 回滚策略

### 用户文档（4 份）

- [ ] 安装指南
- [ ] 故障排除手册
- [ ] 模型许可证 FAQ
- [ ] 更新 FAQ

### 代码仓库（1 个）

- [ ] `agentos-desktop/` - 完整 Tauri 项目
  - `src-tauri/` - Rust 后端
  - `src/` - React 前端
  - `updater-helper/` - 更新辅助程序

### CI/CD Pipeline（1 套）

- [ ] GitHub Actions：自动打包（macOS Intel/ARM, Windows）
- [ ] GitHub Actions：自动签名
- [ ] GitHub Actions：发布到 CDN

---

## 🎯 验收标准（必须满足）

### 核心体验

- [ ] **安装**：macOS 拖拽，Windows 双击，< 2 分钟
- [ ] **首次启动**：3 步内完成配置
- [ ] **聊天响应**：首次响应 < 5 秒
- [ ] **更新**：检测到重启，用户无感知

### 性能

| 指标 | 目标 |
|------|------|
| App 启动时间 | < 3 秒 |
| Sidecar 启动 | < 5 秒 |
| 内存占用（空闲） | < 500 MB |
| 安装包大小 | < 200 MB |

### 安全

- [ ] 所有二进制已签名
- [ ] macOS 通过 Gatekeeper 和 Notarization
- [ ] Windows 通过 SmartScreen
- [ ] 无主流杀毒软件误报

---

## 👥 团队配置（建议）

| 角色 | 人数 | 关键职责 |
|------|------|---------|
| 架构师 | 1 | 技术决策、评审 |
| Rust 后端 | 2 | Sidecar、更新机制 |
| Python 后端 | 1 | Runtime 适配、打包 |
| 前端开发 | 2 | UI、IPC |
| DevOps | 1 | CI/CD、签名 |
| QA | 2 | 测试、自动化 |
| 技术写作 | 1 | 文档 |
| 产品经理 | 1 | 需求、验收 |

**总计**：11 人

---

## 🚀 如何开始

### 如果你要启动这个项目

1. **召开 Kickoff 会议**
   - 议程：过一遍本文档 + 实施方案
   - 输出：团队理解目标，确认时间线

2. **架构评审会议**
   - 议程：审阅 [技术决策记录](./architecture/ADR_001_DESKTOP_APP_TECH_STACK.md)
   - 输出：签字确认技术选型

3. **创建项目仓库**
   - 任务：[P0.1.1](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md#p01-项目初始化)
   - 负责人：DevOps

4. **分配任务**
   - 使用：[任务清单](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md)
   - 工具：Jira / Linear / GitHub Projects

5. **启动第一个 Sprint**
   - 范围：Phase 0（2 周）
   - 产出：架构文档 + 骨架代码

---

### 如果你要参与开发

1. **理解架构**
   - 阅读：[实施方案](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md) 的第 2 节（架构）

2. **找到你的任务**
   - 查看：[任务清单](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md)
   - 筛选：你的角色（前端/后端/DevOps/QA）

3. **环境准备**
   - Rust 工具链：安装 rustup
   - Tauri 依赖：参考 [Tauri 官方文档](https://tauri.app/v2/guides/getting-started/prerequisites/)
   - Python 3.13：用于 Runtime 打包

4. **开始第一个任务**
   - 选择：P0 或 P1 阶段的任务
   - 提交 PR：包含单元测试

---

## 📞 联系方式

### 项目关键角色（待填）

- **项目发起人**: TBD
- **技术负责人**: TBD
- **产品经理**: TBD
- **DevOps Lead**: TBD

### 沟通渠道

- **技术讨论**: [待建立 Discord/Slack]
- **任务管理**: [待配置 Jira/Linear]
- **文档协作**: GitHub Docs
- **每周同步**: 每周四 10:00（建议）

---

## ❓ 常见问题

### Q1: 为什么不用 Electron？

A: Tauri 包体积小 90%，内存占用少 60%，且原生支持 sidecar 管理（关键需求）。团队需要学习 Rust 的成本被这些优势抵消。

### Q2: 用户必须重启才能更新吗？

A: 是的。这是最稳定的方案，避免了跨平台文件锁、签名验证等复杂问题。用户体验上，这也是行业标准（VS Code、Chrome 等都是重启更新）。

### Q3: 可以不集成 Ollama 吗？

A: 技术上可以（让用户自己安装），但违背了"开箱即用"的核心目标。Ollama 是 MIT 许可证，可以合法随包分发。

### Q4: 16-20 周是否太长？

A: 这是包含所有阶段（含测试、文档、签名）的完整周期。如果只做 MVP（Phase 0-2），可以压缩到 8-10 周。

### Q5: 需要多少人？

A: 建议 11 人（见团队配置）。如果资源受限，核心团队至少需要：2 Rust 后端 + 1 前端 + 1 DevOps + 1 QA = 5 人。

### Q6: 已有 WebUI，为什么还要做桌面版？

A: 桌面版是"简化的入口"，面向不想配置环境的普通用户。高级用户仍然可以点击"Open WebUI"使用完整功能。

### Q7: 模型许可证风险如何应对？

A: 下载前强制展示许可证并要求用户确认，记录同意时间戳。不预装模型，避免潜在法律风险。

---

## 📖 下一步阅读

根据你的角色选择：

- **决策者** → [实施方案：成功标准](./architecture/DESKTOP_APP_IMPLEMENTATION_PLAN.md#-成功标准验收标准)
- **架构师** → [技术决策记录 (ADR)](./architecture/ADR_001_DESKTOP_APP_TECH_STACK.md)
- **开发者** → [任务清单](./tasks/DESKTOP_APP_TASK_BREAKDOWN.md)
- **DevOps** → [更新机制设计](./architecture/UPDATE_MECHANISM_DESIGN.md)

---

**文档版本**: 1.0
**最后更新**: 2026-01-30
**维护者**: Claude (Anthropic)

---

祝项目顺利！🚀
