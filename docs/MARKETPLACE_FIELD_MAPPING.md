# MCP Marketplace 前后端字段映射参考

## 概述

本文档列出 MCP Marketplace 的前后端字段映射关系，避免字段名不匹配导致的 bug。

---

## Package 数据（列表 API）

**后端**: `GET /api/mcp/marketplace/packages`

**返回格式**:
```json
{
  "packages": [...],
  "total": 4
}
```

### Package Summary 字段映射

| 前端引用 | 后端字段 | 类型 | 说明 |
|---------|---------|------|------|
| `pkg.package_id` | `package_id` | string | Package 唯一标识（如 "agentos.official/echo-math"） |
| `pkg.name` | `name` | string | 显示名称 |
| `pkg.version` | `version` | string | 版本号 |
| `pkg.author` | `author` | string | 作者 |
| `pkg.description` | `description` | string | 简短描述 |
| `pkg.tools_count` | `tools_count` | number | 工具数量 |
| `pkg.transport` | `transport` | string | 传输协议 (stdio/http/https/tcp/ssh) |
| `pkg.recommended_trust_tier` | `recommended_trust_tier` | string | **推荐**信任层级 (T0-T3) |
| `pkg.requires_admin_token` | `requires_admin_token` | boolean | 是否需要 admin token |
| `pkg.is_connected` | `is_connected` | boolean | 是否已接入 |
| `pkg.tags` | `tags` | string[] | 标签列表 |

### ⚠️ 常见错误

- ❌ `pkg.trust_tier` → ✅ `pkg.recommended_trust_tier`
- ❌ `pkg.connected` → ✅ `pkg.is_connected`
- ❌ `pkg.id` → ✅ `pkg.package_id`

---

## Package 详情（详情 API）

**后端**: `GET /api/mcp/marketplace/packages/{package_id}`

**返回格式**:
```json
{
  "ok": true,
  "data": {
    "package_id": "...",
    "name": "...",
    ...
  }
}
```

### ⚠️ 重要：需要提取 `data` 字段

```javascript
// ✅ 正确
const pkgData = await response.json();
const pkg = pkgData.ok ? pkgData.data : pkgData;

// ❌ 错误
const pkg = await response.json();  // 会得到 {ok: true, data: {...}}
```

### Package Detail 字段映射

详情 API 返回完整的 `MCPPackage` 对象，包含所有字段：

| 前端引用 | 后端字段 | 类型 | 说明 |
|---------|---------|------|------|
| `pkg.package_id` | `package_id` | string | Package ID |
| `pkg.name` | `name` | string | 名称 |
| `pkg.version` | `version` | string | 版本 |
| `pkg.author` | `author` | string | 作者 |
| `pkg.description` | `description` | string | 简短描述 |
| `pkg.long_description` | `long_description` | string | 详细说明 |
| `pkg.tools` | `tools` | MCPToolDeclaration[] | 工具列表 |
| `pkg.declared_side_effects` | `declared_side_effects` | string[] | 声明的副作用 |
| `pkg.transport` | `transport` | string | 传输协议 |
| `pkg.connection_template` | `connection_template` | object | 连接配置模板 |
| `pkg.recommended_trust_tier` | `recommended_trust_tier` | string | 推荐信任层级 |
| `pkg.recommended_quota_profile` | `recommended_quota_profile` | string | 推荐配额档位 |
| `pkg.requires_admin_token` | `requires_admin_token` | boolean | 是否需要 admin token |
| `pkg.homepage` | `homepage` | string | 主页链接 |
| `pkg.repository` | `repository` | string | 仓库链接 |
| `pkg.license` | `license` | string | 许可证 |
| `pkg.tags` | `tags` | string[] | 标签 |
| `pkg.is_connected` | `is_connected` | boolean | 是否已接入 |
| `pkg.connected_at` | `connected_at` | string | 接入时间 |

### MCPToolDeclaration 字段

| 前端引用 | 后端字段 | 类型 |
|---------|---------|------|
| `tool.name` | `name` | string |
| `tool.description` | `description` | string |
| `tool.input_schema` | `input_schema` | object |
| `tool.side_effects` | `side_effects` | string[] |
| `tool.requires_confirmation` | `requires_confirmation` | boolean |

