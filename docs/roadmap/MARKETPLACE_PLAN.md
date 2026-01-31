# Marketplace Implementation Plan

**Date**: 2026-01-30
**Status**: PLANNING
**Author**: System Planning Agent

## Overview

This document outlines the implementation plan for the AgentOS **Marketplace** (Extension Market), which will provide a centralized directory for discovering and installing extensions. The implementation follows the **Index-Only Architecture** principle: Marketplace provides an index, but does not change the installation execution mechanism.

**Key Principle**: Marketplace is an index, not an executor. All installations continue to go through Core's controlled execution engine.

## Core Principles

1. **Marketplace Only as Index**
   - Marketplace provides extension list (index.json)
   - Installation still goes through Core's controlled executor
   - No direct code execution from Marketplace

2. **Security First**
   - HTTPS only
   - Optional domain whitelist
   - SHA256 mandatory verification
   - Schema validation
   - Never execute any Marketplace code

3. **Backward Compatibility**
   - Leverages existing Extension system (PR-A/B/C)
   - Reuses existing API: `POST /api/extensions/install-url`
   - No changes to installation mechanism

## PR-M1: Marketplace Index Service (Core)

**Goal**: Provide a configurable Marketplace index service that fetches, caches, and validates extension listings.

**Estimated Time**: 3-5 days

### 1. Configuration Design

**File**: `agentos/core/marketplace/config.py` (new)

```python
"""Marketplace configuration settings"""

import os
from typing import List, Optional

# Primary marketplace index URL
MARKETPLACE_INDEX_URL = os.getenv(
    "MARKETPLACE_INDEX_URL",
    "https://marketplace.agentos.dev/index.json"
)

# Cache TTL in seconds (default: 1 hour)
MARKETPLACE_CACHE_TTL = int(os.getenv(
    "MARKETPLACE_CACHE_TTL",
    "3600"
))

# Domain whitelist for marketplace URLs
# Empty list = allow all HTTPS URLs
MARKETPLACE_DOMAIN_WHITELIST: List[str] = os.getenv(
    "MARKETPLACE_DOMAIN_WHITELIST",
    ""
).split(",") if os.getenv("MARKETPLACE_DOMAIN_WHITELIST") else []

# Example values:
# MARKETPLACE_DOMAIN_WHITELIST = [
#     "marketplace.agentos.dev",
#     "extensions.agentos.com"
# ]

# Request timeout in seconds
MARKETPLACE_REQUEST_TIMEOUT = int(os.getenv(
    "MARKETPLACE_REQUEST_TIMEOUT",
    "10"
))

# Cache directory
MARKETPLACE_CACHE_DIR = ".agentos/marketplace"
```

### 2. API Design

**Endpoint**: `GET /api/marketplace/index`

**Query Parameters**:
- `force_refresh: bool = False` - Force refresh cache (bypass TTL)

**Response Schema**:
```json
{
  "version": "1.0",
  "last_updated": "2026-01-30T10:00:00Z",
  "extensions": [
    {
      "id": "tools.postman",
      "name": "Postman Toolkit",
      "version": "0.1.0",
      "author": "AgentOS Team",
      "description": "API testing and response explanation toolkit",
      "zip_url": "https://marketplace.agentos.dev/extensions/postman-v0.1.0.zip",
      "sha256": "abc123def456...",
      "min_agentos_version": "1.0.0",
      "tags": ["api", "testing", "http"],
      "icon_url": "https://marketplace.agentos.dev/icons/postman.png",
      "downloads": 1234,
      "rating": 4.5,
      "verified": true
    }
  ]
}
```

**Error Response**:
```json
{
  "ok": false,
  "data": null,
  "error": "Failed to fetch marketplace index",
  "hint": "Using cached version from 2026-01-30T09:00:00Z",
  "reason_code": "MARKETPLACE_FETCH_FAILED"
}
```

### 3. Implementation Details

#### File Structure
```
agentos/core/marketplace/
├── __init__.py
├── config.py          # Configuration settings
├── client.py          # HTTP client for fetching index
├── cache.py           # Cache management
├── schemas.py         # Pydantic schemas
└── service.py         # Business logic
```

#### Core Components

**A. Pydantic Schemas** (`schemas.py`)
```python
"""Marketplace index schemas"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field

class MarketplaceExtension(BaseModel):
    """Single extension in marketplace"""
    id: str = Field(description="Unique extension ID")
    name: str = Field(description="Human-readable name")
    version: str = Field(description="Semantic version (e.g., '0.1.0')")
    author: str = Field(description="Extension author")
    description: str = Field(description="Brief description")
    zip_url: HttpUrl = Field(description="HTTPS URL to download ZIP")
    sha256: str = Field(min_length=64, max_length=64, description="SHA256 hash")
    min_agentos_version: str = Field(description="Minimum AgentOS version")
    tags: List[str] = Field(default_factory=list, description="Category tags")
    icon_url: Optional[HttpUrl] = Field(default=None, description="Icon URL")
    downloads: int = Field(default=0, ge=0, description="Download count")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="User rating")
    verified: bool = Field(default=False, description="Official verification status")

class MarketplaceIndex(BaseModel):
    """Marketplace index schema"""
    version: str = Field(description="Index schema version")
    last_updated: datetime = Field(description="Last update timestamp")
    extensions: List[MarketplaceExtension] = Field(description="Extension list")
```

**B. Cache Manager** (`cache.py`)
```python
"""Marketplace cache management"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from agentos.store import get_store_path
from .config import MARKETPLACE_CACHE_TTL, MARKETPLACE_CACHE_DIR
from .schemas import MarketplaceIndex

class MarketplaceCache:
    """Manages marketplace index cache"""

    def __init__(self):
        self.cache_dir = Path(get_store_path("")) / MARKETPLACE_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "index_cache.json"
        self.meta_file = self.cache_dir / "index_meta.json"

    def get(self) -> Optional[MarketplaceIndex]:
        """Get cached index if valid"""
        if not self.cache_file.exists() or not self.meta_file.exists():
            return None

        # Check cache age
        meta = json.loads(self.meta_file.read_text())
        cached_at = datetime.fromisoformat(meta["cached_at"])
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()

        if age > MARKETPLACE_CACHE_TTL:
            return None  # Cache expired

        # Load and validate
        try:
            index_data = json.loads(self.cache_file.read_text())
            return MarketplaceIndex(**index_data)
        except Exception as e:
            logger.warning(f"Invalid cache, ignoring: {e}")
            return None

    def save(self, index: MarketplaceIndex, etag: Optional[str] = None):
        """Save index to cache"""
        # Save index data
        self.cache_file.write_text(index.model_dump_json(indent=2))

        # Save metadata
        meta = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "etag": etag
        }
        self.meta_file.write_text(json.dumps(meta, indent=2))

    def get_etag(self) -> Optional[str]:
        """Get cached ETag for conditional request"""
        if not self.meta_file.exists():
            return None
        meta = json.loads(self.meta_file.read_text())
        return meta.get("etag")
```

