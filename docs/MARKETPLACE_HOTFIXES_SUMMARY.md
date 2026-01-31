# MCP Marketplace Hotfixes 汇总

## 概述

本文档汇总 MCP Marketplace WebUI 上线后发现的所有 bug 及其修复情况。

---

## Hotfix 001 - 前后端字段名不匹配

**发现时间**: 2026-01-31
**严重程度**: P0（核心功能显示错误）
**详细文档**: `MARKETPLACE_HOTFIX_001.md`

### 问题描述

Trust Tier、Risk Level、Admin Token 等关键信息显示为 "undefined"，影响用户理解治理信息。

### 根本原因

前后端字段名不匹配，前端引用的字段名与后端返回的不一致。

### 修复内容

**第一轮修复**:
- ❌ `pkg.trust_tier` → ✅ `pkg.recommended_trust_tier`
- ❌ `pkg.connected` → ✅ `pkg.is_connected`
- ❌ `pkg.id` → ✅ `pkg.package_id`

**第二轮修复**:
- ❌ `gov.trust_tier` → ✅ `gov.inferred_trust_tier`
- ❌ `gov.risk_level` → ✅ `gov.inferred_risk_level`
- ❌ `gov.requires_admin_token` (boolean) → ✅ `gov.requires_admin_token_for` (array)
- 修复变量作用域错误（`trustTierLabel` 未定义）

**新增辅助方法**:
- `getTrustTierLabel(tier)` - Trust Tier 标签生成
- `sanitizeId(packageId)` - Package ID 清理

### 影响范围

- MarketplaceView.js (列表页)
- MCPPackageDetailView.js (详情页)

### 验证

```bash
./scripts/verify_marketplace_fields.sh
```

**结果**: ✅ 所有检查通过（0 错误，0 警告）

---

## Hotfix 002 - 详情页宽度不一致

**发现时间**: 2026-01-31
**严重程度**: P2（用户体验问题）
**详细文档**: `MARKETPLACE_HOTFIX_002.md`

### 问题描述

Package Detail 页面宽度（900px）与 Marketplace 列表页（1400px）不一致，视觉不统一。

### 根本原因

CSS 样式设置不一致。

### 修复内容

```css
/* 修复前 */
.package-detail {
    max-width: 900px;  ❌
}

/* 修复后 */
.package-detail {
    max-width: 1400px;  ✅
}
```

### 影响范围

- marketplace.css

### 验证

```bash
./scripts/verify_marketplace_width.sh
```

**结果**: ✅ 宽度设置一致 (1400px)

---

## 修复统计

| Hotfix | 严重程度 | 问题类型 | 修复文件数 | 新增辅助方法 | 验证脚本 |
|--------|---------|---------|-----------|-------------|---------|
| 001 | P0 | 字段名不匹配 | 2 | 2 | ✅ |
| 002 | P2 | 样式不一致 | 1 | 0 | ✅ |
| **总计** | - | - | **3** | **2** | **2** |

---

## 验证清单

### 自动化验证

```bash
# 字段名验证
./scripts/verify_marketplace_fields.sh

# 宽度验证
./scripts/verify_marketplace_width.sh

# 完整验收测试
./scripts/verify_marketplace.sh
```

### 手动验证

1. **刷新浏览器** (清除缓存):
   - Windows/Linux: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

2. **访问 Marketplace**:
   - URL: `http://localhost:5000`
   - 导航: Settings → MCP Marketplace

3. **检查列表页**:
   - [ ] Trust Tier 显示正确（如 "T0 - Local Extension"）
   - [ ] 连接状态显示正确
   - [ ] 页面宽度适中（不太窄）
   - [ ] 无 JavaScript 错误

4. **检查详情页**:
   - [ ] Trust Tier 显示正确
   - [ ] Risk Level 显示正确（如 "MEDIUM"）
   - [ ] Admin Token 显示正确（如 "Yes (side_effects)"）
   - [ ] 页面宽度与列表页一致
   - [ ] 治理预览区域完整展示
   - [ ] 无 JavaScript 错误

---

## 文档清单

| 文档 | 类型 | 大小 | 用途 |
|------|------|------|------|
| `MARKETPLACE_HOTFIX_001.md` | 修复报告 | 11KB | 字段名修复详情 |
| `MARKETPLACE_HOTFIX_002.md` | 修复报告 | 3KB | 宽度修复详情 |
| `MARKETPLACE_FIELD_MAPPING.md` | 技术参考 | 19KB | 前后端字段映射 |
| `MARKETPLACE_HOTFIXES_SUMMARY.md` | 汇总 | 本文档 | 所有 hotfix 汇总 |

---

## 脚本清单

| 脚本 | 功能 | 检查项 | 输出 |
|------|------|--------|------|
| `verify_marketplace_fields.sh` | 字段名验证 | 20+ | PASS/FAIL |
| `verify_marketplace_width.sh` | 宽度一致性 | 2 | PASS/FAIL |
| `verify_marketplace.sh` | 完整验收 | 25+ | PASS/FAIL |

---

## 预防措施

### 短期

1. **代码审查清单**:
   - 检查前后端字段名一致性
   - 验证 CSS 样式一致性
   - 确保辅助方法复用

2. **测试增强**:
   - 添加字段名验证测试
   - 添加 UI 宽度测试

### 长期

1. **前端类型系统**:
   - 使用 TypeScript
   - 定义共享接口
   - 编译时捕获字段名错误

2. **API 契约测试**:
   - JSON Schema 验证
   - 自动化契约测试

3. **E2E 测试**:
   - Playwright/Cypress
   - 自动验证 UI 正确性

4. **设计系统**:
   - 统一的样式变量
   - 组件库
   - 设计 Token

---

## 经验教训

### 字段名不匹配（Hotfix 001）

**原因**:
- 前后端开发未充分对齐
- 缺乏类型定义和契约

**教训**:
- ✅ 使用 TypeScript 或 JSON Schema
- ✅ 前后端共享类型定义
- ✅ API 返回格式统一（`{ok: true, data: {...}}`）
- ✅ 添加运行时数据验证

### 样式不一致（Hotfix 002）

**原因**:
- 复制模板时未全局检查
- 缺乏样式规范文档

**教训**:
- ✅ 建立设计系统
- ✅ 使用 CSS 变量
- ✅ 代码审查检查样式一致性
- ✅ 自动化 UI 测试

---

## 后续计划

### 立即执行（本周）

- [ ] 添加 E2E 测试覆盖 Marketplace
- [ ] 创建前后端字段映射文档（已完成）
- [ ] 添加 CSS 样式规范文档

### 短期（本月）

- [ ] 引入 TypeScript（渐进式）
- [ ] 添加 API 契约测试
- [ ] 建立 Design Token 系统

### 长期（下季度）

- [ ] 完整的组件库
- [ ] 自动化视觉回归测试
- [ ] 性能监控和报警

---

## 联系人

**技术负责人**: AgentOS Team
**修复人**: Claude Code (Sonnet 4.5)
**文档维护**: 实时更新

---

## 更新日志

- **2026-01-31**: 初始版本（Hotfix 001, 002）
- **2026-01-31**: 添加验证脚本和文档

---

**状态**: ✅ 所有已知问题已修复并验证通过