---

## 治理预览（Governance Preview API）

**后端**: `GET /api/mcp/marketplace/governance-preview/{package_id}`

**返回格式**:
```json
{
  "ok": true,
  "data": {
    "package_id": "...",
    "inferred_trust_tier": "T1",
    "inferred_risk_level": "MEDIUM",
    ...
  }
}
```

### ⚠️ 重要：需要提取 `data` 字段（同上）

### Governance Preview 字段映射

| 前端引用 | 后端字段 | 类型 | 说明 |
|---------|---------|------|------|
| `gov.package_id` | `package_id` | string | Package ID |
| `gov.inferred_trust_tier` | `inferred_trust_tier` | string | **推断的**信任层级 (T0-T3) |
| `gov.inferred_risk_level` | `inferred_risk_level` | string | **推断的**风险等级 (LOW/MEDIUM/HIGH/CRITICAL) |
| `gov.default_quota` | `default_quota` | object | 默认配额设置 |
| `gov.requires_admin_token_for` | `requires_admin_token_for` | string[] | 需要 admin token 的操作列表 |
| `gov.gate_warnings` | `gate_warnings` | string[] | 预测的闸门警告 |
| `gov.audit_level` | `audit_level` | string | 审计级别 (standard/enhanced/forensic) |

### ⚠️ 常见错误

- ❌ `gov.trust_tier` → ✅ `gov.inferred_trust_tier`
- ❌ `gov.risk_level` → ✅ `gov.inferred_risk_level`
- ❌ `gov.requires_admin_token` → ✅ `gov.requires_admin_token_for`（数组，不是布尔值）

### default_quota 对象结构

```javascript
gov.default_quota = {
    calls_per_minute: 500,
    max_concurrent: 5,
    max_runtime_ms: 30000
}
```

---

## Attach API

**后端**: `POST /api/mcp/marketplace/attach`

**请求体**:
```json
{
  "package_id": "agentos.official/echo-math",
  "override_trust_tier": "T1",  // 可选
  "custom_config": {...}        // 可选
}
```

**返回格式**:
```json
{
  "ok": true,
  "data": {
    "server_id": "echo-math",
    "status": "attached",
    "enabled": false,
    "trust_tier": "T1",
    "audit_id": "audit_abc123",
    "warnings": [...],
    "next_steps": [...]
  }
}
```

### Attach Response 字段映射

| 前端引用 | 后端字段 | 类型 | 说明 |
|---------|---------|------|------|
| `result.server_id` | `server_id` | string | 生成的 server ID |
| `result.status` | `status` | string | "attached" |
| `result.enabled` | `enabled` | boolean | **始终为 false**（默认 disabled） |
| `result.trust_tier` | `trust_tier` | string | 应用的信任层级 |
| `result.audit_id` | `audit_id` | string | 审计事件 ID |
| `result.warnings` | `warnings` | string[] | 警告列表 |
| `result.next_steps` | `next_steps` | string[] | 后续步骤 |

---

## 前端辅助方法

### Trust Tier Label 生成

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

### Package ID Sanitization

```javascript
/**
 * Sanitize package ID for HTML id attribute
 *
 * Package IDs like "agentos.official/echo-math" contain '/' and '.'
 * which are invalid in HTML id attributes
 */
sanitizeId(packageId) {
    return packageId.replace(/[^a-zA-Z0-9-_]/g, '-');
}
```

### Server ID 提取

```javascript
/**
 * Extract server ID from package ID or use provided server_id
 *
 * Package ID: "agentos.official/echo-math"
 * Server ID: "echo-math" (last segment)
 */
const serverId = pkg.server_id || pkg.package_id.split('/').pop();
```

---

## API 响应提取模式

### 统一提取模式

```javascript
// 获取数据
const response = await fetch('/api/mcp/marketplace/...');
const json = await response.json();

// 提取 data（如果返回格式是 {ok: true, data: {...}}）
const data = json.ok ? json.data : json;
```

