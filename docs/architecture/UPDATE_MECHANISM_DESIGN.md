# AgentOS Desktop 更新机制详细设计

> **版本**: 1.0
> **日期**: 2026-01-30
> **状态**: 设计阶段

---

## 目标

实现一个**安全、可靠、用户友好**的组件级热更新系统，满足：

1. **安全性**: SHA-256 校验，签名验证
2. **可靠性**: 失败自动回滚，保留用户数据
3. **用户友好**: 进度透明，重启提示清晰
4. **组件解耦**: App/Runtime/Ollama 独立更新

---

## 架构概览

```
┌────────────────────────────────────────────────────────┐
│                    AgentOS Desktop                     │
│                                                        │
│  ┌──────────────────────────────────────────────┐    │
│  │         Update Manager (Rust)                │    │
│  │  - 检查更新                                   │    │
│  │  - 下载 & 校验                                │    │
│  │  - 应用更新（通过 Helper）                    │    │
│  └──────────────────────────────────────────────┘    │
│                         ↓                             │
│  ┌──────────────────────────────────────────────┐    │
│  │     Update Manifest (Remote)                 │    │
│  │     https://releases.agentos.com/            │    │
│  │     manifest.json                            │    │
│  └──────────────────────────────────────────────┘    │
│                         ↓                             │
│  ┌──────────────────────────────────────────────┐    │
│  │        Updater Helper (独立进程)              │    │
│  │  - App 退出后启动                             │    │
│  │  - 替换 resources/ 下的文件                   │    │
│  │  - 重启 App                                   │    │
│  └──────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. Update Manifest（远端）

**位置**: `https://releases.agentos.com/manifest.json`

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
          "size": 52428800,
          "signature": "..."
        },
        "macos-x64": {
          "url": "https://releases.agentos.com/app/v0.4.2/AgentOS-macos-x64.tar.gz",
          "sha256": "def456...",
          "size": 54525952,
          "signature": "..."
        },
        "windows-x64": {
          "url": "https://releases.agentos.com/app/v0.4.2/AgentOS-windows-x64.zip",
          "sha256": "ghi789...",
          "size": 48234496,
          "signature": "..."
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
          "sha256": "jkl012...",
          "size": 35651584
        },
        "macos-x64": {
          "url": "https://releases.agentos.com/runtime/v0.4.2/agentos-runtime-macos-x64",
          "sha256": "mno345...",
          "size": 37748736
        },
        "windows-x64": {
          "url": "https://releases.agentos.com/runtime/v0.4.2/agentos-runtime-windows-x64.exe",
          "sha256": "pqr678...",
          "size": 33554432
        }
      },
      "dependencies": {
        "ollama": ">=0.5.0"
      }
    },
    "ollama": {
      "version": "0.5.4",
      "platforms": {
        "macos-arm64": {
          "url": "https://releases.agentos.com/ollama/v0.5.4/ollama-macos-arm64",
          "sha256": "stu901...",
          "size": 104857600
        },
        "macos-x64": {
          "url": "https://releases.agentos.com/ollama/v0.5.4/ollama-macos-x64",
          "sha256": "vwx234...",
          "size": 108003328
        },
        "windows-x64": {
          "url": "https://releases.agentos.com/ollama/v0.5.4/ollama-windows-x64.exe",
          "sha256": "yz5678...",
          "size": 102760448
        }
      }
    }
  },
  "update_policies": {
    "check_interval_hours": 24,
    "auto_download": false,
    "auto_install": false,
    "allow_downgrade": false
  }
}
```

---

### 2. Version Info（本地）

**位置**:
- `resources/runtime/version.json`
- `resources/ollama/version.json`
- App 内嵌版本信息

**格式**:
```json
{
  "name": "agentos-runtime",
  "version": "0.4.1",
  "build": "20260125",
  "commit": "6aa4aaa",
  "platform": "macos-arm64"
}
```

---

### 3. Update Manager（Rust 模块）

**职责**:
1. 定期检查更新（默认 24 小时）
2. 比较版本号
3. 下载更新包到 `~/.agentos/updates/pending/`
4. 校验 SHA-256
5. 移动到 `staging/`
6. 标记 `pending_update.json`
7. 通知 UI 提示用户重启

**状态机**:
```
IDLE → CHECKING → AVAILABLE → DOWNLOADING → VERIFYING → STAGED → PENDING_RESTART
                     ↓            ↓             ↓
                 NO_UPDATE    FAILED         FAILED