**C. HTTP Client** (`client.py`)
```python
"""Marketplace HTTP client"""

import logging
import requests
from typing import Optional, Tuple
from .config import (
    MARKETPLACE_INDEX_URL,
    MARKETPLACE_REQUEST_TIMEOUT,
    MARKETPLACE_DOMAIN_WHITELIST
)
from .schemas import MarketplaceIndex

logger = logging.getLogger(__name__)

class MarketplaceClient:
    """HTTP client for fetching marketplace index"""

    def fetch_index(
        self,
        etag: Optional[str] = None
    ) -> Tuple[Optional[MarketplaceIndex], Optional[str], bool]:
        """
        Fetch marketplace index from remote

        Args:
            etag: ETag from previous fetch for conditional request

        Returns:
            Tuple of (index, etag, is_modified)
            - index: MarketplaceIndex or None if 304 Not Modified
            - etag: New ETag from response
            - is_modified: True if content changed, False if 304

        Raises:
            Exception: On network error or validation failure
        """
        url = MARKETPLACE_INDEX_URL

        # Security: Enforce HTTPS
        if not url.startswith("https://"):
            raise ValueError("Marketplace index URL must use HTTPS")

        # Security: Check domain whitelist
        if MARKETPLACE_DOMAIN_WHITELIST:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain not in MARKETPLACE_DOMAIN_WHITELIST:
                raise ValueError(
                    f"Domain {domain} not in whitelist: {MARKETPLACE_DOMAIN_WHITELIST}"
                )

        # Prepare headers
        headers = {"User-Agent": "AgentOS-Marketplace/1.0"}
        if etag:
            headers["If-None-Match"] = etag

        # Make request
        logger.info(f"Fetching marketplace index from: {url}")
        response = requests.get(
            url,
            headers=headers,
            timeout=MARKETPLACE_REQUEST_TIMEOUT
        )

        # Handle 304 Not Modified
        if response.status_code == 304:
            logger.info("Index not modified (304)")
            return None, etag, False

        # Handle errors
        response.raise_for_status()

        # Parse and validate
        index_data = response.json()
        index = MarketplaceIndex(**index_data)

        # Get new ETag
        new_etag = response.headers.get("ETag")

        logger.info(
            f"Fetched index: {len(index.extensions)} extensions, "
            f"last_updated={index.last_updated}"
        )

        return index, new_etag, True
```

**D. Service Layer** (`service.py`)
```python
"""Marketplace service business logic"""

import logging
from typing import Optional
from .client import MarketplaceClient
from .cache import MarketplaceCache
from .schemas import MarketplaceIndex

logger = logging.getLogger(__name__)

class MarketplaceService:
    """Marketplace index service"""

    def __init__(self):
        self.client = MarketplaceClient()
        self.cache = MarketplaceCache()

    def get_index(self, force_refresh: bool = False) -> MarketplaceIndex:
        """
        Get marketplace index (cached or fresh)

        Args:
            force_refresh: Force refresh, bypassing cache

        Returns:
            MarketplaceIndex

        Raises:
            Exception: On fetch failure with no valid cache
        """
        # Try cache first (unless force_refresh)
        if not force_refresh:
            cached = self.cache.get()
            if cached:
                logger.info("Using cached marketplace index")
                return cached

        # Fetch from remote
        try:
            etag = self.cache.get_etag() if not force_refresh else None
            index, new_etag, is_modified = self.client.fetch_index(etag)

            if is_modified and index:
                # Save to cache
                self.cache.save(index, new_etag)
                return index
            else:
                # Not modified, return cached
                cached = self.cache.get()
                if cached:
                    return cached
                # Should not happen, but fallback
                raise Exception("Index not modified but no cache available")

        except Exception as e:
            logger.error(f"Failed to fetch marketplace index: {e}")

            # Fallback to cache (even if expired)
            cached = self.cache.get()
            if cached:
                logger.warning("Using expired cache as fallback")
                return cached

            # No cache available
            raise Exception(
                f"Failed to fetch marketplace index and no cache available: {e}"
            )
```

#### E. API Endpoint** (`agentos/webui/api/marketplace.py` - new)
```python
"""Marketplace API endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from agentos.core.marketplace.service import MarketplaceService
from agentos.webui.api.contracts import ReasonCode

router = APIRouter()
_service = None

def get_service() -> MarketplaceService:
    global _service
    if _service is None:
        _service = MarketplaceService()
    return _service

@router.get("/api/marketplace/index")
async def get_marketplace_index(
    force_refresh: bool = Query(False, description="Force refresh cache")
) -> Dict[str, Any]:
    """
    Get marketplace extension index

    Returns:
    {
      "version": "1.0",
      "last_updated": "2026-01-30T10:00:00Z",
      "extensions": [...]
    }
    """
    try:
        service = get_service()
        index = service.get_index(force_refresh=force_refresh)
        return index.model_dump(mode="json")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "data": None,
                "error": f"Failed to fetch marketplace index: {str(e)}",
                "hint": "Try again later or check MARKETPLACE_INDEX_URL configuration",
                "reason_code": ReasonCode.MARKETPLACE_FETCH_FAILED
            }
        )
```

### 4. Security Considerations (Gate-M1: Trust Chain)

**A. HTTPS Enforcement**
- Marketplace index URL **MUST** use HTTPS
- Reject HTTP URLs at validation time
- Error: "Marketplace index URL must use HTTPS"

**B. Domain Whitelist (Optional)**
- Configurable via `MARKETPLACE_DOMAIN_WHITELIST` env var
- Empty list = allow all HTTPS domains
- Non-empty list = only allow listed domains
- Example: `MARKETPLACE_DOMAIN_WHITELIST=marketplace.agentos.dev,extensions.example.com`

**C. Schema Validation**
- All index data validated via Pydantic schemas
- Invalid schema = reject entire index
- SHA256 format validated (exactly 64 hex chars)
- Version format validated (semantic versioning)

**D. Timeout Protection**
- Default timeout: 10 seconds
- Configurable via `MARKETPLACE_REQUEST_TIMEOUT`
- Prevents hanging on slow/malicious servers

**E. Cache Fallback**
- On network error, fallback to last cached version
- Even expired cache is better than no index
- Log warning: "Using expired cache as fallback"

**F. Trust Chain Enforcement (Gate-M1)**
- **SHA256 Mandatory Validation**:
  - Index schema enforces 64-character hex SHA256 field
  - Validator enforces `@validator('zip_url')` to require HTTPS
  - Double-check SHA256 during installation (downloader + installer)
  - Mismatch → SecurityError with error_code="SHA256_MISMATCH"

- **Source URL Recording**:
  - Record to database: `source_type`, `source_url`, `marketplace_index_url`, `installed_at`
  - Create indexes on `(source_type, source_url)` for audit queries
  - Field `trust_chain_verified` to indicate successful validation

- **Domain Whitelist**:
  - Add `validate_extension_url()` method in MarketplaceConfig
  - Check domain against whitelist before download
  - Raise SecurityError if domain not in whitelist

See `docs/security/MARKETPLACE_SECURITY.md` for full Gate-M1 implementation details.

### 5. Error Handling

| Error Scenario | Behavior | User Experience |
|----------------|----------|-----------------|
| Network error | Use cached index (even if expired) | Show warning banner |
| Invalid schema | Reject index, use cache | Error message with hint |
| HTTPS violation | Reject immediately | Configuration error |
| Domain not whitelisted | Reject immediately | Configuration error |
| Timeout | Use cached index | Show warning banner |
| No cache available | Return error | Cannot fetch index |

### 6. Testing Requirements

**Unit Tests** (`tests/unit/core/marketplace/`):
1. `test_schema_validation` - Valid/invalid index data
2. `test_https_enforcement` - Reject HTTP URLs
3. `test_domain_whitelist` - Allow/reject domains
4. `test_cache_ttl` - Cache expiration logic
5. `test_cache_fallback` - Use cache on error
6. `test_etag_support` - 304 Not Modified handling

**Integration Tests** (`tests/integration/marketplace/`):
1. `test_fetch_real_index` - Fetch from real endpoint (if available)
2. `test_cache_persistence` - Save and load cache
3. `test_api_endpoint` - GET /api/marketplace/index

**Security Tests (Gate-M1)**:
1. `test_marketplace_sha256_mismatch_rejected` - SHA256 不匹配时拒绝安装
2. `test_marketplace_non_https_rejected` - HTTP URL 被拒绝
3. `test_marketplace_domain_whitelist_enforced` - 域名白名单生效
4. `test_trust_chain_recorded` - 信任链记录到数据库

**Rollback Tests (Gate-M2)**:
1. `test_extension_install_idempotent` - 幂等性：重复安装相同版本
2. `test_extension_update_rollback_on_failure` - 更新失败时回滚
3. `test_extension_update_preserves_enabled_state` - 更新保持启用状态

