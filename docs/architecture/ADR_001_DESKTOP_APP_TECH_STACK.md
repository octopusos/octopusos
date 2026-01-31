# ADR 001: AgentOS Desktop 技术栈选型

> **状态**: 提议中
> **日期**: 2026-01-30
> **决策人**: 技术委员会
> **影响范围**: 整个桌面应用项目

---

## 背景

AgentOS 需要从"开发者工具"升级为"面向普通用户的桌面产品"。关键约束：

1. 用户不应看到 Python 环境
2. 需要集成 Ollama Server 作为 sidecar
3. 支持热更新（重启后生效）
4. 跨平台（macOS Intel/ARM, Windows）
5. 开箱即用体验

---

## 决策

### 1. Desktop Framework: **Tauri 2.x**

#### 选择理由

| 标准 | Tauri | Electron | Flutter |
|------|-------|----------|---------|
| **包体积** | ✅ ~3-5 MB | ❌ ~50-70 MB | ⚠️ ~20-30 MB |
| **内存占用** | ✅ ~50-100 MB | ❌ ~150-300 MB | ⚠️ ~100-150 MB |
| **Sidecar 支持** | ✅ 原生 | ⚠️ 手动实现 | ⚠️ 手动实现 |
| **代码签名** | ✅ 内置 | ✅ 支持 | ✅ 支持 |
| **热更新** | ✅ 官方方案 | ✅ 社区方案 | ⚠️ 有限支持 |
| **安全性** | ✅ Rust | ⚠️ Node.js | ✅ Dart |
| **团队熟悉度** | ⚠️ 需学习 | ✅ 熟悉 | ❌ 不熟悉 |

**决策**: Tauri 2.x

**核心优势**：
- 原生 sidecar 管理（关键需求）
- 极小的包体积（降低分发成本）
- Rust 安全性（减少运行时漏洞）

**风险**：
- 团队需要学习 Rust（缓解：仅需掌握基础，复杂逻辑在 Python Runtime）

---

### 2. Python Runtime 打包: **Nuitka**

#### 选择理由

| 工具 | 单文件 | 性能 | 增量更新 | 签名支持 |
|------|-------|------|---------|---------|
| **Nuitka** | ✅ | ✅ 编译为 C | ✅ | ✅ |
| PyInstaller | ✅ | ⚠️ 解释执行 | ⚠️ | ✅ |
| PyOxidizer | ✅ | ✅ Rust 包装 | ❌ | ✅ |

**决策**: Nuitka

**核心优势**：
- 真正的编译（性能提升 10-15%）
- 单文件模式（用户无感知）
- 支持增量更新（关键需求）

**劣势**：
- 编译时间较长（缓解：CI/CD 自动化）

---

### 3. Ollama 集成: **Sidecar 模式**

#### 对比方案

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Sidecar（随包）** | • 开箱即用<br>• 版本可控 | • 包体积增大 (~100MB) |
| 外部安装检测 | • 包体积小 | • 用户需手动安装<br>• 版本不可控 |

**决策**: Sidecar 随包分发

**理由**：
- 符合"开箱即用"核心目标
- Ollama 是 MIT 许可证，可合法分发
- 通过环境变量控制端口和模型目录

**配置方式**：
```bash
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_MODELS=~/.agentos/models
OLLAMA_ORIGINS=http://127.0.0.1:*
```

---

### 4. 更新策略: **组件级热更新 + 重启生效**

#### 对比方案

| 方案 | 技术复杂度 | 用户体验 | 风险 |
|------|-----------|---------|------|
| **重启生效** | 低 | 可接受 | 低 |
| In-place 替换 | 高 | 理想 | 高（文件锁） |

**决策**: 重启生效

**理由**：
- 避免平台差异（Windows 文件锁、macOS 签名验证）
- 降低风险（失败可回滚）
- 用户心智模型清晰（"下载 → 重启"）

**实现方式**：
```
下载 → 校验 → 暂存 → 标记 pending → 提示重启 → Helper 替换 → App 重启
```

---

### 5. 前端框架: **React + Vite**

#### 选择理由

- **复用现有资源**: AgentOS 已有 WebUI，部分组件可复用
- **团队熟悉**: 降低学习成本
- **生态成熟**: UI 库、状态管理方案丰富

---

## 后果

### 正面影响

1. **极小包体积**: 相比 Electron 节省 ~90% 大小
2. **稳定更新**: 重启机制避免 90% 的平台兼容问题
3. **快速开发**: 复用 AgentOS 现有 Python 后端逻辑

### 负面影响

1. **学习曲线**: 团队需要掌握 Rust 基础（预计 1-2 周）
2. **打包时间**: Nuitka 编译较慢（缓解：CI 并行）
3. **首次重启**: 用户需要重启才能应用更新（行业标准，可接受）

---

## 依赖与约束

### 硬性约束

- **Ollama 版本锁定**: 0.5.x（需验证 API 兼容性）
- **Python 版本**: 3.13（已验证）
- **最小 macOS 版本**: 13 (Ventura)
- **最小 Windows 版本**: 10 (Build 1809)

### 外部依赖

- **Apple Developer ID**: 用于 macOS 签名和公证
- **Windows Authenticode 证书**: 用于 Windows 签名
- **CDN**: 托管更新包（建议 Cloudflare R2）

---

## 验证标准

### 技术验证（Phase 0 结束前完成）

- [ ] Tauri 可以启动 AgentOS Runtime sidecar
- [ ] Tauri 可以启动 Ollama sidecar
- [ ] Nuitka 打包的 binary 可以独立运行
- [ ] 更新 Helper 可以在 App 退出后替换文件

### 用户验证（Beta 测试）

- [ ] 10 个用户成功完成 FTU
- [ ] 0 个用户报告"看到 Python 环境"
- [ ] 更新成功率 > 95%

---

## 替代方案（已拒绝）

### Electron + PyInstaller

**拒绝理由**: 包体积过大（~120 MB vs ~50 MB）

### Flutter + PyOxidizer

**拒绝理由**: 团队不熟悉 Flutter，学习成本高于 Tauri

### 完全 Web 化（Browser Extension）

**拒绝理由**: 无法管理本地 sidecar 进程

---

## 参考资料

- [Tauri Sidecar Documentation](https://tauri.app/v2/guides/building/sidecar/)
- [Nuitka User Manual](https://nuitka.net/doc/user-manual.html)
- [Ollama Environment Variables](https://github.com/ollama/ollama/blob/main/docs/faq.md#how-do-i-configure-ollama-server)

---

## 变更记录

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| 0.1 | 2026-01-30 | 初稿 | Claude |

---

**状态**: 提议中
**下一步**: 技术评审会议（预计 2026-02-05）