```

**API**:
```rust
pub struct UpdateManager {
    manifest_url: String,
    cache_dir: PathBuf,
    current_versions: HashMap<String, Version>,
}

impl UpdateManager {
    pub async fn check_for_updates(&self) -> Result<Vec<ComponentUpdate>, Error>;
    pub async fn download_update(&self, component: &str) -> Result<(), Error>;
    pub async fn stage_update(&self, component: &str) -> Result<(), Error>;
    pub fn is_update_pending(&self) -> bool;
    pub fn get_pending_updates(&self) -> Vec<PendingUpdate>;
}
```

---

### 4. Updater Helper（独立进程）

**触发时机**: App 退出时检测到 `pending_update.json`

**生命周期**:
```
App 退出
 ↓
检测 pending_update.json
 ↓
启动 updater-helper
 ↓
App 进程退出
 ↓
Helper 执行替换
 ↓
Helper 重启 App
 ↓
Helper 退出
```

**实现**（Rust）:
```rust
// updater-helper/src/main.rs
use std::fs;
use std::process::Command;
use std::time::Duration;
use std::thread;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. 读取待更新清单
    let pending = read_pending_updates()?;

    // 2. 等待主进程完全退出
    thread::sleep(Duration::from_secs(2));

    // 3. 备份现有文件
    for component in &pending.components {
        backup_file(&component.current_path)?;
    }

    // 4. 替换文件
    match replace_files(&pending) {
        Ok(_) => {
            log_success("Update applied successfully");
            // 5. 删除 backup
            cleanup_backups(&pending);
        },
        Err(e) => {
            log_error(&format!("Update failed: {}", e));
            // 6. 回滚
            rollback(&pending)?;
        }
    }

    // 7. 清理 pending 标记
    fs::remove_file(get_pending_update_path())?;

    // 8. 重启 App
    restart_app()?;

    Ok(())
}

fn replace_files(pending: &PendingUpdate) -> Result<(), Error> {
    for component in &pending.components {
        let source = Path::new(&component.staged_path);
        let dest = Path::new(&component.target_path);

        // 复制文件
        fs::copy(source, dest)?;

        // 设置权限（Unix）
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            fs::set_permissions(dest, fs::Permissions::from_mode(0o755))?;
        }
    }
    Ok(())
}

fn rollback(pending: &PendingUpdate) -> Result<(), Error> {
    for component in &pending.components {
        let backup_path = format!("{}.bak", component.target_path);
        fs::copy(&backup_path, &component.target_path)?;
    }
    Ok(())
}
```

---

## 更新流程（详细步骤）

### 阶段 1: 检查更新

```
[App 启动 24 小时后]
 ↓
UpdateManager.check_for_updates()
 ↓
GET https://releases.agentos.com/manifest.json
 ↓
比较 manifest.version 与本地 version.json
 ↓
发现新版本 → 状态: AVAILABLE
 ↓
UI 显示："New update available (v0.4.2)"
```

**用户操作**: 点击 "Download" 或 "Dismiss"

---

### 阶段 2: 下载更新

```
[用户点击 Download]
 ↓
UpdateManager.download_update("agentos-runtime")
 ↓
下载到: ~/.agentos/updates/pending/agentos-runtime-v0.4.2
 ↓
显示进度: "Downloading runtime update... 42%"
 ↓
下载完成 → 状态: VERIFYING
```

**断点续传支持**（HTTP Range）:
```rust
async fn download_with_resume(url: &str, dest: &Path) -> Result<(), Error> {
    let existing_size = if dest.exists() {
        fs::metadata(dest)?.len()
    } else {
        0
    };

    let client = reqwest::Client::new();
    let response = client
        .get(url)
        .header("Range", format!("bytes={}-", existing_size))
        .send()
        .await?;

    // ... 写入文件
}
```

---

### 阶段 3: 校验更新

```
[下载完成]
 ↓