---

## PR-M2: WebUI Marketplace Page

**Goal**: Create a user-friendly extension marketplace browsing and installation interface.

**Estimated Time**: 5-7 days

### 1. Routing

**New Route**: `/extensions/marketplace`

**Navigation Flow**:
- `/extensions` - Installed extensions (existing)
- `/extensions/marketplace` - Extension marketplace (new)

**URL Structure**:
```
/extensions/marketplace
/extensions/marketplace?search=postman
/extensions/marketplace?tag=api
/extensions/marketplace?sort=popular
```

### 2. Page Structure

**File**: `agentos/webui/static/js/views/MarketplaceView.js` (new)

```javascript
class MarketplaceView {
    constructor() {
        this.extensions = [];
        this.installedIds = new Set();
        this.searchTerm = '';
        this.selectedTag = 'all';
        this.sortBy = 'popular';
    }

    async init() {
        await this.fetchMarketplaceIndex();
        await this.fetchInstalledExtensions();
        this.render();
    }

    async fetchMarketplaceIndex() {
        const response = await fetch('/api/marketplace/index');
        const data = await response.json();
        this.extensions = data.extensions;
    }

    async fetchInstalledExtensions() {
        const response = await fetch('/api/extensions');
        const data = await response.json();
        this.installedIds = new Set(data.extensions.map(e => e.id));
    }

    render() {
        const filtered = this.filterExtensions();
        const sorted = this.sortExtensions(filtered);

        const html = `
            ${this.renderHeader()}
            ${this.renderFilters()}
            ${this.renderGrid(sorted)}
        `;

        document.querySelector('#marketplace-container').innerHTML = html;
        this.attachEventListeners();
    }

    // ... (implementation details)
}
```

### 3. UI Components

#### A. Page Header

**HTML Structure**:
```html
<div class="marketplace-page">
  <div class="marketplace-header">
    <h1>Extension Marketplace</h1>
    <p class="subtitle">Discover and install extensions to enhance AgentOS</p>

    <div class="search-bar">
      <input
        type="text"
        placeholder="Search extensions..."
        class="search-input"
        id="marketplace-search"
      >
      <button class="search-button">
        <svg><!-- Search icon --></svg>
      </button>
    </div>
  </div>

  <!-- ... -->
</div>
```

**CSS** (`agentos/webui/static/css/marketplace.css` - new):
```css
.marketplace-header {
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;
}

.marketplace-header h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.marketplace-header .subtitle {
  font-size: 1.1rem;
  opacity: 0.9;
  margin-bottom: 2rem;
}

.search-bar {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.search-input {
  flex: 1;
  padding: 1rem;
  border: none;
  font-size: 1rem;
  outline: none;
}

.search-button {
  padding: 1rem 1.5rem;
  background: #667eea;
  border: none;
  cursor: pointer;
  transition: background 0.2s;
}

.search-button:hover {
  background: #5568d3;
}
```

#### B. Filters and Sorting

**HTML Structure**:
```html
<div class="marketplace-filters">
  <div class="tag-filters">
    <button class="tag-btn active" data-tag="all">All</button>
    <button class="tag-btn" data-tag="api">API Tools</button>
    <button class="tag-btn" data-tag="productivity">Productivity</button>
    <button class="tag-btn" data-tag="development">Development</button>
    <button class="tag-btn" data-tag="testing">Testing</button>
  </div>

  <div class="sort-control">
    <label>Sort by:</label>
    <select class="sort-select" id="marketplace-sort">
      <option value="popular">Most Popular</option>
      <option value="recent">Recently Updated</option>
      <option value="rating">Highest Rated</option>
      <option value="name">Name (A-Z)</option>
    </select>
  </div>
</div>
```

**CSS**:
```css
.marketplace-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.tag-filters {
  display: flex;
  gap: 0.5rem;
}

.tag-btn {
  padding: 0.5rem 1rem;
  border: 1px solid #dee2e6;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.tag-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.tag-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.sort-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-select {
  padding: 0.5rem 1rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  background: white;
  cursor: pointer;
}
```

#### C. Extension Cards Grid

**HTML Structure**:
```html
<div class="marketplace-grid">
  <!-- Extension Card -->
  <div class="marketplace-card" data-extension-id="tools.postman">
    <div class="card-header">
      <img
        src="https://marketplace.agentos.dev/icons/postman.png"
        class="extension-icon"
        alt="Postman Toolkit"
      >
      <div class="card-badges">
        <span class="badge badge-verified" title="Verified by AgentOS">✓</span>
      </div>
    </div>

    <div class="card-body">
      <h3 class="extension-name">Postman Toolkit</h3>
      <p class="extension-author">by AgentOS Team</p>
      <p class="extension-description">
        API testing and response explanation toolkit for developers
      </p>

      <div class="extension-tags">
        <span class="tag">api</span>
        <span class="tag">testing</span>
        <span class="tag">http</span>
      </div>

      <div class="extension-stats">
        <span class="stat">
          <svg><!-- Download icon --></svg>
          1.2K downloads
        </span>
        <span class="stat">
          <svg><!-- Star icon --></svg>
          4.5 rating
        </span>
      </div>
    </div>

    <div class="card-footer">
      <!-- Not installed -->
      <button class="btn btn-install" data-extension-id="tools.postman">
        Install
      </button>

      <!-- Already installed -->
      <button class="btn btn-installed" disabled>
        <svg><!-- Checkmark icon --></svg>
        Installed
      </button>

      <!-- Update available -->
      <button class="btn btn-update" data-extension-id="tools.postman">
        Update to v0.2.0
      </button>

      <button class="btn btn-detail" data-extension-id="tools.postman">
        View Details
      </button>
    </div>
  </div>
</div>
```

**CSS**:
```css
.marketplace-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
  padding: 2rem;
}

.marketplace-card {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.marketplace-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.card-header {
  position: relative;
  padding: 1.5rem;
  text-align: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.extension-icon {
  width: 80px;
  height: 80px;
  border-radius: 12px;
  object-fit: cover;
}

.card-badges {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
}

.badge-verified {
  display: inline-block;
  width: 24px;
  height: 24px;
  background: #28a745;
  color: white;
  border-radius: 50%;
  text-align: center;
  line-height: 24px;
  font-weight: bold;
}

.card-body {
  flex: 1;
  padding: 1.5rem;
}

.extension-name {
  font-size: 1.25rem;
  margin-bottom: 0.25rem;
  color: #212529;
}

.extension-author {
  font-size: 0.875rem;
  color: #6c757d;
  margin-bottom: 1rem;
}

.extension-description {
  font-size: 0.95rem;
  color: #495057;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.extension-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.extension-tags .tag {
  padding: 0.25rem 0.75rem;
  background: #e9ecef;
  border-radius: 12px;
  font-size: 0.75rem;
  color: #495057;
}

.extension-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
  color: #6c757d;
}

.extension-stats .stat {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.card-footer {
  padding: 1rem 1.5rem;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 0.5rem;
}

.btn {
  flex: 1;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.btn-install {
  background: #667eea;
  color: white;
}

.btn-install:hover {
  background: #5568d3;
}

.btn-installed {
  background: #28a745;
  color: white;
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-update {
  background: #ffc107;
  color: #212529;
}

.btn-update:hover {
  background: #e0a800;
}

.btn-detail {
  background: white;
  color: #667eea;
  border: 1px solid #667eea;
}

.btn-detail:hover {
  background: #f8f9fa;
}
```

#### D. Extension Detail Modal

