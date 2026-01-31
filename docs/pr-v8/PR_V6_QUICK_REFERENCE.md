# PR-V6: Evidence Drawer - 快速参考

**状态**: ✅ 完成
**日期**: 2026-01-30

---

## 一分钟了解

**什么是 Evidence Drawer？**

证据抽屉是一个侧滑 UI 组件，让用户查看 checkpoint 的证据细节，理解任务执行的可靠性。

**核心功能**:
- 🟢 查看证据验证状态（已验证/失效/待验证）
- 📦 支持 4 种证据类型（文件、命令、数据库、哈希）
- 🎯 一键复制（路径、哈希、命令）
- 📱 响应式设计（桌面端 + 移动端）

---

## 快速开始

### 1. 打开演示页面

```bash
open demo_evidence_drawer.html
```

点击任意卡片即可查看不同场景的证据展示。

---

### 2. 在代码中使用

```javascript
// 初始化 EvidenceDrawer
const drawer = new EvidenceDrawer('evidence-drawer-container');

// 打开证据查看器
await drawer.open('checkpoint_abc123');

// 关闭
drawer.close();
```

---

### 3. API 调用

```bash
# 获取 checkpoint 证据
curl http://localhost:5000/api/checkpoints/ckpt_abc123/evidence

# 健康检查
curl http://localhost:5000/api/evidence/health
```

---

## 文件位置

| 文件 | 路径 |
|------|------|
| API 端点 | `agentos/webui/api/evidence.py` |
| 前端组件 | `agentos/webui/static/js/components/EvidenceDrawer.js` |
| CSS 样式 | `agentos/webui/static/css/evidence-drawer.css` |
| 演示页面 | `demo_evidence_drawer.html` |
| 完整报告 | `PR_V6_EVIDENCE_DRAWER_ACCEPTANCE_REPORT.md` |

---

## 证据类型

| 类型 | 图标 | 说明 |
|-----|------|------|
| artifact | 📦 | 文件或目录存在性验证 |
| file_sha256 | 🔐 | 文件内容哈希验证 |
| command | ⚙️ | 命令执行结果验证 |
| db_row | 💾 | 数据库记录断言验证 |

---

## 验证状态

| 状态 | 徽章 | 说明 |
|-----|------|------|
| verified | 🟢 已验证 | 所有证据通过，可安全恢复 |
| invalid | 🔴 失效 | 部分证据失败，需要回滚 |
| pending | 🟡 待验证 | 证据尚未验证 |

---

## 集成点

### PipelineView

- 自动捕获 `checkpoint_commit` 事件
- 在事件流中显示"查看证据"按钮
- 点击打开 EvidenceDrawer

### TimelineView

- 为 checkpoint 事件添加内联 verified 图标
- 点击图标打开 EvidenceDrawer
- 不干扰事件详情模态框

---

## 快速测试

### 测试场景 1: 查看已验证证据

```bash
open demo_evidence_drawer.html
# 点击 "迭代完成" 卡片（绿色徽章）
```

### 测试场景 2: 查看失效证据

```bash
open demo_evidence_drawer.html
# 点击 "测试失败" 卡片（红色徽章）
```

### 测试场景 3: 查看所有证据类型

```bash
open demo_evidence_drawer.html
# 点击 "完整示例" 卡片（4 种类型）
```

---

## 常见问题

### Q: 如何添加新的证据类型？

**A**:
1. 在 `agentos/core/checkpoints/models.py` 的 `EvidenceType` 枚举中添加新类型
2. 在 `EvidenceDrawer.js` 的 `renderEvidenceDetails()` 中添加渲染逻辑
3. 在 `evidence.py` 的 `_build_evidence_details()` 中添加数据构建逻辑

### Q: 如何自定义抽屉宽度？

**A**: 修改 `evidence-drawer.css` 中的 `--drawer-width` 变量：

```css
:root {
    --drawer-width: 600px; /* 默认 500px */
}
```

### Q: 如何支持多个抽屉同时打开？

**A**: 当前版本不支持。如需实现：
1. 修改 `EvidenceDrawer` 构造函数，接受唯一 ID
2. 每个视图创建独立的抽屉实例
3. 修改 CSS 使用动态定位（避免 right 冲突）

---

## 下一步

- **PR-V7**: 稳定性工程（性能优化、节流、回放一致性）
- **PR-V8**: 测试与压测（脚本化验收）

---

## 相关文档

- [完整验收报告](PR_V6_EVIDENCE_DRAWER_ACCEPTANCE_REPORT.md)
- [Checkpoint 管理文档](agentos/core/checkpoints/README.md)
- [Evidence 验证规范](docs/architecture/EVIDENCE_VERIFICATION.md)

---

**版本**: v1.0
**作者**: Frontend Evidence Agent
**日期**: 2026-01-30