计算 SHA-256
 ↓
sha256(file) == manifest.sha256 ?
 ├─ Yes → 状态: STAGED
 └─ No  → 删除文件，显示错误
```

**实现**:
```rust
use sha2::{Sha256, Digest};

fn verify_checksum(file_path: &Path, expected: &str) -> Result<bool, Error> {
    let mut file = File::open(file_path)?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut file, &mut hasher)?;
    let hash = format!("{:x}", hasher.finalize());
    Ok(hash == expected)
}
```

---

### 阶段 4: 暂存更新

```
[校验通过]
 ↓
移动文件: pending/ → staging/
 ↓
写入 pending_update.json:
{
  "timestamp": "2026-01-30T12:00:00Z",
  "components": [
    {
      "name": "agentos-runtime",
      "version": "0.4.2",
      "staged_path": "~/.agentos/updates/staging/agentos-runtime",
      "target_path": "resources/runtime/agentos-runtime",
      "current_path": "resources/runtime/agentos-runtime"
    }
  ]
}
 ↓
状态: PENDING_RESTART
 ↓
UI 显示: "Update ready. Restart to apply."
```

---

### 阶段 5: 重启并应用

```
[用户点击 Restart]
 ↓
App.on_exit():
  if pending_update.json exists:
    spawn updater-helper
    wait 1s
    exit(0)
 ↓
[updater-helper 启动]
 ↓
等待 App 退出（检测进程）
 ↓
备份: resources/runtime/agentos-runtime → .bak
 ↓
复制: staging/agentos-runtime → resources/runtime/
 ↓
设置权限: chmod +x
 ↓
删除 pending_update.json
 ↓
重启 App
 ↓
helper 退出
 ↓
[App 重启]
 ↓
读取 resources/runtime/version.json
 ↓
版本号 = 0.4.2 ✓
 ↓
显示: "Update applied successfully"
```

---

## 失败场景与恢复

### 场景 1: 下载中断

**检测**: 文件大小 < manifest.size

**恢复**: 断点续传（HTTP Range）

---

### 场景 2: SHA-256 不匹配

**检测**: 校验失败

**恢复**:
1. 删除损坏文件
2. 提示用户重新下载
3. 记录日志到 `~/.agentos/logs/update-error.log`

---

### 场景 3: Helper 崩溃

**检测**: App 重启后发现 `pending_update.json` 仍存在

**恢复**:
1. 显示 "Previous update failed. Rollback?"
2. 用户确认 → 从 `.bak` 恢复
3. 删除 `pending_update.json`

---

### 场景 4: 新版本启动失败

**检测**: 健康检查超时（5s）

**恢复**:
1. 自动回滚到 `.bak`
2. 重启 App
3. 显示 "Update failed. Rolled back to v0.4.1"
4. 上报错误到远端（可选）

---

## 安全措施

### 1. HTTPS 强制

```rust
fn fetch_manifest(url: &str) -> Result<Manifest, Error> {
    if !url.starts_with("https://") {
        return Err(Error::InsecureUrl);
    }
    // ...
}
```

---

### 2. SHA-256 校验

所有下载文件必须通过校验，否则拒绝应用。

---

### 3. 签名验证（可选）

```rust
// 使用 Ed25519 签名
use ed25519_dalek::{PublicKey, Signature, Verifier};