**HTML Structure**:
```html
<div class="modal marketplace-detail-modal" id="extension-detail-modal">
  <div class="modal-overlay" onclick="closeModal()"></div>

  <div class="modal-content">
    <div class="modal-header">
      <img
        src="https://marketplace.agentos.dev/icons/postman.png"
        class="extension-icon-large"
        alt="Postman Toolkit"
      >
      <div class="header-info">
        <h1 class="extension-name">Postman Toolkit</h1>
        <p class="extension-author">by AgentOS Team</p>
        <span class="version-badge">v0.1.0</span>
        <span class="verified-badge">✓ Verified</span>
      </div>
      <button class="modal-close" onclick="closeModal()">
        <svg><!-- Close icon --></svg>
      </button>
    </div>

    <div class="modal-body">
      <!-- Description Section -->
      <section class="detail-section">
        <h2>Description</h2>
        <p>
          Postman Toolkit provides powerful API testing capabilities directly
          in AgentOS. Send HTTP requests, inspect responses, and get AI-powered
          explanations of API behavior.
        </p>
      </section>

      <!-- Features Section -->
      <section class="detail-section">
        <h2>Features</h2>
        <ul>
          <li>Send GET, POST, PUT, DELETE requests</li>
          <li>Automatic response formatting (JSON, XML, HTML)</li>
          <li>AI-powered response explanation</li>
          <li>Request history tracking</li>
        </ul>
      </section>

      <!-- Commands Section -->
      <section class="detail-section">
        <h2>Available Commands</h2>
        <div class="command-list">
          <div class="command-item">
            <code>/postman get &lt;URL&gt;</code>
            <p>Send a GET request to the specified URL</p>
          </div>
          <div class="command-item">
            <code>/postman post &lt;URL&gt; --data &lt;JSON&gt;</code>
            <p>Send a POST request with JSON data</p>
          </div>
        </div>
      </section>

      <!-- Permissions Section -->
      <section class="detail-section">
        <h2>Required Permissions</h2>
        <ul class="permission-list">
          <li>
            <strong>network</strong> - Access external APIs
          </li>
          <li>
            <strong>exec</strong> - Execute CLI tools (curl, wget)
          </li>
        </ul>
      </section>

      <!-- Changelog Section -->
      <section class="detail-section">
        <h2>Changelog</h2>
        <div class="changelog">
          <div class="changelog-version">
            <h3>v0.1.0 <span class="date">(2026-01-15)</span></h3>
            <ul>
              <li>Initial release</li>
              <li>Support for GET, POST, PUT, DELETE methods</li>
              <li>JSON response formatting</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- Stats Section -->
      <section class="detail-section stats-section">
        <div class="stat-card">
          <div class="stat-value">1,234</div>
          <div class="stat-label">Downloads</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">4.5</div>
          <div class="stat-label">Rating</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">v0.1.0</div>
          <div class="stat-label">Version</div>
        </div>
      </section>
    </div>

    <div class="modal-footer">
      <button class="btn btn-install-large" onclick="installExtension('tools.postman')">
        Install Extension
      </button>
      <button class="btn btn-cancel" onclick="closeModal()">
        Cancel
      </button>
    </div>
  </div>
</div>
```

**CSS** (modal styles):
```css
.modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
}

.modal.active {
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal-content {
  position: relative;
  max-width: 800px;
  max-height: 90vh;
  width: 90%;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.extension-icon-large {
  width: 80px;
  height: 80px;
  border-radius: 12px;
  object-fit: cover;
}

.header-info {
  flex: 1;
}

.header-info .extension-name {
  font-size: 1.75rem;
  margin-bottom: 0.25rem;
}

.header-info .extension-author {
  font-size: 1rem;
  opacity: 0.9;
  margin-bottom: 0.5rem;
}

.version-badge,
.verified-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  font-size: 0.875rem;
  margin-right: 0.5rem;
}

.modal-close {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.2s;
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h2 {
  font-size: 1.5rem;
  margin-bottom: 1rem;
  color: #212529;
}

.command-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.command-item {
  padding: 1rem;
  background: #f8f9fa;
  border-left: 4px solid #667eea;
  border-radius: 4px;
}

.command-item code {
  display: block;
  font-size: 1rem;
  color: #667eea;
  margin-bottom: 0.5rem;
}

.permission-list {
  list-style: none;
  padding: 0;
}

.permission-list li {
  padding: 0.75rem;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.stat-card {
  padding: 1.5rem;
  background: #f8f9fa;
  border-radius: 8px;
  text-align: center;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.875rem;
  color: #6c757d;
}

.modal-footer {
  padding: 1.5rem 2rem;
  background: #f8f9fa;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 1rem;
}

.btn-install-large {
  flex: 1;
  padding: 1rem 2rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-install-large:hover {
  background: #5568d3;
}

.btn-cancel {
  padding: 1rem 2rem;
  background: white;
  color: #6c757d;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f8f9fa;
}
```

### 4. Installation Flow (with Gate-M3: Permission Risk Display)

**JavaScript** (`MarketplaceView.js`):

```javascript
async installExtension(extensionId) {
    const ext = this.extensions.find(e => e.id === extensionId);
    if (!ext) return;

    // Gate-M3: Check for dangerous permissions
    const permissions = ext.permissions_required || [];
    const criticalPerms = permissions.filter(p => p === 'exec');
    const highPerms = permissions.filter(p =>
        ['filesystem.write', 'network'].includes(p)
    );

    // Gate-M3: Show security warning for dangerous permissions
    if (criticalPerms.length > 0 || highPerms.length > 0) {
        const confirmed = await this.showSecurityWarning({
            title: '⚠️ Security Warning',
            extensionName: ext.name,
            permissions: permissions,
            message: this.buildPermissionWarningMessage(permissions),
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
            return;  // User cancelled
        }
    }

    // Show progress modal
    this.showProgressModal(ext);

    try {
        // Step 1: Start installation
        const response = await fetch('/api/extensions/install-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: ext.zip_url,
                sha256: ext.sha256  // Gate-M1: SHA256 included
            })
        });

        const result = await response.json();
        const installId = result.install_id;

        // Step 2: Poll for progress
        await this.pollInstallProgress(installId);

        // Step 3: Success
        this.showSuccessMessage(ext);
        this.installedIds.add(extensionId);
        this.render();

    } catch (error) {
        // Step 4: Error
        this.showErrorMessage(ext, error);
    }
}

// Gate-M3: Build permission warning message
buildPermissionWarningMessage(permissions) {
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

// Gate-M3: Render permission badges in extension cards
renderPermissionBadges(permissions) {
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

async pollInstallProgress(installId) {
    return new Promise((resolve, reject) => {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/extensions/install/${installId}`);
                const progress = await response.json();

                // Update progress UI
                this.updateProgressModal(progress);

                if (progress.status === 'COMPLETED') {
                    clearInterval(interval);
                    resolve();
                } else if (progress.status === 'FAILED') {
                    clearInterval(interval);
                    reject(new Error(progress.error));
                }
            } catch (error) {
                clearInterval(interval);
                reject(error);
            }
        }, 1000); // Poll every 1 second
    });
}
```

**Gate-M3 CSS** (add to `marketplace.css`):

```css
/* Permission badges */
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

See `docs/security/MARKETPLACE_SECURITY.md` for full Gate-M3 implementation details.

### 5. Integration Points

**A. Router Integration** (`agentos/webui/app.py`):
```python
# Register marketplace router
from agentos.webui.api.marketplace import router as marketplace_router
app.include_router(marketplace_router)
```

**B. Navigation Menu** (update existing nav):
```html
<nav class="sidebar">
  <a href="/chat" class="nav-item">Chat</a>
  <a href="/projects" class="nav-item">Projects</a>
  <a href="/extensions" class="nav-item">Extensions</a>
  <a href="/extensions/marketplace" class="nav-item">
    Marketplace
    <span class="badge">New</span>
  </a>
  <!-- ... -->
</nav>
```

**C. Extensions Page Link**:
```html
<!-- On /extensions page -->
<div class="extensions-header">
  <h1>Installed Extensions</h1>
  <a href="/extensions/marketplace" class="btn btn-primary">
    Browse Marketplace
  </a>
</div>
```

### 6. State Management

