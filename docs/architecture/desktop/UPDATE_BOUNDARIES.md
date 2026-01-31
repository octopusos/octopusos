# AgentOS Desktop 更新边界规范

> **版本**: 1.0
> **日期**: 2026-01-30
> **状态**: 冻结（Frozen）
> **目的**: 明确定义 AgentOS Desktop 更新机制的边界、约束和失败处理策略

---

## 📑 目录

- [概述](#概述)
- [可更新路径](#可更新路径)
- [不可更新路径](#不可更新路径)
- [文件锁策略](#文件锁策略)
- [备份机制](#备份机制)
- [回滚边界](#回滚边界)
- [失败场景处理](#失败场景处理)
- [变更记录](#变更记录)

---

## 概述

AgentOS Desktop 的更新系统基于**组件级热更新**，通过 `updater-helper` 在 App 退出后替换文件。本文档定义了更新机制的**安全边界**，确保用户数据不受影响。

### 核心约束

| 约束 | 说明 |
|------|------|
| **不可运行时更新** | 运行中的二进制文件不可被覆盖 |
| **用户数据隔离** | 用户数据目录永远不可被更新触及 |
| **强制备份** | 替换前必须创建 `.bak` 备份 |
| **自动回滚** | 更新失败时自动恢复到备份 |

---

## 可更新路径

以下路径可以被 `updater-helper` 在 **App 完全退出后** 替换：

### 白名单（Whitelist）

| 路径 | 描述 | 更新方式 | 验证要求 |
|------|------|---------|---------|
| `resources/runtime/agentos-runtime(.exe)` | AgentOS Runtime 可执行文件 | 完整替换 | SHA-256 + 权限检查 |
| `resources/runtime/version.json` | Runtime 版本信息 | 完整替换 | JSON 格式验证 |
| `resources/ollama/ollama(.exe)` | Ollama 服务器 | 完整替换 | SHA-256 + 权限检查 |
| `resources/ollama/version.json` | Ollama 版本信息 | 完整替换 | JSON 格式验证 |
| `resources/updater/manifest.json` | 更新清单缓存 | 完整替换 | JSON 格式验证 |

⚠️ **注意**: 以上路径仅在以下条件全部满足时可更新：
1. ✅ App 主进程已退出
2. ✅ 所有 sidecar 进程（runtime/ollama）已停止
3. ✅ 已创建 `.bak` 备份
4. ✅ SHA-256 校验通过

---

### 更新流程

```
[用户点击 "Restart to Update"]
 ↓
停止所有 sidecar 进程
 ├─ agentos-runtime (SIGTERM → 10s → SIGKILL)
 └─ ollama (SIGTERM → 10s → SIGKILL)
 ↓
App 主进程退出
 ↓
启动 updater-helper (独立进程)
 ↓
等待 2 秒（确保所有进程退出）
 ↓
创建备份
 ├─ resources/runtime/agentos-runtime → .bak
 └─ resources/ollama/ollama → .bak
 ↓
替换文件（从 staging/ 复制）
 ├─ 验证 SHA-256
 ├─ 复制文件
 └─ 设置权限（Unix: 0755）
 ↓
验证新文件
 ├─ 文件存在性
 ├─ 文件大小
 └─ 可执行性
 ↓
成功 → 删除 .bak 备份
失败 → 回滚到 .bak
 ↓
清理 pending_update.json
 ↓
重启 App
 ↓
updater-helper 退出
```

---

### 更新实现（伪代码）

```rust
// updater-helper/src/main.rs

fn apply_update() -> Result<(), Error> {
    // 1. 读取待更新清单
    let pending = read_pending_updates()?;

    // 2. 等待主进程退出
    wait_for_app_exit()?;

    // 3. 备份现有文件
    let backups = backup_files(&pending)?;

    // 4. 替换文件
    match replace_files(&pending) {
        Ok(_) => {
            log::info!("Update applied successfully");
            cleanup_backups(&backups);
            Ok(())
        }
        Err(e) => {
            log::error!("Update failed: {}", e);
            rollback_from_backups(&backups)?;
            Err(e)
        }
    }
}

fn replace_files(pending: &PendingUpdate) -> Result<(), Error> {
    for component in &pending.components {
        let source = &component.staged_path;
        let dest = &component.target_path;

        // 验证 SHA-256
        verify_checksum(source, &component.expected_sha256)?;

        // 复制文件
        std::fs::copy(source, dest)?;

        // 设置权限（Unix）
        #[cfg(unix)]
        set_executable(dest)?;

        // 验证新文件
        verify_file(dest)?;
    }
    Ok(())
}
```

---

## 不可更新路径

以下路径**永远不可被更新机制触及**，任何尝试修改这些路径的操作都会被拒绝。

### 黑名单（Blacklist）

| 路径类别 | 具体路径 | 原因 | 保护措施 |
|---------|---------|------|---------|
| **用户数据** | `~/.agentos/models/` | 用户下载的模型（可达 50 GB） | 硬编码禁止 |
| **用户配置** | `~/.agentos/config/` | 用户自定义配置 | 硬编码禁止 |
| **任务数据库** | `~/.agentos/agentos.db` | 任务历史和状态 | 硬编码禁止 + SQLite 锁 |
| **许可证文件** | `resources/licenses/` | 第三方许可证（只读） | 文件系统只读权限 |
| **App 主程序** | `MacOS/AgentOS(.exe)` | 通过 Tauri Updater 更新 | 仅 Tauri Updater 可触及 |

---

### 路径保护实现

```rust
const PROTECTED_PATHS: &[&str] = &[
    ".agentos/models",
    ".agentos/config",
    ".agentos/agentos.db",
    "resources/licenses",
    "MacOS/AgentOS",
    "AgentOS.exe",
];

fn is_path_protected(path: &Path) -> bool {
    PROTECTED_PATHS.iter().any(|p| path.to_string_lossy().contains(p))
}

fn validate_update_path(path: &Path) -> Result<(), Error> {
    if is_path_protected(path) {
        return Err(Error::ProtectedPath(path.to_path_buf()));
    }
    Ok(())
}
```

---

### 用户数据迁移策略

⚠️ **重要**: 用户数据**不可自动迁移**，必须由用户明确授权。

```
[跨大版本升级 0.x → 1.0]
 ↓
检测到需要数据迁移
 ↓
弹出对话框:
┌─────────────────────────────────────────┐
│  Data Migration Required                │
├─────────────────────────────────────────┤
│  AgentOS 1.0 requires upgrading your    │
│  task database schema.                  │
│                                          │
│  • Your data will be backed up to:      │
│    ~/.agentos/backups/agentos.db.bak    │
│                                          │
│  • This process may take 2-5 minutes    │
│                                          │
│  [Cancel] [Backup and Upgrade]          │
└─────────────────────────────────────────┘
 ↓
用户确认 → 备份 → 迁移 → 验证
用户取消 → 回滚到旧版本
```

---

## 文件锁策略

### 操作系统级文件锁

| 平台 | 锁机制 | 行为 |
|------|-------|------|
| **macOS/Linux** | 进程占用 | 运行中的可执行文件无法删除，但可重命名 |
| **Windows** | 文件锁 | 运行中的 `.exe` 无法删除或重命名 |

---

### 运行时锁定检测

```rust
fn is_file_locked(path: &Path) -> bool {
    #[cfg(windows)]
    {
        // Windows: 尝试打开文件进行独占访问
        match std::fs::OpenOptions::new()
            .write(true)
            .open(path)
        {
            Ok(_) => false,  // 未锁定
            Err(e) if e.kind() == std::io::ErrorKind::PermissionDenied => true,
            Err(_) => false,
        }
    }

    #[cfg(unix)]
    {
        // Unix: 检查进程是否仍在运行
        is_process_running_for_file(path)
    }
}

fn wait_for_unlock(path: &Path, timeout: Duration) -> Result<(), Error> {
    let start = Instant::now();
    while is_file_locked(path) {
        if start.elapsed() > timeout {
            return Err(Error::FileLockedTimeout(path.to_path_buf()));
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    Ok(())
}
```

---

### 更新前锁定检查

```rust
fn pre_update_check() -> Result<(), Error> {
    let runtime_path = get_runtime_path();
    let ollama_path = get_ollama_path();

    // 1. 检查进程是否已停止
    if is_process_running("agentos-runtime") {
        return Err(Error::ProcessStillRunning("agentos-runtime"));
    }
    if is_process_running("ollama") {
        return Err(Error::ProcessStillRunning("ollama"));
    }

    // 2. 检查文件锁
    wait_for_unlock(&runtime_path, Duration::from_secs(10))?;
    wait_for_unlock(&ollama_path, Duration::from_secs(10))?;

    Ok(())
}
```

---

## 备份机制

### 备份策略

| 文件类型 | 备份方式 | 保留时间 | 存储位置 |
|---------|---------|---------|---------|
| **可执行文件** | 完整复制 | 直到新版本验证成功 | 同目录 `.bak` 后缀 |
| **配置文件** | 完整复制 | 永久（用户手动删除） | `~/.agentos/backups/` |
| **数据库** | SQLite backup API | 永久 | `~/.agentos/backups/` |

---

### 备份实现

```rust
fn backup_file(path: &Path) -> Result<PathBuf, Error> {
    let backup_path = path.with_extension(
        format!("{}.bak", path.extension().unwrap_or_default().to_string_lossy())
    );

    std::fs::copy(path, &backup_path)?;

    // 验证备份
    verify_backup(path, &backup_path)?;

    log::info!("Backup created: {}", backup_path.display());
    Ok(backup_path)
}

fn verify_backup(original: &Path, backup: &Path) -> Result<(), Error> {
    let original_hash = sha256_file(original)?;
    let backup_hash = sha256_file(backup)?;

    if original_hash != backup_hash {
        return Err(Error::BackupVerificationFailed);
    }

    Ok(())
}

fn sha256_file(path: &Path) -> Result<String, Error> {
    use sha2::{Sha256, Digest};
    use std::io::Read;

    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0; 4096];

    loop {
        let bytes_read = file.read(&mut buffer)?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }

    Ok(format!("{:x}", hasher.finalize()))
}
```

---

### 数据库备份（特殊处理）

```rust
fn backup_database(db_path: &Path) -> Result<PathBuf, Error> {
    use rusqlite::Connection;

    let backup_dir = get_user_data_dir().join("backups");
    std::fs::create_dir_all(&backup_dir)?;

    let timestamp = chrono::Utc::now().format("%Y%m%d%H%M%S");
    let backup_path = backup_dir.join(format!("agentos-{}.db", timestamp));

    // 使用 SQLite 的 backup API（在线备份）
    let source = Connection::open(db_path)?;
    let dest = Connection::open(&backup_path)?;

    source.backup(rusqlite::DatabaseName::Main, &dest, None)?;

    log::info!("Database backup created: {}", backup_path.display());
    Ok(backup_path)
}
```

---

## 回滚边界

### 可回滚场景

以下场景下，更新失败可以**自动回滚**到备份：

| 场景 | 检测方式 | 回滚操作 |
|------|---------|---------|
| **文件替换失败** | 复制操作异常 | 恢复 `.bak` 文件 |
| **SHA-256 不匹配** | 校验失败 | 拒绝替换，删除损坏文件 |
| **权限设置失败** | `chmod` 异常 | 恢复 `.bak` 文件 |
| **新版本启动失败** | 健康检查超时 | 恢复 `.bak` 文件并重启 |

---

### 不可回滚场景（需要重新安装）

以下场景下，**无法自动恢复**，用户需要重新安装 App：

| 场景 | 原因 | 用户操作 |
|------|------|---------|
| **备份文件损坏** | `.bak` 文件校验失败 | 重新下载并安装 |
| **updater-helper 崩溃** | 进程意外终止 | 手动删除 pending_update.json 并重启 |
| **磁盘空间不足** | 无法写入备份 | 清理磁盘空间后重试 |
| **文件系统权限错误** | 无法访问 resources/ | 修复权限或重新安装 |

---

### 回滚实现

```rust
fn rollback_from_backups(backups: &[PathBuf]) -> Result<(), Error> {
    log::warn!("Rolling back from backups...");

    for backup_path in backups {
        let original_path = backup_path.with_extension("");

        // 删除损坏的新文件
        if original_path.exists() {
            std::fs::remove_file(&original_path)?;
        }

        // 恢复备份
        std::fs::copy(backup_path, &original_path)?;

        // 设置权限
        #[cfg(unix)]
        set_executable(&original_path)?;

        log::info!("Rolled back: {}", original_path.display());
    }

    Ok(())
}
```

---

### 启动时自动回滚

```rust
fn startup_rollback_check() -> Result<(), Error> {
    let pending_update_path = get_user_data_dir().join("updates/pending_update.json");

    // 如果发现未完成的更新，说明上次失败
    if pending_update_path.exists() {
        log::warn!("Detected incomplete update from previous run");

        let backups = find_backup_files()?;
        if !backups.is_empty() {
            // 自动回滚
            rollback_from_backups(&backups)?;
            std::fs::remove_file(&pending_update_path)?;

            show_notification(
                "Update Failed",
                "The previous update was incomplete and has been rolled back."
            );
        }
    }

    Ok(())
}
```

---

## 失败场景处理

### 场景矩阵

| 场景 | 检测方法 | 自动恢复 | 用户操作 |
|------|---------|---------|---------|
| **1. 下载中断** | 文件大小 < expected | ✅ 断点续传 | 无需操作 |
| **2. SHA-256 不匹配** | 校验失败 | ✅ 删除文件，提示重新下载 | 点击"重试" |
| **3. 磁盘空间不足** | 写入失败（ENOSPC） | ❌ | 清理磁盘，点击"重试" |
| **4. updater-helper 崩溃** | 进程退出码 != 0 | ⚠️ 下次启动时回滚 | 重启 App |
| **5. 新版本启动失败** | 健康检查超时 | ✅ 自动回滚到 .bak | 无需操作 |
| **6. 备份文件损坏** | 备份校验失败 | ❌ | 重新安装 App |
| **7. 权限错误** | 无法写入 resources/ | ❌ | 修复权限或重新安装 |
| **8. 文件被锁定** | 进程未退出 | ⚠️ 等待 10s 超时 | 强制关闭进程 |

---

### 场景 1: 下载中断

```rust
async fn download_with_resume(url: &str, dest: &Path, expected_size: u64) -> Result<(), Error> {
    let existing_size = if dest.exists() {
        std::fs::metadata(dest)?.len()
    } else {
        0
    };

    if existing_size == expected_size {
        log::info!("File already downloaded completely");
        return Ok(());
    }

    if existing_size > 0 {
        log::info!("Resuming download from {} bytes", existing_size);
    }

    let client = reqwest::Client::new();
    let response = client
        .get(url)
        .header("Range", format!("bytes={}-", existing_size))
        .send()
        .await?;

    // ... 写入文件
    Ok(())
}
```

---

### 场景 2: SHA-256 不匹配

```rust
fn handle_checksum_failure(file_path: &Path, expected: &str, actual: &str) -> Result<(), Error> {
    log::error!(
        "SHA-256 mismatch for {}: expected {}, got {}",
        file_path.display(),
        expected,
        actual
    );

    // 删除损坏文件
    std::fs::remove_file(file_path)?;

    // 显示错误通知
    show_notification(
        "Update Failed",
        &format!("Downloaded file is corrupted. Please retry.\n\nExpected: {}\nActual: {}", expected, actual)
    );

    Err(Error::ChecksumMismatch {
        expected: expected.to_string(),
        actual: actual.to_string(),
    })
}
```

---

### 场景 5: 新版本启动失败

```rust
fn startup_health_check() -> Result<(), Error> {
    let runtime_path = get_runtime_path();
    let backup_path = format!("{}.bak", runtime_path.display());

    // 尝试启动 runtime
    match spawn_sidecar(&runtime_path) {
        Ok(handle) => {
            // 等待健康检查
            match wait_for_health("http://127.0.0.1:8000/health", Duration::from_secs(10)) {
                Ok(_) => {
                    log::info!("Health check passed");
                    // 删除备份（新版本正常）
                    if Path::new(&backup_path).exists() {
                        std::fs::remove_file(&backup_path)?;
                    }
                    Ok(())
                }
                Err(_) => {
                    log::error!("Health check failed, rolling back");
                    handle.kill()?;
                    rollback_and_restart(&runtime_path, &backup_path)
                }
            }
        }
        Err(e) => {
            log::error!("Failed to start runtime: {}", e);
            rollback_and_restart(&runtime_path, &backup_path)
        }
    }
}

fn rollback_and_restart(runtime_path: &str, backup_path: &str) -> Result<(), Error> {
    if !Path::new(backup_path).exists() {
        return Err(Error::NoBackupAvailable);
    }

    // 恢复备份
    std::fs::copy(backup_path, runtime_path)?;

    // 设置权限
    #[cfg(unix)]
    set_executable(Path::new(runtime_path))?;

    // 重新启动
    spawn_sidecar(runtime_path)?;

    show_notification(
        "Update Rolled Back",
        "The new version failed to start and has been rolled back to the previous version."
    );

    Ok(())
}
```

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-30 | 初始版本，定义更新边界 | Claude |

---

## 附录：错误码定义

```rust
#[derive(Debug, thiserror::Error)]
pub enum UpdateError {
    #[error("Protected path cannot be updated: {0}")]
    ProtectedPath(PathBuf),

    #[error("File is locked by another process: {0}")]
    FileLocked(PathBuf),

    #[error("File locked timeout after waiting: {0}")]
    FileLockedTimeout(PathBuf),

    #[error("Process still running: {0}")]
    ProcessStillRunning(String),

    #[error("SHA-256 checksum mismatch: expected {expected}, got {actual}")]
    ChecksumMismatch { expected: String, actual: String },

    #[error("Backup verification failed")]
    BackupVerificationFailed,

    #[error("No backup available for rollback")]
    NoBackupAvailable,

    #[error("Disk space insufficient: need {need} bytes, available {available} bytes")]
    DiskSpaceInsufficient { need: u64, available: u64 },

    #[error("Update helper crashed with exit code: {0}")]
    UpdateHelperCrashed(i32),
}
```

---

**审阅状态**: 待审阅
**下一步**: 团队确认更新边界后冻结此文档
