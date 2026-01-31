# Marketplace Security Model

**Version**: 1.0
**Last Updated**: 2026-01-30
**Status**: Design Complete

---

## Three-Gate Defense

Marketplace 采用三层防御策略，确保供应链安全。

### Gate-M1: Trust Chain (信任链)

**目标**: 确保下载的扩展包未被篡改

**机制**:
1. **Index → Zip SHA256 链**
   - Marketplace index.json 中每个扩展必须声明 sha256
   - 安装时强制校验：下载的 zip 的 sha256 必须匹配
   - 不匹配 → 拒绝安装 + 记录安全事件

2. **Source URL Recording**
   - 每次安装记录：source_url, sha256, marketplace_index_url, installed_at
   - 可追溯：哪个扩展来自哪个源
   - 可审计：检查所有安装的信任链

3. **HTTPS + Domain Whitelist**
   - 强制 HTTPS（拒绝 HTTP）
   - 可选域名白名单（默认允许所有 HTTPS）
   - 配置示例：
     ```python
     MARKETPLACE_DOMAIN_WHITELIST = [
         "marketplace.agentos.dev",
         "extensions.agentos.com"
     ]
     ```

**实现位置**: PR-M1（Marketplace Index 服务）

**测试要求**:
- test_marketplace_sha256_mismatch_rejected ✅
- test_marketplace_non_https_rejected ✅
- test_marketplace_domain_whitelist_enforced ✅

---

### Gate-M2: Rollback & Idempotency (回滚与幂等)

**目标**: 确保更新失败不会破坏系统

**机制**:
1. **Idempotency (幂等性)**
   - 相同版本重复安装 → 幂等返回成功，不重复执行
   - 不同版本 → 自动触发 update_extension()

2. **Update with Rollback (带回滚的更新)**
   - 备份旧版本：
     - 文件系统：复制到 .agentos/extensions/.backup/
     - 数据库：事务保护
   - 安装新版本：
     - 禁用旧版本 → 卸载 → 安装新版本 → 恢复 enabled 状态
   - 失败回滚：
     - 恢复文件系统（从备份复制回）
     - 恢复数据库记录（事务回滚）
     - 保持原 enabled 状态

3. **State Protection (状态保护)**
   - 最小保证：原 enabled 状态不被破坏
   - 即使回滚失败，也要尝试恢复 enabled 状态
   - 记录关键失败到审计日志（需要人工干预）

**实现位置**: PR-M1 或独立 PR

**测试要求**:
- test_extension_install_idempotent ✅
- test_extension_update_rollback_on_failure ✅
- test_extension_update_preserves_enabled_state ✅

---

### Gate-M3: Permission Risk Display (权限风险展示)

**目标**: 用户安装前了解扩展的权限风险

**机制**:
1. **Permission Badge (权限徽章)**
   - 卡片上显示所有权限
   - 颜色编码：
     - 🔴 Critical: exec（可执行系统命令）
     - 🟠 High: filesystem.write（可修改文件）
     - 🟡 Medium: network（可访问网络）
     - 🟢 Low: filesystem.read（可读文件）

2. **Pre-install Confirmation (安装前确认)**
   - 危险权限（exec, filesystem.write）→ 弹出警告对话框
   - 对话框内容：
     - 权限列表 + 风险说明
     - "只安装你信任的扩展"警告
     - "所有操作都被记录"提示
   - 用户明确确认后才能继续

3. **Remote Mode Warning (远程模式警告，v1.1+)**
   - 检测部署模式（local vs remote）
   - Remote 模式：
     - 显示更强的警告（网络暴露风险）
     - 要求 admin token（v1.1+）
     - 提示审计日志监控

**实现位置**: PR-M2（WebUI Marketplace 页面）

**测试要求**:
- test_permission_badges_displayed_correctly ✅
- test_dangerous_permission_shows_confirmation ✅
- test_remote_mode_shows_stronger_warning ✅ (v1.1+)

---

## Attack Scenarios & Mitigations