**Check Installed Status**:
```javascript
function isInstalled(extensionId) {
    return this.installedIds.has(extensionId);
}

function hasUpdate(extensionId) {
    const marketExt = this.extensions.find(e => e.id === extensionId);
    const installedExt = this.installed.find(e => e.id === extensionId);

    if (!marketExt || !installedExt) return false;

    return marketExt.version !== installedExt.version;
}
```

**Card Button Logic**:
```javascript
function renderActionButton(ext) {
    if (isInstalled(ext.id)) {
        if (hasUpdate(ext.id)) {
            return `
                <button class="btn btn-update" onclick="updateExtension('${ext.id}')">
                    Update to v${ext.version}
                </button>
            `;
        } else {
            return `
                <button class="btn btn-installed" disabled>
                    <svg><!-- Checkmark --></svg>
                    Installed
                </button>
            `;
        }
    } else {
        return `
            <button class="btn btn-install" onclick="installExtension('${ext.id}')">
                Install
            </button>
        `;
    }
}
```

---

## PR-M3: Publishing Toolchain

**Goal**: Provide tools and workflows for maintaining a Marketplace repository (official or internal).

**Estimated Time**: 2-3 days

### 1. Repository Structure

**Recommended Structure** (example repo: `agentos-marketplace`):
```
agentos-marketplace/
├── extensions/
│   ├── postman/
│   │   ├── postman-v0.1.0.zip
│   │   ├── postman-v0.2.0.zip
│   │   ├── metadata.json
│   │   ├── icon.png
│   │   └── screenshots/
│   │       ├── screenshot1.png
│   │       └── screenshot2.png
│   ├── hello/
│   │   ├── hello-v1.0.0.zip
│   │   ├── metadata.json
│   │   └── icon.png
│   └── curl/
│       └── ...
├── icons/
│   ├── postman.png
│   ├── hello.png
│   └── curl.png
├── index.json                 # Auto-generated, DO NOT EDIT
├── tools/
│   ├── build_index.py         # Generate index.json
│   ├── validate_extension.py  # Validate ZIP packages
│   ├── generate_sha256.sh     # Batch hash calculation
│   └── requirements.txt
├── .github/
│   └── workflows/
│       └── publish.yml        # CI/CD pipeline
├── README.md
└── LICENSE
```

### 2. Extension Metadata Schema

**File**: `extensions/{extension-name}/metadata.json`

```json
{
  "id": "tools.postman",
  "author": "AgentOS Team",
  "tags": ["api", "testing", "http"],
  "downloads": 0,
  "rating": 0.0,
  "verified": true,
  "long_description": "Postman Toolkit provides powerful API testing capabilities...",
  "features": [
    "Send GET, POST, PUT, DELETE requests",
    "Automatic response formatting",
    "AI-powered response explanation"
  ],
  "screenshots": [
    "screenshot1.png",
    "screenshot2.png"
  ],
  "changelog": {
    "0.2.0": {
      "date": "2026-01-20",
      "changes": [
        "Added support for PUT and DELETE methods",
        "Improved error handling"
      ]
    },
    "0.1.0": {
      "date": "2026-01-15",
      "changes": [
        "Initial release",
        "Support for GET and POST methods"
      ]
    }
  },
  "homepage": "https://github.com/agentos/postman-extension",
  "support_url": "https://github.com/agentos/postman-extension/issues",
  "min_agentos_version": "1.0.0"
}
```

### 3. build_index.py Script

**File**: `tools/build_index.py`

```python
#!/usr/bin/env python3
"""
Generate marketplace index.json from extensions/ directory

Scans all extension directories, reads metadata.json and latest ZIP,
generates a compliant index.json file.

Usage:
    python3 tools/build_index.py

Output:
    index.json (at repository root)
"""

import json
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def extract_manifest_from_zip(zip_path: Path) -> Dict[str, Any]:
    """Extract manifest.json from extension ZIP"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find manifest.json (should be in root dir)
        manifest_files = [f for f in zf.namelist() if f.endswith('manifest.json')]
        if not manifest_files:
            raise ValueError(f"No manifest.json found in {zip_path}")

        manifest_path = manifest_files[0]
        manifest_data = zf.read(manifest_path)
        return json.loads(manifest_data)

def get_latest_zip(ext_dir: Path) -> Path:
    """Get the latest version ZIP file from extension directory"""
    zips = sorted(ext_dir.glob("*.zip"), reverse=True)
    if not zips:
        raise ValueError(f"No ZIP files found in {ext_dir}")
    return zips[0]

def build_index(base_url: str = "https://marketplace.agentos.dev") -> Dict[str, Any]:
    """
    Build marketplace index

    Args:
        base_url: Base URL for the marketplace (will be prepended to relative URLs)

    Returns:
        Index dictionary
    """
    extensions_dir = Path("extensions")
    extensions = []

    print(f"Scanning extensions in: {extensions_dir}")

    for ext_dir in sorted(extensions_dir.iterdir()):
        if not ext_dir.is_dir():
            continue

        print(f"\nProcessing: {ext_dir.name}")

        # Read metadata.json
        metadata_path = ext_dir / "metadata.json"
        if not metadata_path.exists():
            print(f"  ⚠️  Skipping (no metadata.json)")
            continue

        metadata = json.loads(metadata_path.read_text())

        # Find latest ZIP
        try:
            latest_zip = get_latest_zip(ext_dir)
        except ValueError as e:
            print(f"  ⚠️  Skipping: {e}")
            continue

        # Extract manifest from ZIP
        try:
            manifest = extract_manifest_from_zip(latest_zip)
        except Exception as e:
            print(f"  ⚠️  Skipping: Failed to extract manifest: {e}")
            continue

        # Calculate SHA256
        sha256 = calculate_sha256(latest_zip)
        print(f"  ✓ SHA256: {sha256[:16]}...")

        # Build extension entry
        entry = {
            "id": metadata["id"],
            "name": manifest["name"],
            "version": manifest["version"],
            "author": metadata["author"],
            "description": manifest["description"],
            "zip_url": f"{base_url}/extensions/{ext_dir.name}/{latest_zip.name}",
            "sha256": sha256,
            "min_agentos_version": metadata.get("min_agentos_version", "1.0.0"),
            "tags": metadata.get("tags", []),
            "icon_url": f"{base_url}/icons/{metadata['id']}.png",
            "downloads": metadata.get("downloads", 0),
            "rating": metadata.get("rating", 0.0),
            "verified": metadata.get("verified", False)
        }

        extensions.append(entry)
        print(f"  ✓ Added: {entry['name']} v{entry['version']}")

    # Build index
    index = {
        "version": "1.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "extensions": extensions
    }

    return index

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Build marketplace index.json")
    parser.add_argument(
        "--base-url",
        default="https://marketplace.agentos.dev",
        help="Base URL for the marketplace"
    )
    parser.add_argument(
        "--output",
        default="index.json",
        help="Output file path"
    )

    args = parser.parse_args()

    # Build index
    index = build_index(base_url=args.base_url)

    # Write to file
    output_path = Path(args.output)
    output_path.write_text(json.dumps(index, indent=2))

    print(f"\n✅ Generated {output_path} with {len(index['extensions'])} extensions")
    print(f"   Last updated: {index['last_updated']}")

if __name__ == "__main__":
    main()
```

### 4. validate_extension.py Script

**File**: `tools/validate_extension.py`

