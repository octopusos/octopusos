# Marketplace Hotfix 001 - 修复前后端字段名不匹配

## 问题描述

在 MCP Marketplace WebUI 中，Trust Tier 显示为 "undefined"，影响用户体验。

**截图**: Trust Tier 位置显示 "undefined"

## 根因分析

**前后端字段名不匹配**:

### 后端 API 返回字段名（正确）

**列表 API** (`GET /api/mcp/marketplace/packages`):
```json
{
  "packages": [{
    "package_id": "agentos.official/echo-math",
    "recommended_trust_tier": "T0",
    "is_connected": false,
    ...
  }]
}
```

**详情 API** (`GET /api/mcp/marketplace/packages/{id}`):
```json
{
  "ok": true,
  "data": {
    "package_id": "agentos.official/echo-math",
    "is_connected": false,
    ...
  }
}
```

**治理预览 API** (`GET /api/mcp/marketplace/governance-preview/{id}`):
```json
{
  "ok": true,
  "data": {
    "inferred_trust_tier": "T0",
    ...
  }
}
```

### 前端引用字段名（错误）

**MarketplaceView.js**:
- ❌ `pkg.trust_tier` → ✅ `pkg.recommended_trust_tier`
- ❌ `pkg.connected` → ✅ `pkg.is_connected`
- ❌ `pkg.id` → ✅ `pkg.package_id`

**MCPPackageDetailView.js**:
- ❌ `pkg.connected` → ✅ `pkg.is_connected`
- ❌ `gov.trust_tier` → ✅ `gov.inferred_trust_tier`
- ❌ 未提取 `data` 字段 → ✅ 需要提取

## 修复内容

### 1. MarketplaceView.js（列表页）

**修复内容**:
```javascript
// 修复前
const trustTierClass = this.getTrustTierClass(pkg.trust_tier);
const statusClass = pkg.connected ? 'connected' : 'not-connected';
const card = document.getElementById(`pkg-card-${pkg.id}`);

// 修复后
const trustTierClass = this.getTrustTierClass(pkg.recommended_trust_tier);
const statusClass = pkg.is_connected ? 'connected' : 'not-connected';
const card = document.getElementById(`pkg-card-${this.sanitizeId(pkg.package_id)}`);
```

**新增方法**:
```javascript
sanitizeId(packageId) {
    return packageId.replace(/[^a-zA-Z0-9-_]/g, '-');
}
```

**影响范围**:
- ✅ Trust Tier 徽章正确显示
- ✅ 连接状态正确显示
- ✅ 卡片点击正确工作
- ✅ 过滤功能正确工作

### 2. MCPPackageDetailView.js（详情页）

**修复内容**:
```javascript
// 修复前
this.package = await pkgResponse.json();
this.governance = await govResponse.json();
const statusClass = pkg.connected ? 'connected' : 'not-connected';
<span class="trust-tier-badge">${gov.trust_tier}</span>

// 修复后
const pkgData = await pkgResponse.json();
const govData = await govResponse.json();
this.package = pkgData.ok ? pkgData.data : pkgData;
this.governance = govData.ok ? govData.data : govData;
const statusClass = pkg.is_connected ? 'connected' : 'not-connected';
const trustTierLabel = trustTierLabels[gov.inferred_trust_tier];
<span class="trust-tier-badge">${gov.inferred_trust_tier} (${trustTierLabel})</span>
```

**影响范围**:
- ✅ Trust Tier 正确显示
- ✅ 连接状态正确显示
- ✅ 治理预览数据正确加载
- ✅ Attach 流程正常工作

## 测试验证

### 手动测试步骤

1. **启动 WebUI**:
   ```bash
   cd /Users/pangge/PycharmProjects/AgentOS
   agentos webui
   ```

2. **访问 Marketplace**:
   - 打开: `http://localhost:5000`
   - 导航: Settings → MCP Marketplace

3. **验证列表页**:
   - ✅ Trust Tier 显示为 "T0 - Local Extension"（而非 "undefined"）
   - ✅ 连接状态显示正确（Connected / Not Connected）
   - ✅ 点击卡片可跳转到详情页

4. **验证详情页**:
   - ✅ Trust Tier 显示正确
   - ✅ 治理预览区域正确展示
   - ✅ Attach 按钮正常工作

### 预期结果

**修复前**:
```
Trust Tier: undefined
Connection Status: undefined
```

**修复后**:
```
Trust Tier: T0 - Local Extension
Connection Status: Not Connected
```