| Attack Vector | Mitigation | Gate |
|--------------|------------|------|
| **Man-in-the-middle** | HTTPS 强制 + SHA256 校验 | M1 |
| **Malicious marketplace** | 域名白名单 | M1 |
| **Tampered extension** | SHA256 mismatch → 拒绝 | M1 |
| **Supply chain poisoning** | 审计日志 + source_url 记录 | M1 |
| **Version rollback attack** | SHA256 + 版本号联合校验 | M1 |
| **Failed update breaks system** | 回滚机制 + 状态保护 | M2 |
| **User installs malicious extension** | 权限 badge + 确认对话框 | M3 |
| **Silent permission escalation** | 明确显示所有权限 | M3 |

---

## Security Assumptions

**Assumed Trusted**:
- Marketplace index.json 的提供者（marketplace.agentos.dev）
- HTTPS/TLS 证书体系
- 用户自己的判断（在看到权限后）

**Not Trusted**:
- 扩展作者（除非 verified badge）
- 网络传输路径（因此用 HTTPS + SHA256）
- 扩展代码本身（因此有沙箱 + 审计）

---

## Implementation Details

### Gate-M1: Trust Chain Implementation

#### 1. Index Schema with Mandatory SHA256

**File**: `agentos/core/marketplace/schemas.py`

```python
"""Marketplace index schemas with security enhancements"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field, validator

class MarketplaceExtension(BaseModel):
    """Single extension in marketplace with trust chain"""
    id: str = Field(description="Unique extension ID")
    name: str = Field(description="Human-readable name")
    version: str = Field(description="Semantic version (e.g., '0.1.0')")
    author: str = Field(description="Extension author")
    description: str = Field(description="Brief description")
    zip_url: HttpUrl = Field(description="HTTPS URL to download ZIP")
    sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA256 hash of the extension zip file (lowercase hex)"
    )
    min_agentos_version: str = Field(description="Minimum AgentOS version")
    tags: List[str] = Field(default_factory=list, description="Category tags")
    icon_url: Optional[HttpUrl] = Field(default=None, description="Icon URL")
    downloads: int = Field(default=0, ge=0, description="Download count")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="User rating")
    verified: bool = Field(default=False, description="Official verification status")
    permissions_required: List[str] = Field(
        default_factory=list,
        description="Permissions required by this extension"
    )

    @validator('zip_url')
    def validate_https(cls, v):
        """Enforce HTTPS for all extension URLs"""
        if v.scheme != 'https':
            raise ValueError('zip_url must use HTTPS')
        return v

class MarketplaceIndex(BaseModel):
    """Marketplace index schema"""
    version: str = Field(description="Index schema version")
    last_updated: datetime = Field(description="Last update timestamp")
    extensions: List[MarketplaceExtension] = Field(description="Extension list")
```

#### 2. Installation with Trust Chain Validation

**File**: `agentos/core/marketplace/service.py`

Add to the MarketplaceService class:

```python
def install_from_marketplace(
    self,
    extension_entry: MarketplaceExtension
) -> InstallResult:
    """
    从 Marketplace 安装扩展（带信任链校验）

    Args:
        extension_entry: Marketplace extension metadata

    Returns:
        InstallResult with success/failure details

    Raises:
        SecurityError: On SHA256 mismatch or other security violations
    """
    logger.info(f"Installing {extension_entry.id} from marketplace")

    # 1. 下载 zip
    logger.info(f"Downloading {extension_entry.zip_url}")
    zip_path = self.downloader.download(
        url=str(extension_entry.zip_url),
        expected_sha256=extension_entry.sha256  # 强制校验
    )

    # 2. 双重 SHA256 校验（下载器已校验，这里再验证一次）
    actual_sha256 = self.validator.calculate_sha256(zip_path)
    if actual_sha256 != extension_entry.sha256:
        raise SecurityError(
            error_code="SHA256_MISMATCH",
            message=f"SHA256 mismatch for {extension_entry.id}",
            details={
                "expected": extension_entry.sha256,
                "actual": actual_sha256,
                "source": str(extension_entry.zip_url)
            },
            hint="Possible tampering detected. Do not proceed."
        )

    # 3. 记录信任链到数据库
    self.registry.record_install_source(
        extension_id=extension_entry.id,
        version=extension_entry.version,
        source="marketplace",
        source_url=str(extension_entry.zip_url),
        sha256=actual_sha256,
        marketplace_index_url=self.config.MARKETPLACE_INDEX_URL,
        installed_at=datetime.now()
    )

    # 4. 继续正常安装流程
    return self.installer.install_from_zip(zip_path)
```