```python
#!/usr/bin/env python3
"""
Validate extension ZIP packages

Uses AgentOS Core's ExtensionValidator to validate extension packages.
This ensures all marketplace extensions are compliant before publishing.

Usage:
    python3 tools/validate_extension.py extensions/postman/*.zip
    python3 tools/validate_extension.py extensions/*/*.zip
"""

import sys
from pathlib import Path

# Import validator from AgentOS Core
# Note: AgentOS must be installed in the environment
try:
    from agentos.core.extensions.validator import ExtensionValidator
except ImportError:
    print("❌ Error: AgentOS not installed or not in PYTHONPATH")
    print("   Install AgentOS: pip install agentos")
    sys.exit(1)

def validate_extension(zip_path: Path) -> bool:
    """
    Validate an extension package

    Args:
        zip_path: Path to ZIP file

    Returns:
        True if valid, False otherwise
    """
    validator = ExtensionValidator()

    print(f"\nValidating: {zip_path.name}")
    print("─" * 60)

    try:
        root_dir, manifest, sha256 = validator.validate_extension_package(zip_path)

        print(f"✅ VALID")
        print(f"   Extension ID: {manifest.id}")
        print(f"   Name: {manifest.name}")
        print(f"   Version: {manifest.version}")
        print(f"   Author: {manifest.author}")
        print(f"   SHA256: {sha256[:16]}...")
        print(f"   Platforms: {', '.join(manifest.platforms)}")
        print(f"   Capabilities: {len(manifest.capabilities)}")

        return True

    except Exception as e:
        print(f"❌ INVALID")
        print(f"   Error: {e}")
        return False

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 validate_extension.py <zip_files...>")
        print("Example: python3 validate_extension.py extensions/*/*.zip")
        sys.exit(1)

    zip_files = [Path(arg) for arg in sys.argv[1:]]

    if not zip_files:
        print("❌ No ZIP files specified")
        sys.exit(1)

    print(f"Validating {len(zip_files)} extension(s)...")

    results = []
    for zip_path in zip_files:
        if not zip_path.exists():
            print(f"\n❌ File not found: {zip_path}")
            results.append(False)
            continue

        results.append(validate_extension(zip_path))

    # Summary
    print("\n" + "=" * 60)
    total = len(results)
    valid = sum(results)
    invalid = total - valid

    print(f"Summary: {valid}/{total} valid, {invalid}/{total} invalid")

    if invalid > 0:
        print("\n❌ Validation failed. Fix errors before publishing.")
        sys.exit(1)
    else:
        print("\n✅ All extensions valid!")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### 5. generate_sha256.sh Script

**File**: `tools/generate_sha256.sh`

```bash
#!/bin/bash
# Generate SHA256 hashes for all extension ZIPs
# Usage: bash tools/generate_sha256.sh

echo "Generating SHA256 hashes for all extensions..."
echo ""

for zip_file in extensions/*/*.zip; do
    if [ -f "$zip_file" ]; then
        echo "File: $zip_file"
        sha256sum "$zip_file" | awk '{print "SHA256:", $1}'
        echo ""
    fi
done

echo "✅ Done!"
```

### 6. CI/CD Pipeline

**File**: `.github/workflows/publish.yml`

```yaml
name: Publish Marketplace

on:
  push:
    branches: [main]
    paths:
      - 'extensions/**'
  workflow_dispatch:

jobs:
  validate-and-publish:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r tools/requirements.txt
          pip install agentos

      - name: Validate all extensions
        run: |
          python3 tools/validate_extension.py extensions/*/*.zip

      - name: Build index.json
        run: |
          python3 tools/build_index.py \
            --base-url "https://marketplace.agentos.dev" \
            --output index.json

      - name: Verify index.json
        run: |
          # Check JSON is valid
          python3 -m json.tool index.json > /dev/null

          # Check contains extensions
          count=$(jq '.extensions | length' index.json)
          echo "Index contains $count extensions"

          if [ "$count" -lt 1 ]; then
            echo "❌ Error: Index has no extensions"
            exit 1
          fi

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: .
          publish_branch: gh-pages
          force_orphan: true

      - name: Summary
        run: |
          echo "✅ Marketplace published successfully!"
          echo "   URL: https://marketplace.agentos.dev/index.json"
          echo "   Extensions: $(jq '.extensions | length' index.json)"
```

**File**: `tools/requirements.txt`
```
agentos>=1.0.0
pyyaml>=6.0
requests>=2.31.0
```

### 7. README Template

**File**: `README.md` (for marketplace repository)

```markdown
# AgentOS Marketplace

Official extension marketplace for AgentOS.

## Structure

- `extensions/` - Extension packages and metadata
- `icons/` - Extension icons
- `tools/` - Publishing tools
- `index.json` - Auto-generated marketplace index (DO NOT EDIT)

## Adding an Extension

1. Create a directory under `extensions/{extension-name}/`
2. Add the extension ZIP file(s): `{extension-name}-v{version}.zip`
3. Create `metadata.json` (see template below)
4. Add icon: `icon.png` (recommended: 256x256 PNG)
5. Commit and push to `main` branch
6. CI/CD will validate and publish automatically

### metadata.json Template

```json
{
  "id": "tools.example",
  "author": "Your Name",
  "tags": ["category1", "category2"],
  "downloads": 0,
  "rating": 0.0,
  "verified": false,
  "long_description": "Detailed description...",
  "features": [
    "Feature 1",
    "Feature 2"
  ],
  "screenshots": [],
  "changelog": {
    "1.0.0": {
      "date": "2026-01-30",
      "changes": ["Initial release"]
    }
  },
  "homepage": "https://github.com/...",
  "support_url": "https://github.com/.../issues",
  "min_agentos_version": "1.0.0"
}
```

## Local Testing

### Validate extension
```bash
python3 tools/validate_extension.py extensions/example/*.zip
```

### Build index
```bash
python3 tools/build_index.py --base-url "http://localhost:8000"
```

### Test locally
```bash
# Serve files locally
python3 -m http.server 8000

# Configure AgentOS to use local marketplace
export MARKETPLACE_INDEX_URL="http://localhost:8000/index.json"
agentos webui
```

## License

MIT
```

### 8. Workflow Summary

**Publishing Flow**:
1. Developer creates extension ZIP following AgentOS standards
2. Developer adds ZIP and metadata to `extensions/{name}/` directory
3. Developer commits and pushes to `main` branch
4. GitHub Actions CI/CD:
   - Validates all ZIPs using AgentOS validator
   - Generates `index.json` from metadata
   - Deploys to GitHub Pages (or other hosting)
5. Marketplace is now accessible at configured URL
6. Users can browse and install from AgentOS WebUI

**Update Flow**:
1. Developer adds new version ZIP: `{name}-v{new-version}.zip`
2. Updates `metadata.json` with changelog
3. Commits and pushes
4. CI/CD regenerates index (latest version is picked automatically)
5. Users see "Update Available" in marketplace

---

## Technical Choices

### Backend Technology

**FastAPI** (existing)
- Already used in AgentOS WebUI
- Async support for concurrent requests
- Pydantic for schema validation
- OpenAPI documentation

### Frontend Technology

**Vanilla JavaScript + CSS** (no framework)
- Consistent with existing WebUI
- No build step required
- Lightweight and fast
- Easy to maintain

### Cache Strategy

**JSON File Cache** (simple and reliable)
- Store cache in `.agentos/marketplace/index_cache.json`
- Store metadata (ETag, timestamp) in `index_meta.json`
- TTL-based expiration (default: 1 hour)
- ETag support for conditional requests (304 Not Modified)
- Fallback to expired cache on network error

**Why not Redis/Database?**
- Adds deployment complexity
- Marketplace index is read-heavy, write-rare
- File cache is sufficient for this use case

### CDN/Hosting

**Recommended Options**:

1. **GitHub Pages** (Free, easy)
   - Push to `gh-pages` branch
   - Automatic HTTPS
   - CDN-backed
   - URL: `https://{org}.github.io/{repo}/index.json`

2. **Cloudflare Pages** (Free, fast)
   - Connect to Git repository
   - Global CDN
   - Custom domain support
   - URL: `https://marketplace.agentos.dev/index.json`

3. **AWS S3 + CloudFront** (Enterprise)
   - Full control
   - Analytics
   - Custom domains
   - Higher cost

## Security Considerations

**IMPORTANT**: This section describes the three-gate defense system for Marketplace security. For complete implementation details, see `docs/security/MARKETPLACE_SECURITY.md`.