### 推荐封装

```javascript
async function fetchMarketplaceAPI(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const json = await response.json();
    return json.ok ? json.data : json;
}

// 使用
const pkg = await fetchMarketplaceAPI(`/api/mcp/marketplace/packages/${id}`);
const gov = await fetchMarketplaceAPI(`/api/mcp/marketplace/governance-preview/${id}`);
```

---

## Admin Token 字段处理

### Package 级别（boolean）

```javascript
// 后端: requires_admin_token (boolean)
if (pkg.requires_admin_token) {
    console.log("This package requires admin token");
}
```

### Governance 级别（array）

```javascript
// 后端: requires_admin_token_for (string[])
// 示例: ["side_effects", "all_calls"]

if (gov.requires_admin_token_for && gov.requires_admin_token_for.length > 0) {
    console.log(`Admin token required for: ${gov.requires_admin_token_for.join(', ')}`);
}
```

### 显示逻辑

```javascript
// ✅ 正确
${gov.requires_admin_token_for && gov.requires_admin_token_for.length > 0
    ? `Yes (${gov.requires_admin_token_for.join(', ')})`
    : 'No'}

// ❌ 错误
${gov.requires_admin_token ? 'Yes' : 'No'}
```

---

## 完整示例

### MarketplaceView (列表页)

```javascript
renderPackageCard(pkg) {
    return `
        <div class="package-card" id="pkg-card-${this.sanitizeId(pkg.package_id)}">
            <h3>${pkg.name}</h3>
            <p>${pkg.author}</p>
            <p>${pkg.description}</p>
            <span class="badge">${pkg.tools_count} tools</span>
            <span class="trust-tier-badge ${pkg.recommended_trust_tier}">
                ${this.getTrustTierLabel(pkg.recommended_trust_tier)}
            </span>
            <span class="status ${pkg.is_connected ? 'connected' : 'not-connected'}">
                ${pkg.is_connected ? 'Connected' : 'Not Connected'}
            </span>
        </div>
    `;
}
```

### MCPPackageDetailView (详情页)

```javascript
async loadPackage() {
    const [pkgData, govData] = await Promise.all([
        fetch(`/api/mcp/marketplace/packages/${this.packageId}`).then(r => r.json()),
        fetch(`/api/mcp/marketplace/governance-preview/${this.packageId}`).then(r => r.json())
    ]);

    // 提取 data
    this.package = pkgData.ok ? pkgData.data : pkgData;
    this.governance = govData.ok ? govData.data : govData;

    this.render();
}

renderGovernancePreview() {
    const gov = this.governance;
    const tierLabel = this.getTrustTierLabel(gov.inferred_trust_tier);

    return `
        <div>
            <p>Trust Tier: ${gov.inferred_trust_tier} (${tierLabel})</p>
            <p>Risk Level: ${gov.inferred_risk_level}</p>
            <p>Default Quota: ${gov.default_quota.calls_per_minute} calls/min</p>
            <p>Admin Token: ${
                gov.requires_admin_token_for && gov.requires_admin_token_for.length > 0
                    ? `Yes (${gov.requires_admin_token_for.join(', ')})`
                    : 'No'
            }</p>
        </div>
    `;
}
```

---

## 测试清单

使用以下检查清单验证字段映射正确性：

### 列表页
- [ ] Trust Tier 显示正确（不是 "undefined"）
- [ ] 连接状态显示正确
- [ ] 点击卡片可跳转

### 详情页
- [ ] Package 信息完整显示
- [ ] Tools 列表正确
- [ ] Trust Tier 显示正确
- [ ] Risk Level 显示正确
- [ ] Admin Token 要求显示正确（数组内容）
- [ ] 治理预览区域无错误

### 浏览器控制台
- [ ] 无 "undefined" 错误
- [ ] 无 "is not defined" 错误
- [ ] 无字段访问错误

---

## 更新日志

- **2026-01-31**: 初始版本（基于 Hotfix 001）
- **2026-01-31**: 添加第二轮修复的字段映射

---

**维护**: 当后端 API 字段变更时，必须同步更新此文档。