#### 3. Domain Whitelist Configuration

**File**: `agentos/config.py`

Add marketplace configuration:

```python
class MarketplaceConfig(BaseSettings):
    """Marketplace security configuration"""

    MARKETPLACE_INDEX_URL: str = "https://marketplace.agentos.dev/index.json"
    MARKETPLACE_CACHE_TTL: int = 3600
    MARKETPLACE_DOMAIN_WHITELIST: List[str] = Field(
        default_factory=lambda: [
            "marketplace.agentos.dev",
            "extensions.agentos.com"
        ],
        description="Allowed domains for extension downloads (empty = allow all HTTPS)"
    )

    def validate_extension_url(self, url: str) -> None:
        """验证扩展 URL 是否在白名单内"""
        from urllib.parse import urlparse
        parsed = urlparse(url)

        # HTTPS 强制
        if parsed.scheme != "https":
            raise SecurityError(
                f"Extension URL must use HTTPS: {url}"
            )

        # 域名白名单（如果配置了）
        if self.MARKETPLACE_DOMAIN_WHITELIST:
            if parsed.netloc not in self.MARKETPLACE_DOMAIN_WHITELIST:
                raise SecurityError(
                    f"Domain {parsed.netloc} not in whitelist: "
                    f"{self.MARKETPLACE_DOMAIN_WHITELIST}"
                )
```

#### 4. Database Schema Extensions

**SQL Migration**:

```sql
-- 在 extensions 表中添加 source tracking 字段
ALTER TABLE extensions ADD COLUMN source_type TEXT; -- 'upload', 'url', 'marketplace'
ALTER TABLE extensions ADD COLUMN source_url TEXT;
ALTER TABLE extensions ADD COLUMN marketplace_index_url TEXT;
ALTER TABLE extensions ADD COLUMN trust_chain_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE extensions ADD COLUMN installed_at TIMESTAMP;

-- 创建索引
CREATE INDEX idx_extensions_source ON extensions(source_type, source_url);
CREATE INDEX idx_extensions_trust ON extensions(trust_chain_verified);
```

---

### Gate-M2: Rollback & Idempotency Implementation

#### 1. Idempotent Installation

**File**: `agentos/core/extensions/registry.py`

Add to ExtensionRegistry class:

```python
def install_extension(
    self,
    zip_path: Path,
    source: str = "upload"
) -> InstallResult:
    """安装扩展（幂等）"""
    # 提取 manifest
    manifest = self.validator.extract_manifest(zip_path)

    # 幂等性检查
    existing = self.get_extension(manifest.id)
    if existing:
        if existing.version == manifest.version:
            # 相同版本：幂等返回成功
            logger.info(
                f"Extension {manifest.id} v{manifest.version} "
                f"already installed (idempotent)"
            )
            return InstallResult(
                success=True,
                message="Already installed (idempotent)",
                extension_id=manifest.id,
                version=manifest.version,
                skipped=True
            )
        else:
            # 不同版本：调用 update_extension
            logger.info(
                f"Updating {manifest.id} from v{existing.version} "
                f"to v{manifest.version}"
            )
            return self.update_extension(manifest.id, zip_path)

    # 新安装：继续正常流程
    return self._install_new_extension(zip_path, source)
```

#### 2. Update with Rollback