### Three-Gate Defense Overview

1. **Gate-M1: Trust Chain** - Ensure downloads are untampered (SHA256 + HTTPS + whitelist)
2. **Gate-M2: Rollback & Idempotency** - Ensure updates don't break the system
3. **Gate-M3: Permission Risk Display** - Ensure users understand what they're installing

---

### Gate-M1: Trust Chain (PR-M1)

**Rationale**: Prevent supply chain attacks through tampered extensions.

**Core Mechanisms**:
1. **HTTPS Enforcement**: Marketplace index URL **MUST** use HTTPS
2. **SHA256 Mandatory Validation**: Index must include SHA256 for each extension
3. **Domain Whitelist**: Optional whitelist of trusted domains
4. **Source Recording**: Track where each extension came from

**Implementation**:
- Schema enforces HTTPS via `@validator('zip_url')`
- Schema enforces 64-character hex SHA256 field
- Double SHA256 check: downloader + installer
- Database tracks: `source_type`, `source_url`, `marketplace_index_url`, `installed_at`
- SecurityError raised on SHA256 mismatch

**Code** (`schemas.py`):
```python
class MarketplaceExtension(BaseModel):
    sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$"
    )

    @validator('zip_url')
    def validate_https(cls, v):
        if v.scheme != 'https':
            raise ValueError('zip_url must use HTTPS')
        return v
```

**Attack Mitigations**:
- Man-in-the-middle → HTTPS + SHA256
- Malicious marketplace → Domain whitelist
- Tampered extension → SHA256 mismatch rejection
- Supply chain poisoning → Audit logs + source tracking

---

### Gate-M2: Rollback & Idempotency (PR-M1)

**Rationale**: Ensure updates don't leave the system in a broken state.

**Core Mechanisms**:
1. **Idempotency**: Same version install is a no-op (returns success)
2. **Update with Rollback**: Backup before update, restore on failure
3. **State Protection**: Preserve enabled state through update/rollback

**Implementation**:
- Check existing version before install
- Same version → return `InstallResult(skipped=True)`
- Different version → trigger `update_extension()`
- Backup to `.agentos/extensions/.backup/{id}-{version}/`
- Use database transaction for atomic operations
- On failure: restore filesystem + database state

**Code** (`registry.py`):
```python
def install_extension(self, zip_path: Path, source: str = "upload"):
    manifest = self.validator.extract_manifest(zip_path)
    existing = self.get_extension(manifest.id)

    if existing and existing.version == manifest.version:
        # Idempotent
        return InstallResult(success=True, skipped=True)

    if existing:
        # Update with rollback
        return self.update_extension(manifest.id, zip_path)

    # New install
    return self._install_new_extension(zip_path, source)
```

**Attack Mitigations**:
- Failed update breaks system → Automatic rollback
- Inconsistent state → Database transactions
- Lost enabled state → State preservation logic

---

### Gate-M3: Permission Risk Display (PR-M2)

**Rationale**: Inform users about security risks before installation.

**Core Mechanisms**:
1. **Permission Badges**: Visual indicators on extension cards
2. **Pre-install Confirmation**: Dialog for dangerous permissions
3. **Remote Mode Warning**: Stronger warnings for network-exposed deployments (v1.1+)

**Implementation**:
- CSS classes: `permission-critical`, `permission-high`, `permission-medium`, `permission-low`
- Color coding: Red (exec), Orange (filesystem.write), Yellow (network), Green (filesystem.read)
- Pre-install dialog for `exec` or `filesystem.write`
- User must explicitly confirm: "I Understand, Install Anyway"

**Code** (`MarketplaceView.js`):
```javascript
async installExtension(extensionId) {
    const ext = this.extensions.find(e => e.id === extensionId);
    const permissions = ext.permissions_required || [];

    // Check dangerous permissions
    const hasDangerous = permissions.some(p =>
        ['exec', 'filesystem.write'].includes(p)
    );

    if (hasDangerous) {
        const confirmed = await this.showSecurityWarning({
            title: '⚠️ Security Warning',
            permissions: permissions,
            message: this.buildPermissionWarningMessage(permissions)
        });

        if (!confirmed) return;
    }

    // Continue installation...
}
```

**Attack Mitigations**:
- User installs malicious extension → Permission badge warning
- Silent permission escalation → Explicit display of all permissions
- Uninformed installation → Mandatory confirmation dialog

---

### Additional Security Measures

**4. Schema Validation**

**Rationale**: Prevent malformed index data from causing errors.

**Implementation**:
- All index data validated via Pydantic schemas
- Invalid schema = reject entire index
- Fallback to cached version if available

**5. No Code Execution**

**Rationale**: Marketplace is index-only, never executes code.

**Implementation**:
- Marketplace only provides metadata (JSON)
- Installation goes through Core's controlled executor
- Extension validation enforces ADR-EXT-001 (no entrypoints)
- No direct code execution from marketplace

**6. Rate Limiting (Future v1.1+)**

**Recommendation**: Add rate limiting to marketplace API in production.

**Implementation** (future):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/api/marketplace/index")
@limiter.limit("10/minute")
async def get_marketplace_index(...):
    ...
```

---

### Security Compliance

The three-gate defense system ensures Marketplace complies with:
- ✅ OWASP Top 10 (Supply Chain Attacks)
- ✅ CIS Controls (Software Asset Management)
- ✅ NIST Cybersecurity Framework (Integrity Checking)

**For complete implementation details, code examples, and test requirements, see**:
`docs/security/MARKETPLACE_SECURITY.md`

## Dependency Relationships

```
PR-M1 (Index Service)
  ↓
PR-M2 (WebUI)