## 影响评估

**严重程度**: P0（核心功能显示错误）

**影响范围**:
- MCP Marketplace 列表页
- MCP Package 详情页
- 治理预览功能

**用户影响**:
- 无法看到 Trust Tier 信息（治理系统核心）
- 界面显示 "undefined"，用户体验差
- 过滤功能可能不正常

## 修复状态

- ✅ 已修复 MarketplaceView.js
- ✅ 已修复 MCPPackageDetailView.js (第一轮)
- ✅ 已添加 sanitizeId 辅助方法
- ✅ 已添加 getTrustTierLabel 辅助方法
- ✅ 已修复 trustTierLabel 作用域错误 (第二轮)
- ✅ 已修复 risk_level 字段名 (第二轮)
- ✅ 已修复 requires_admin_token 字段名 (第二轮)
- ⏳ 等待人工验证

## 第二轮修复（2026-01-31）

### 新发现的问题

**问题 1**: `trustTierLabel is not defined`
- **位置**: `MCPPackageDetailView.renderGovernancePreview()`
- **根因**: `trustTierLabel` 变量只在 `renderPackageDetail()` 方法中定义，在 `renderGovernancePreview()` 中超出作用域
- **修复**: 提取为类方法 `getTrustTierLabel(tier)`，在两个地方复用

**问题 2**: `gov.risk_level` → `gov.inferred_risk_level`
- **位置**: 多处引用
- **根因**: 后端返回 `inferred_risk_level`，前端引用 `risk_level`
- **修复**: 全局替换为正确字段名

**问题 3**: `gov.requires_admin_token` → `gov.requires_admin_token_for`
- **位置**: 治理预览和 Attach 提示
- **根因**: 后端返回数组 `requires_admin_token_for`，前端当作布尔值 `requires_admin_token`
- **修复**:
  ```javascript
  // 修复前
  ${gov.requires_admin_token ? 'Yes' : 'No'}

  // 修复后
  ${gov.requires_admin_token_for && gov.requires_admin_token_for.length > 0
    ? `Yes (${gov.requires_admin_token_for.join(', ')})`
    : 'No'}
  ```

### 修复的代码段

**新增辅助方法**:
```javascript
/**
 * Get trust tier display label
 */
getTrustTierLabel(tier) {
    const labels = {
        'T0': 'Local Extension',
        'T1': 'Local MCP',
        'T2': 'Remote MCP',
        'T3': 'Cloud MCP'
    };
    return labels[tier] || tier;
}
```

**使用辅助方法**:
```javascript
// renderPackageDetail()
const trustTierLabel = this.getTrustTierLabel(gov.inferred_trust_tier);

// renderGovernancePreview()
const tierLabel = this.getTrustTierLabel(gov.inferred_trust_tier);
```

## 后续改进建议

### 1. 前后端类型契约（推荐）

使用 TypeScript 或 JSON Schema 定义前后端数据契约:

```typescript
// shared/types/marketplace.ts
interface MCPPackageSummary {
    package_id: string;
    name: string;
    recommended_trust_tier: string;
    is_connected: boolean;
    ...
}
```

### 2. API 响应格式统一

确保所有 API 都返回一致的格式:

```javascript
{
  "ok": true,
  "data": {...},
  "error": null
}
```

前端统一处理:

```javascript
async function fetchAPI(url) {
    const response = await fetch(url);
    const json = await response.json();
    return json.ok ? json.data : json;
}
```

### 3. 添加 E2E 测试

创建 Playwright/Cypress 测试验证 UI 正确渲染:

```javascript
test('Marketplace displays trust tier correctly', async ({ page }) => {
    await page.goto('/marketplace');
    const tierBadge = page.locator('.trust-tier-badge').first();
    await expect(tierBadge).not.toContainText('undefined');
    await expect(tierBadge).toContainText(/T[0-3]/);
});
```

### 4. 前端数据验证

添加运行时数据验证:

```javascript
function validatePackage(pkg) {
    if (!pkg.recommended_trust_tier) {
        console.error('Missing recommended_trust_tier:', pkg);
    }
    return pkg;
}
```

## 相关文件

- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/MarketplaceView.js`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/MCPPackageDetailView.js`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/mcp_marketplace.py`
- `/Users/pangge/PycharmProjects/AgentOS/agentos/core/mcp/marketplace_models.py`

## 修复日期

2026-01-31

## 修复人

Claude Code (Sonnet 4.5)