```python
def update_extension(
    self,
    extension_id: str,
    new_zip: Path
) -> InstallResult:
    """更新扩展（带回滚）"""
    # 1. 备份当前状态
    old_state = self.get_extension(extension_id)
    if not old_state:
        raise ExtensionNotFoundError(extension_id)

    old_version = old_state.version
    old_enabled = old_state.enabled
    old_path = Path(f".agentos/extensions/{extension_id}/")
    backup_path = Path(
        f".agentos/extensions/.backup/{extension_id}-{old_version}/"
    )

    # 2. 创建文件系统备份
    logger.info(f"Backing up {extension_id} v{old_version}")
    if backup_path.exists():
        shutil.rmtree(backup_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(old_path, backup_path)

    # 3. 使用数据库事务保护
    try:
        with self.db.transaction():
            # 3.1 禁用旧版本（保证服务不中断）
            if old_enabled:
                self.disable_extension(extension_id)

            # 3.2 卸载旧版本
            self.uninstall_extension(extension_id)

            # 3.3 安装新版本
            result = self._install_new_extension(new_zip, source="update")

            if not result.success:
                raise InstallError(
                    f"New version install failed: {result.error}"
                )

            # 3.4 恢复启用状态
            if old_enabled:
                self.enable_extension(extension_id)

            logger.info(
                f"Successfully updated {extension_id} from "
                f"v{old_version} to v{result.version}"
            )

            # 3.5 清理备份
            shutil.rmtree(backup_path)

            return result

    except Exception as e:
        logger.error(
            f"Update failed for {extension_id}, rolling back to "
            f"v{old_version}: {e}"
        )

        # 4. 回滚
        try:
            # 4.1 恢复文件系统
            if old_path.exists():
                shutil.rmtree(old_path)
            shutil.copytree(backup_path, old_path)

            # 4.2 恢复数据库记录（事务已自动回滚）
            # 但需要确保文件系统和数据库一致
            self._restore_extension_state(old_state)

            logger.info(f"Rolled back to v{old_version}")

        except Exception as rollback_error:
            logger.critical(
                f"Rollback failed for {extension_id}: {rollback_error}. "
                f"Manual intervention required."
            )
            raise InstallError(
                f"Update failed and rollback also failed: {rollback_error}"
            )

        raise InstallError(
            f"Update failed and rolled back to v{old_version}: {e}"
        )

def _restore_extension_state(self, old_state: ExtensionRecord):
    """恢复扩展状态（内部方法）"""
    # 重新插入数据库记录
    # 恢复所有字段：enabled, version, sha256, source, etc.
    self.db.execute(
        """
        INSERT INTO extensions (id, name, version, enabled, sha256, source_type,
                               source_url, installed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (old_state.id, old_state.name, old_state.version, old_state.enabled,
         old_state.sha256, old_state.source_type, old_state.source_url,
         old_state.installed_at)
    )
```

---

### Gate-M3: Permission Risk Display Implementation

#### 1. Permission Badge CSS

**File**: `agentos/webui/static/css/marketplace.css`

Add permission badge styles:

```css
.extension-permissions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.permission-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
}

.permission-critical {
  background: #ff4444;
  color: white;
}

.permission-high {
  background: #ff8800;
  color: white;
}

.permission-medium {
  background: #ffaa00;
  color: #222;
}

.permission-low {
  background: #44ff44;
  color: #222;
}

.permission-badge::before {
  margin-right: 4px;
}

.permission-badge.permission-critical::before {
  content: "⚠️";
}

.permission-badge.permission-high::before {
  content: "🔴";
}

.permission-badge.permission-medium::before {
  content: "🟡";
}

.permission-badge.permission-low::before {
  content: "🟢";
}
```

#### 2. Permission Badge JavaScript

**File**: `agentos/webui/static/js/views/MarketplaceView.js`

Add permission rendering:

```javascript
function renderPermissionBadges(permissions) {
  const permissionLevels = {
    'exec': 'critical',
    'filesystem.write': 'high',
    'network': 'medium',
    'filesystem.read': 'low'
  };

  return permissions.map(perm => {
    const level = permissionLevels[perm] || 'medium';
    return `<span class="permission-badge permission-${level}">${perm}</span>`;
  }).join('');
}
```

#### 3. Pre-install Confirmation Dialog

```javascript
async function installExtension(extensionId, extensionData) {
  const permissions = extensionData.permissions_required;

  // 检查危险权限
  const criticalPerms = permissions.filter(p => p === 'exec');
  const highPerms = permissions.filter(p =>
    ['filesystem.write', 'network'].includes(p)
  );

  if (criticalPerms.length > 0 || highPerms.length > 0) {
    // 显示警告对话框
    const confirmed = await showSecurityWarning({
      title: '⚠️ Security Warning',
      extensionName: extensionData.name,
      permissions: permissions,
      message: buildPermissionWarningMessage(permissions),
      confirmButton: {
        text: 'I Understand, Install Anyway',
        style: 'danger'
      },
      cancelButton: {
        text: 'Cancel',
        style: 'default'
      }
    });

    if (!confirmed) {
      return;
    }
  }

  // 继续安装
  const response = await fetch('/api/extensions/install-url', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      url: extensionData.zip_url,
      sha256: extensionData.sha256
    })
  });

  // 显示进度...
}

function buildPermissionWarningMessage(permissions) {
  const messages = {
    'exec': '⚠️ Can execute system commands (highest risk)',
    'filesystem.write': '🔴 Can modify files on your system',
    'network': '🟡 Can access external networks',
    'filesystem.read': '🟢 Can read files (limited risk)'
  };

  const permList = permissions.map(p =>
    `<li><strong>${p}:</strong> ${messages[p] || 'Unknown permission'}</li>`
  ).join('');

  return `
    <p>This extension requires the following permissions:</p>
    <ul style="text-align: left; margin: 16px 0;">
      ${permList}
    </ul>
    <p><strong>Only install extensions you trust.</strong></p>
    <p>All actions are logged for audit.</p>
  `;
}
```

#### 4. Remote Mode Warning (v1.1+)

```javascript
// 在未来 v1.1+ 实现 admin token 后启用
async function installExtensionRemoteMode(extensionId, extensionData) {
  // 检测部署模式（从配置或 API 获取）
  const deploymentMode = await fetch('/api/system/deployment-mode')
    .then(r => r.json())
    .then(d => d.mode);

  if (deploymentMode === 'remote') {
    const confirmed = await showRemoteWarning({
      title: '⚠️ Remote Deployment Warning',
      message: `
        <p>You are installing an extension on a <strong>network-exposed instance</strong>.</p>
        <p>This extension will have access to:</p>
        <ul>
          <li>Server file system</li>
          <li>Network resources</li>
          <li>Potentially sensitive data</li>
        </ul>
        <p><strong>Make sure you trust the extension author.</strong></p>
        <p>All actions are logged and require admin approval.</p>
      `,
      requireAdminToken: true  // v1.1+ 功能
    });

    if (!confirmed) {
      return;
    }
  }

  // 继续安装...
}
```

---

## Testing Requirements

### Gate-M1 Tests

**File**: `tests/unit/core/marketplace/test_trust_chain.py`