PR-M3 (Toolchain) - Independent
```

- **PR-M2 depends on PR-M1**: WebUI needs API to fetch index
- **PR-M3 is independent**: Can be developed in parallel
- **PR-M1 and PR-M3 can be combined**: Both are infrastructure work

**Recommended Order**:
1. Week 1: PR-M1 + PR-M3 (backend + toolchain)
2. Week 2: PR-M2 (frontend)
3. Week 3: Testing and polish

## Milestones

### Week 1: Infrastructure (PR-M1 + PR-M3)

**Days 1-3: PR-M1 (Index Service)**
- Day 1: Config, schemas, cache manager
- Day 2: HTTP client, service layer
- Day 3: API endpoint, unit tests

**Days 4-5: PR-M3 (Toolchain)**
- Day 4: Build scripts (build_index.py, validate_extension.py)
- Day 5: CI/CD pipeline, documentation

### Week 2: Frontend (PR-M2)

**Days 6-8: Core UI**
- Day 6: Marketplace grid view, search, filters
- Day 7: Extension cards, status indicators
- Day 8: Detail modal, installation flow

**Days 9-10: Integration**
- Day 9: Router integration, navigation, state management
- Day 10: Polish, responsive design, error handling

### Week 3: Testing and Launch

**Days 11-12: Testing**
- Day 11: Integration tests, E2E testing
- Day 12: Performance testing, security review

**Days 13-15: Launch Preparation**
- Day 13: Documentation (user guide, admin guide)
- Day 14: Sample extensions, demo marketplace
- Day 15: Launch, monitoring, bug fixes

## Time Estimates Summary

| PR | Component | Estimated Time |
|----|-----------|----------------|
| PR-M1 | Marketplace Index Service (Core) | 3-5 days |
| PR-M2 | WebUI Marketplace Page | 5-7 days |
| PR-M3 | Publishing Toolchain | 2-3 days |
| **Total** | **All PRs** | **10-15 days (2-3 weeks)** |

**Assumptions**:
- 1 full-time developer
- Includes implementation, testing, and documentation
- Excludes design review and approval time

## Future Enhancements (v2)

### 1. User Ratings and Reviews

**Features**:
- Star ratings (1-5 stars)
- Text reviews
- Helpful votes
- Moderation system

**Implementation**:
- Add `ratings` table in database
- API: `POST /api/marketplace/{id}/rate`
- API: `GET /api/marketplace/{id}/reviews`
- Update index generation to include average rating

### 2. Extension Analytics

**Features**:
- Download counts
- Installation success rate
- Usage statistics
- Trending extensions

**Implementation**:
- Track installation events in database
- API: `POST /api/marketplace/{id}/track-download`
- Dashboard for extension authors
- Weekly/monthly reports

### 3. Extension Certification

**Features**:
- Official verification badge
- Security audit status
- Code review process
- Trusted publishers

**Implementation**:
- Manual review workflow
- Verification API: `POST /api/admin/extensions/{id}/verify`
- Badge displayed in UI
- Certification criteria documented

### 4. Paid Extensions

**Features**:
- One-time purchase
- Subscription model
- Free trial period
- License key validation

**Implementation**:
- Payment gateway integration (Stripe)
- License server
- API: `POST /api/marketplace/{id}/purchase`
- License validation in installer

### 5. Multi-language Support

**Features**:
- Translated descriptions
- Localized screenshots
- Language-specific search
- Auto-detection from browser

**Implementation**:
- Add `i18n/` directory in extension packages
- Accept-Language header support
- API: `GET /api/marketplace/index?lang=zh-CN`
- UI language switcher

### 6. Categories and Collections

**Features**:
- Curated collections (e.g., "Top 10 for Developers")
- Featured extensions
- "New This Week"
- "Most Popular"

**Implementation**:
- Add `collections.json` in marketplace repo
- API: `GET /api/marketplace/collections`
- UI: Collections page

### 7. Extension Dependencies

**Features**:
- Declare dependencies in manifest
- Auto-install dependencies
- Version compatibility checks
- Dependency graph visualization

**Implementation**:
- Add `dependencies` field to manifest
- Recursive installation logic
- Conflict detection
- Dependency resolver

## Acceptance Criteria

### PR-M1: Marketplace Index Service

**Core Functionality**:
- [ ] Configuration options documented and working
- [ ] API endpoint returns valid index
- [ ] Cache implemented with TTL and ETag support
- [ ] HTTPS enforcement working
- [ ] Domain whitelist (optional) working
- [ ] Schema validation rejects invalid data
- [ ] Error handling with cache fallback
- [ ] Unit tests: 6+ tests passing
- [ ] Integration test: Fetch real index

**Gate-M1: Trust Chain**:
- [ ] Index schema enforces SHA256 (64-char hex, mandatory)
- [ ] Schema validation enforces HTTPS for zip_url
- [ ] Double SHA256 validation during installation
- [ ] SHA256 mismatch raises SecurityError
- [ ] Source tracking fields added to database schema
- [ ] `record_install_source()` method implemented
- [ ] Domain whitelist validation in `validate_extension_url()`
- [ ] Trust chain tests pass: `test_marketplace_sha256_mismatch_rejected`, `test_marketplace_non_https_rejected`, `test_marketplace_domain_whitelist_enforced`

**Gate-M2: Rollback & Idempotency**:
- [ ] `install_extension()` checks for existing version (idempotent)
- [ ] Same version install returns success with `skipped=True`
- [ ] Different version triggers `update_extension()`
- [ ] `update_extension()` creates filesystem backup
- [ ] `update_extension()` uses database transaction
- [ ] Update failure triggers rollback (filesystem + database)
- [ ] Enabled state preserved through update/rollback
- [ ] Rollback tests pass: `test_extension_install_idempotent`, `test_extension_update_rollback_on_failure`, `test_extension_update_preserves_enabled_state`

### PR-M2: WebUI Marketplace Page

**Core Functionality**:
- [ ] Marketplace page accessible at `/extensions/marketplace`
- [ ] Search, filters, and sorting working
- [ ] Extension cards display correctly
- [ ] Install/Installed/Update buttons show correct state
- [ ] Installation flow works end-to-end
- [ ] Progress modal shows installation status
- [ ] Detail modal displays all information
- [ ] Responsive design works on mobile
- [ ] Error handling shows user-friendly messages

**Gate-M3: Permission Risk Display**:
- [ ] Permission badges CSS implemented (critical/high/medium/low)
- [ ] `renderPermissionBadges()` displays badges on extension cards
- [ ] Permission badges use color coding (red/orange/yellow/green)
- [ ] `buildPermissionWarningMessage()` generates security warnings
- [ ] Pre-install confirmation dialog for dangerous permissions
- [ ] Confirmation dialog lists all permissions with risk levels
- [ ] User must explicitly confirm to proceed
- [ ] Installation cancelled if user declines confirmation
- [ ] Permission display tests pass: `test_permission_badges_displayed_correctly`, `test_dangerous_permission_shows_confirmation`
- [ ] (v1.1+) Remote mode warning placeholder added

### PR-M3: Publishing Toolchain

- [ ] `build_index.py` generates valid index.json
- [ ] `validate_extension.py` validates ZIP packages
- [ ] `generate_sha256.sh` calculates hashes
- [ ] CI/CD pipeline validates and publishes
- [ ] README documentation complete
- [ ] Sample metadata.json provided
- [ ] Local testing instructions work
- [ ] GitHub Pages deployment successful

### Documentation

- [ ] `docs/security/MARKETPLACE_SECURITY.md` created
- [ ] Three-gate defense documented
- [ ] Attack scenarios and mitigations documented
- [ ] Implementation details for each gate provided
- [ ] Testing requirements documented
- [ ] Code examples included for all gates

## References

- **ADR-EXT-001**: `/docs/adr/ADR-EXT-001-declarative-extensions-only.md`
- **Extension System**: `/docs/extensions/`
- **Existing API**: `/agentos/webui/api/extensions.py`
- **Validator**: `/agentos/core/extensions/validator.py`
- **Installer**: `/agentos/core/extensions/installer.py`
- **Security Model**: `/docs/security/MARKETPLACE_SECURITY.md` (NEW)

## Conclusion

This implementation plan provides a comprehensive blueprint for building the AgentOS Marketplace in three progressive PRs:

1. **PR-M1**: Backend infrastructure for fetching and caching marketplace index + Gate-M1 (Trust Chain) + Gate-M2 (Rollback)
2. **PR-M2**: User-facing marketplace browsing and installation interface + Gate-M3 (Permission Risk Display)
3. **PR-M3**: Tools and workflows for maintaining marketplace repositories

**Key Strengths**:
- **Security-first**: Three-gate defense system (Trust Chain, Rollback, Permission Display)
- **Supply Chain Security**: HTTPS enforcement, SHA256 verification, domain whitelist, source tracking
- **Resilient**: Rollback mechanism, idempotency, cache fallback, ETag support
- **User-informed**: Permission badges, pre-install warnings, risk communication
- **Simple**: Leverages existing installation mechanism, no new execution paths
- **Scalable**: Index-only architecture, CDN-friendly, supports large catalogs
- **Developer-friendly**: Clear toolchain, CI/CD automation, validation scripts

**Security Gates Summary**:
- **Gate-M1 (Trust Chain)**: SHA256 mandatory validation, HTTPS enforcement, source recording, domain whitelist
- **Gate-M2 (Rollback)**: Idempotent installs, atomic updates with rollback, state preservation
- **Gate-M3 (Permission Display)**: Visual badges, pre-install confirmation, risk communication

**Total Effort**: 2-3 weeks for complete implementation including testing and documentation.

**Security Compliance**: OWASP Top 10, CIS Controls, NIST Cybersecurity Framework

---

**Status**: Ready for implementation (with security gates)
**Next Step**: Review security model (`docs/security/MARKETPLACE_SECURITY.md`), then begin PR-M1
**Estimated Start**: 2026-02-01
**Estimated Completion**: 2026-02-21

---

**Prepared by**: System Planning Agent
**Date**: 2026-01-30
**Version**: 1.1 (with security gates)