fn verify_manifest_signature(manifest: &str, signature: &str, pubkey: &PublicKey) -> bool {
    let sig = Signature::from_bytes(signature.as_bytes()).unwrap();
    pubkey.verify(manifest.as_bytes(), &sig).is_ok()
}
```

---

### 4. 禁止降级（默认）

```rust
fn can_update(current: &Version, new: &Version) -> bool {
    new > current  // 除非用户明确允许降级
}
```

---

## UI/UX 设计

### 更新通知

```
┌─────────────────────────────────────────┐
│  New Update Available                   │
├─────────────────────────────────────────┤
│  AgentOS v0.4.2 is now available        │
│  (you have v0.4.1)                      │
│                                          │
│  What's new:                            │
│  • Fixed WebSocket ping handling        │
│  • Improved model download progress     │
│  • 15 bug fixes                         │
│                                          │
│  [View Release Notes] [Download] [Skip] │
└─────────────────────────────────────────┘
```

---

### 下载进度

```
┌─────────────────────────────────────────┐
│  Downloading Update                     │
├─────────────────────────────────────────┤
│  Runtime: ████████████░░░░  72%         │
│  Downloaded: 25.3 MB / 35.2 MB          │
│  Speed: 3.2 MB/s                        │
│                                          │
│  [Pause] [Cancel]                       │
└─────────────────────────────────────────┘
```

---

### 准备重启

```
┌─────────────────────────────────────────┐
│  Update Ready                           │
├─────────────────────────────────────────┤
│  AgentOS needs to restart to complete   │
│  the update to v0.4.2.                  │
│                                          │
│  Your chat history will be preserved.   │
│                                          │
│  [Restart Now] [Restart Later]          │
└─────────────────────────────────────────┘
```

---

## 测试策略

### 单元测试

- [ ] `test_version_comparison()`
- [ ] `test_sha256_verification()`
- [ ] `test_download_resume()`
- [ ] `test_manifest_parsing()`

### 集成测试

- [ ] 完整更新流程（模拟服务器）
- [ ] 下载中断恢复
- [ ] 校验失败处理
- [ ] Helper 替换文件

### E2E 测试

| 场景 | 平台 | 预期结果 |
|------|------|---------|
| 正常更新 | macOS/Windows | 重启后版本正确 |
| 网络中断 | 所有 | 断点续传成功 |
| 文件损坏 | 所有 | 拒绝应用，提示重新下载 |
| Helper 崩溃 | 所有 | 下次启动提示回滚 |

---

## 监控与日志

### 日志级别

```
INFO  - 正常更新事件
WARN  - 可恢复的错误（如下载失败）
ERROR - 严重错误（如回滚失败）
```

### 日志格式

```
2026-01-30T12:00:00Z [INFO] UpdateManager: Checking for updates
2026-01-30T12:00:01Z [INFO] UpdateManager: New version available: agentos-runtime v0.4.2
2026-01-30T12:05:30Z [INFO] UpdateManager: Download complete: agentos-runtime (35.2 MB)
2026-01-30T12:05:31Z [INFO] UpdateManager: SHA-256 verification passed
2026-01-30T12:05:32Z [INFO] UpdateManager: Update staged, waiting for restart
2026-01-30T12:10:00Z [INFO] UpdateHelper: Applying update
2026-01-30T12:10:02Z [INFO] UpdateHelper: Files replaced successfully
2026-01-30T12:10:03Z [INFO] App: Restarted with new version v0.4.2
```

---

## 性能指标

| 指标 | 目标值 |
|------|-------|
| 检查更新延迟 | < 2 秒 |
| 下载速度（35 MB） | < 30 秒（宽带）|
| SHA-256 校验时间 | < 1 秒 |
| Helper 替换时间 | < 3 秒 |
| 总重启时间 | < 10 秒 |

---

## 合规性

### 隐私

- ❌ 不收集用户 ID
- ✅ 仅发送平台信息（`macos-arm64`）
- ✅ 所有更新检查通过 HTTPS

### 许可证

- Ollama: MIT（可分发）
- AgentOS Runtime: Apache 2.0（可分发）

---

## 参考实现

- [Tauri Updater](https://tauri.app/v2/guides/distribute/updater/)
- [Electron Auto Updater](https://www.electronjs.org/docs/latest/api/auto-updater)
- [Sparkle Framework (macOS)](https://sparkle-project.org/)

---

## 下一步

1. [ ] 实现 Update Manager 骨架
2. [ ] 搭建 manifest.json 托管（Cloudflare R2）
3. [ ] 编写 Updater Helper
4. [ ] E2E 测试（模拟服务器）

---

**审阅人**: TBD
**批准状态**: 草稿