```python
def test_marketplace_sha256_mismatch_rejected():
    """测试：SHA256 不匹配时拒绝安装"""
    service = MarketplaceService()

    entry = MarketplaceExtension(
        id="test.extension",
        name="Test Extension",
        version="1.0.0",
        zip_url="https://marketplace.agentos.dev/test.zip",
        sha256="abc123...",  # 错误的 hash
        # ... other fields
    )

    with pytest.raises(SecurityError) as exc_info:
        service.install_from_marketplace(entry)

    assert "SHA256_MISMATCH" in str(exc_info.value)

def test_marketplace_non_https_rejected():
    """测试：HTTP URL 被拒绝"""
    with pytest.raises(ValueError) as exc_info:
        MarketplaceExtension(
            zip_url="http://example.com/test.zip",  # HTTP instead of HTTPS
            # ... other fields
        )

    assert "HTTPS" in str(exc_info.value)

def test_marketplace_domain_whitelist_enforced():
    """测试：域名白名单生效"""
    config = MarketplaceConfig(
        MARKETPLACE_DOMAIN_WHITELIST=["marketplace.agentos.dev"]
    )

    # 白名单内的域名应该通过
    config.validate_extension_url("https://marketplace.agentos.dev/test.zip")

    # 白名单外的域名应该被拒绝
    with pytest.raises(SecurityError):
        config.validate_extension_url("https://evil.com/malware.zip")
```

### Gate-M2 Tests

**File**: `tests/unit/core/extensions/test_rollback.py`

```python
def test_extension_install_idempotent():
    """测试幂等性：重复安装相同版本"""
    registry = ExtensionRegistry()

    # 安装一次
    result1 = registry.install_extension(hello_zip)
    assert result1.success

    # 再安装一次
    result2 = registry.install_extension(hello_zip)
    assert result2.success
    assert result2.skipped == True
    assert result2.message == "Already installed (idempotent)"

def test_extension_update_rollback_on_failure():
    """测试回滚：更新失败时回滚到旧版本"""
    registry = ExtensionRegistry()

    # 安装旧版本
    registry.install_extension(postman_v1_zip)
    old_state = registry.get_extension("tools.postman")

    # 尝试安装有问题的新版本（会失败）
    with pytest.raises(InstallError):
        registry.update_extension("tools.postman", broken_v2_zip)

    # 验证回滚成功
    current_state = registry.get_extension("tools.postman")
    assert current_state.version == old_state.version
    assert current_state.enabled == old_state.enabled

def test_extension_update_preserves_enabled_state():
    """测试：更新保持启用状态"""
    registry = ExtensionRegistry()

    # 安装并启用
    registry.install_extension(postman_v1_zip)
    registry.enable_extension("tools.postman")

    # 更新到新版本
    registry.update_extension("tools.postman", postman_v2_zip)

    # 验证仍然启用
    current_state = registry.get_extension("tools.postman")
    assert current_state.enabled == True
```

### Gate-M3 Tests

**File**: `tests/integration/webui/test_marketplace_ui.py`

```python
def test_permission_badges_displayed_correctly():
    """测试：权限徽章正确显示"""
    # 访问 marketplace 页面
    response = client.get('/extensions/marketplace')
    assert response.status_code == 200

    # 检查权限徽章存在
    html = response.text
    assert 'permission-badge' in html
    assert 'permission-critical' in html  # exec 权限
    assert 'permission-high' in html  # filesystem.write

def test_dangerous_permission_shows_confirmation():
    """测试：危险权限显示确认对话框"""
    # 模拟点击安装按钮
    # （需要 UI 测试框架如 Playwright/Selenium）

def test_remote_mode_shows_stronger_warning():
    """测试：远程模式显示更强警告（v1.1+）"""
    # 设置远程模式
    # 验证警告对话框内容更严格
```

---

## Future Enhancements (v2)

1. **Code Signing**
   - 扩展包用私钥签名
   - Marketplace 验证签名（而不只是 SHA256）

2. **Extension Reputation**
   - 下载量、评分、举报记录
   - 自动标记可疑扩展

3. **Sandboxed Preview**
   - 安装前在沙箱中预览扩展行为
   - 显示实际执行的命令

4. **Community Review**
   - 扩展源码公开
   - 社区审核 + verified badge

---

## Compliance

这 3 个 Gate 确保 Marketplace 符合以下安全标准：
- ✅ OWASP Top 10 (Supply Chain Attacks)
- ✅ CIS Controls (Software Asset Management)
- ✅ NIST Cybersecurity Framework (Integrity Checking)

---

**Next Review**: v2.0 Marketplace (Code Signing)
