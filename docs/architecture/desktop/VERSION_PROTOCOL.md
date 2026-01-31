# AgentOS Desktop 版本管理协议

> **版本**: 1.0
> **日期**: 2026-01-30
> **状态**: 冻结（Frozen）
> **目的**: 定义 AgentOS Desktop 组件版本管理的标准格式和规则

---

## 📑 目录

- [概述](#概述)
- [version.json Schema](#versionjson-schema)
- [Semantic Versioning 规则](#semantic-versioning-规则)
- [版本比较算法](#版本比较算法)
- [组件版本管理](#组件版本管理)
- [依赖关系声明](#依赖关系声明)
- [降级策略](#降级策略)
- [版本文件位置](#版本文件位置)
- [变更记录](#变更记录)

---

## 概述

AgentOS Desktop 采用**组件级版本管理**，每个可更新组件都有独立的版本号和版本文件。

### 核心组件

| 组件名称 | 描述 | 可独立更新 |
|---------|------|----------|
| `app` | Tauri Desktop Shell | ✅ (通过 Tauri Updater) |
| `agentos-runtime` | Python 打包的服务端 | ✅ (通过自定义更新) |
| `ollama` | Ollama Server | ✅ (通过自定义更新) |
| `updater-helper` | 更新辅助程序 | ⚠️ (随 app 更新) |

### 版本管理原则

| 原则 | 说明 |
|------|------|
| **Semantic Versioning** | 严格遵循 SemVer 2.0 |
| **平台隔离** | 不同平台独立版本号 |
| **兼容性优先** | 向后兼容性检查 |
| **可追溯性** | 包含构建时间和 Git commit |

---

## version.json Schema

### 标准格式

```json
{
  "name": "agentos-runtime",
  "version": "0.4.2",
  "build": "20260130120000",
  "commit": "6aa4aaa",
  "platform": "macos-arm64",
  "build_date": "2026-01-30T12:00:00Z",
  "dependencies": {
    "ollama": ">=0.5.0"
  }
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 | 示例 |
|------|------|------|------|------|
| `name` | string | ✅ | 组件名称 | `"agentos-runtime"` |
| `version` | string | ✅ | 语义化版本号 | `"0.4.2"` |
| `build` | string | ✅ | 构建时间戳 | `"20260130120000"` |
| `commit` | string | ✅ | Git commit hash (短) | `"6aa4aaa"` |
| `platform` | string | ✅ | 目标平台 | `"macos-arm64"` |
| `build_date` | string | ❌ | ISO 8601 构建日期 | `"2026-01-30T12:00:00Z"` |
| `dependencies` | object | ❌ | 依赖组件版本要求 | `{"ollama": ">=0.5.0"}` |

### 平台标识符（platform）

| 平台 | 标识符 |
|------|--------|
| macOS (Apple Silicon) | `macos-arm64` |
| macOS (Intel) | `macos-x64` |
| Windows (64-bit) | `windows-x64` |
| Linux (64-bit) | `linux-x64` |

---

## Semantic Versioning 规则

遵循 [Semantic Versioning 2.0.0](https://semver.org/)。

### 版本格式

```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
```

**示例**:
- `0.4.2` - 稳定版本
- `0.5.0-beta.1` - Beta 版本
- `1.0.0-rc.2+20260130` - Release Candidate

### 版本递增规则

| 场景 | MAJOR | MINOR | PATCH | 示例 |
|------|-------|-------|-------|------|
| **Breaking Change** | +1 | 0 | 0 | `0.4.2 → 1.0.0` |
| **新功能（向后兼容）** | - | +1 | 0 | `0.4.2 → 0.5.0` |
| **Bug 修复** | - | - | +1 | `0.4.2 → 0.4.3` |

### 预发布版本

```
0.5.0-alpha.1   →  内部测试
0.5.0-beta.1    →  外部测试
0.5.0-rc.1      →  候选版本
0.5.0           →  正式版本
```

**排序规则**:
```
0.4.9 < 0.5.0-alpha.1 < 0.5.0-beta.1 < 0.5.0-rc.1 < 0.5.0
```

---

## 版本比较算法

### 基本比较

```rust
use semver::Version;

fn compare_versions(v1: &str, v2: &str) -> std::cmp::Ordering {
    let version1 = Version::parse(v1).unwrap();
    let version2 = Version::parse(v2).unwrap();
    version1.cmp(&version2)
}

// 示例
assert!(compare_versions("0.4.2", "0.5.0") == std::cmp::Ordering::Less);
assert!(compare_versions("1.0.0", "0.9.9") == std::cmp::Ordering::Greater);
```

### 兼容性判断

```rust
fn is_compatible(required: &str, actual: &str) -> bool {
    let req = semver::VersionReq::parse(required).unwrap();
    let ver = Version::parse(actual).unwrap();
    req.matches(&ver)
}

// 示例
assert!(is_compatible(">=0.5.0", "0.5.4"));
assert!(!is_compatible(">=0.6.0", "0.5.4"));
```

### 版本需求语法

| 语法 | 含义 | 示例 | 匹配版本 |
|------|------|------|---------|
| `1.2.3` | 精确匹配 | `"1.2.3"` | 仅 1.2.3 |
| `>=1.2.0` | 大于等于 | `">=1.2.0"` | 1.2.0, 1.3.0, 2.0.0 |
| `^1.2.3` | 兼容版本 | `"^1.2.3"` | 1.2.3 - 1.x.x (< 2.0.0) |
| `~1.2.3` | 近似版本 | `"~1.2.3"` | 1.2.3 - 1.2.x |
| `>=1.0.0,<2.0.0` | 范围 | `">=1.0.0,<2.0.0"` | 1.0.0 - 1.9.9 |

---

## 组件版本管理

### App 版本

**更新机制**: Tauri Updater（通过 `.dmg`/`.exe` 替换整个 App）

**版本声明位置**: 内嵌在 `tauri.conf.json`

```json
{
  "package": {
    "productName": "AgentOS",
    "version": "0.4.2"
  }
}
```

**运行时获取**:
```rust
let app_version = app.package_info().version.to_string();
```

---

### AgentOS Runtime 版本

**更新机制**: 自定义更新（替换 `resources/runtime/agentos-runtime`）

**版本文件**: `resources/runtime/version.json`

```json
{
  "name": "agentos-runtime",
  "version": "0.4.2",
  "build": "20260130120000",
  "commit": "6aa4aaa",
  "platform": "macos-arm64",
  "dependencies": {
    "ollama": ">=0.5.0"
  }
}
```

**生成方式**（构建时）:
```bash
#!/bin/bash
# scripts/generate-version.sh

VERSION=$(git describe --tags --abbrev=0)
COMMIT=$(git rev-parse --short HEAD)
BUILD=$(date +%Y%m%d%H%M%S)
PLATFORM=$(uname -m)

cat > version.json <<EOF
{
  "name": "agentos-runtime",
  "version": "$VERSION",
  "build": "$BUILD",
  "commit": "$COMMIT",
  "platform": "$PLATFORM"
}
EOF
```

---

### Ollama 版本

**更新机制**: 自定义更新（替换 `resources/ollama/ollama`）

**版本文件**: `resources/ollama/version.json`

```json
{
  "name": "ollama",
  "version": "0.5.4",
  "build": "20260128000000",
  "commit": "abc1234",
  "platform": "macos-arm64"
}
```

**获取方式**（运行时）:
```bash
# Ollama 自带版本查询
ollama --version
# 输出: ollama version is 0.5.4
```

---

## 依赖关系声明

### 依赖类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **强依赖** | 必须满足版本要求 | Runtime 依赖 Ollama |
| **弱依赖** | 可选依赖 | Git（用于代码操作） |
| **平台依赖** | 特定平台要求 | macOS 13.0+ |

### 依赖声明格式

```json
{
  "name": "agentos-runtime",
  "version": "0.4.2",
  "dependencies": {
    "ollama": ">=0.5.0,<0.6.0",
    "python": "3.13.*"
  },
  "optional_dependencies": {
    "git": ">=2.30.0"
  },
  "platform_requirements": {
    "macos": "13.0",
    "windows": "10.0.17763"
  }
}
```

### 依赖兼容性检查

```rust
struct ComponentVersion {
    name: String,
    version: Version,
    dependencies: HashMap<String, VersionReq>,
}

fn check_dependencies(components: Vec<ComponentVersion>) -> Result<(), Error> {
    for component in &components {
        for (dep_name, req) in &component.dependencies {
            let dep = components
                .iter()
                .find(|c| c.name == *dep_name)
                .ok_or(Error::MissingDependency(dep_name.clone()))?;

            if !req.matches(&dep.version) {
                return Err(Error::IncompatibleVersion {
                    component: component.name.clone(),
                    required: req.to_string(),
                    actual: dep.version.to_string(),
                });
            }
        }
    }
    Ok(())
}
```

---

## 降级策略

### 默认策略：禁止降级

```rust
fn can_update(current: &Version, new: &Version) -> Result<(), Error> {
    if new < current {
        return Err(Error::DowngradeNotAllowed {
            current: current.to_string(),
            new: new.to_string(),
        });
    }
    Ok(())
}
```

### 用户明确允许降级

```
┌─────────────────────────────────────────┐
│  Downgrade Warning                      │
├─────────────────────────────────────────┤
│  You are about to downgrade from        │
│  v0.5.0 to v0.4.2.                      │
│                                          │
│  This may cause data loss or            │
│  compatibility issues.                  │
│                                          │
│  ⚠️ Only proceed if you know what       │
│     you're doing.                       │
│                                          │
│  [Cancel] [I Understand, Proceed]       │
└─────────────────────────────────────────┘
```

### 强制降级标记

```json
{
  "allow_downgrade": true,
  "downgrade_reason": "Critical bug in v0.5.0",
  "timestamp": "2026-01-30T12:00:00Z"
}
```

---

## 版本文件位置

### 本地版本文件

| 组件 | 路径 |
|------|------|
| App | 内嵌在可执行文件 |
| Runtime | `resources/runtime/version.json` |
| Ollama | `resources/ollama/version.json` |
| Updater Helper | `resources/updater/version.json` |

### 远端版本清单

**URL**: `https://releases.agentos.com/manifest.json`

**格式**:
```json
{
  "version": "1.0",
  "generated_at": "2026-01-30T12:00:00Z",
  "components": {
    "app": {
      "version": "0.4.2",
      "platforms": {
        "macos-arm64": {
          "url": "https://releases.agentos.com/app/v0.4.2/AgentOS-macos-arm64.tar.gz",
          "sha256": "abc123...",
          "size": 52428800
        }
      },
      "release_notes_url": "https://releases.agentos.com/app/v0.4.2/RELEASE_NOTES.md",
      "minimum_os_version": {
        "macos": "13.0",
        "windows": "10.0.17763"
      }
    },
    "agentos-runtime": {
      "version": "0.4.2",
      "platforms": {
        "macos-arm64": {
          "url": "https://releases.agentos.com/runtime/v0.4.2/agentos-runtime-macos-arm64",
          "sha256": "def456...",
          "size": 35651584
        }
      },
      "dependencies": {
        "ollama": ">=0.5.0"
      }
    }
  }
}
```

---

## 版本锁定文件

### 本地锁定（防止回滚失败）

**位置**: `~/.agentos/config/version-lock.json`

```json
{
  "app": {
    "version": "0.4.2",
    "locked_at": "2026-01-30T12:00:00Z",
    "can_downgrade": false
  },
  "agentos-runtime": {
    "version": "0.4.2",
    "locked_at": "2026-01-30T12:00:00Z",
    "can_downgrade": false
  },
  "ollama": {
    "version": "0.5.4",
    "locked_at": "2026-01-28T10:00:00Z",
    "can_downgrade": true
  }
}
```

---

## 版本迁移路径

### 跨大版本升级

```
0.4.x → 0.5.x → 1.0.x
```

**迁移检查**:
```rust
fn migration_required(from: &Version, to: &Version) -> bool {
    from.major != to.major
}

fn get_migration_path(from: &Version, to: &Version) -> Vec<Version> {
    // 示例: 0.4.2 → 1.0.0 需要先升级到 0.5.x
    if from.major == 0 && to.major == 1 {
        vec![
            Version::parse("0.5.0").unwrap(),
            Version::parse("1.0.0").unwrap(),
        ]
    } else {
        vec![to.clone()]
    }
}
```

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-30 | 初始版本，定义版本协议 | Claude |

---

## 附录：完整示例

### 构建时生成 version.json

```rust
// build.rs
use std::process::Command;
use std::fs;

fn main() {
    let version = env!("CARGO_PKG_VERSION");
    let commit = Command::new("git")
        .args(&["rev-parse", "--short", "HEAD"])
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|_| "unknown".to_string());

    let build = chrono::Utc::now().format("%Y%m%d%H%M%S").to_string();
    let platform = std::env::consts::ARCH;

    let version_json = serde_json::json!({
        "name": "agentos-runtime",
        "version": version,
        "build": build,
        "commit": commit,
        "platform": format!("{}-{}", std::env::consts::OS, platform),
    });

    fs::write("version.json", version_json.to_string()).unwrap();
}
```

### 运行时读取版本

```rust
use serde::{Deserialize, Serialize};
use std::fs;

#[derive(Serialize, Deserialize)]
struct VersionInfo {
    name: String,
    version: String,
    build: String,
    commit: String,
    platform: String,
}

fn read_version(path: &str) -> Result<VersionInfo, Box<dyn std::error::Error>> {
    let content = fs::read_to_string(path)?;
    let version: VersionInfo = serde_json::from_str(&content)?;
    Ok(version)
}
```

---

**审阅状态**: 待审阅
**下一步**: 团队确认版本管理规则后冻结此文档
