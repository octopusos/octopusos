# AgentOS Desktop 目录结构规范

> **版本**: 1.0
> **日期**: 2026-01-30
> **状态**: 冻结（Frozen）
> **目的**: 定义 AgentOS Desktop 的目录结构、文件布局及访问约束

---

## 📑 目录

- [概述](#概述)
- [App 安装目录结构](#app-安装目录结构)
- [用户数据目录](#用户数据目录)
- [路径访问约束](#路径访问约束)
- [平台差异](#平台差异)
- [冲突解决规则](#冲突解决规则)
- [变更记录](#变更记录)

---

## 概述

AgentOS Desktop 的目录结构分为两个核心部分：

1. **App 安装目录**：包含应用程序本体及其运行时组件，由更新机制管理
2. **用户数据目录**：存储用户生成的数据和配置，永远不可被更新覆盖

### 设计原则

| 原则 | 说明 |
|------|------|
| **分离关注点** | 应用程序代码与用户数据完全隔离 |
| **更新安全** | 用户数据目录不可被更新机制触及 |
| **跨平台一致性** | 不同平台使用相同逻辑结构 |
| **可预测性** | 所有路径在启动时确定，不动态更改 |

---

## App 安装目录结构

### macOS 布局

```
AgentOS.app/
└── Contents/
    ├── MacOS/
    │   └── AgentOS                          # Tauri 主程序（不可直接更新）
    ├── Info.plist                           # App 元数据
    └── Resources/
        ├── runtime/                         # ✅ 可更新
        │   ├── agentos-runtime              # Python 打包后的可执行文件
        │   ├── version.json                 # 版本声明文件
        │   └── config/                      # 内置配置模板
        │       ├── default-settings.json
        │       └── default-providers.json
        ├── ollama/                          # ✅ 可更新
        │   ├── ollama                       # Ollama 二进制
        │   └── version.json                 # Ollama 版本信息
        ├── updater/                         # ⚠️ 更新辅助程序
        │   ├── manifest.json                # 更新清单缓存
        │   └── updater-helper               # 更新辅助进程
        └── licenses/                        # ❌ 只读资源
            ├── AgentOS-LICENSE
            ├── Ollama-LICENSE.txt
            └── THIRD_PARTY_NOTICES.txt
```

### Windows 布局

```
C:\Program Files\AgentOS\
├── AgentOS.exe                              # Tauri 主程序（不可直接更新）
└── resources\
    ├── runtime\                             # ✅ 可更新
    │   ├── agentos-runtime.exe
    │   ├── version.json
    │   └── config\
    │       ├── default-settings.json
    │       └── default-providers.json
    ├── ollama\                              # ✅ 可更新
    │   ├── ollama.exe
    │   └── version.json
    ├── updater\                             # ⚠️ 更新辅助程序
    │   ├── manifest.json
    │   └── updater-helper.exe
    └── licenses\                            # ❌ 只读资源
        ├── AgentOS-LICENSE.txt
        ├── Ollama-LICENSE.txt
        └── THIRD_PARTY_NOTICES.txt
```

### 目录权限要求

| 路径 | macOS 权限 | Windows 权限 | 说明 |
|------|-----------|-------------|------|
| `MacOS/AgentOS` | `0755` (rx) | ReadOnly | 主程序，通过 Tauri Updater 更新 |
| `Resources/runtime/` | `0755` (rx) | ReadOnly | 可被 UpdaterHelper 替换 |
| `Resources/ollama/` | `0755` (rx) | ReadOnly | 可被 UpdaterHelper 替换 |
| `Resources/licenses/` | `0644` (r) | ReadOnly | 只读资源 |

⚠️ **重要约束**：
- 运行中的二进制文件**不可被覆盖**（操作系统限制）
- 必须通过 `updater-helper` 在 App 退出后替换
- 替换前必须创建 `.bak` 备份

---

## 用户数据目录

### 跨平台路径映射

| 平台 | 用户数据目录 |
|------|------------|
| **macOS** | `~/.agentos/` |
| **Linux** | `~/.agentos/` |
| **Windows** | `%USERPROFILE%\.agentos\` |

### 完整目录结构

```
~/.agentos/                                  # 用户数据根目录
├── models/                                  # ❌ 永远不可删除
│   ├── llama3/                              # Ollama 模型存储
│   │   ├── model
│   │   └── manifest
│   ├── codellama/
│   └── ...
├── config/                                  # ❌ 永远不可删除
│   ├── settings.json                        # 用户配置
│   ├── providers.json                       # Provider 配置
│   ├── ports.json                           # 端口分配记录
│   └── model-preferences.json               # 模型偏好设置
├── logs/                                    # ✅ 可清理（保留 7 天）
│   ├── agentos-runtime.log
│   ├── ollama.log
│   ├── desktop-app.log
│   └── update.log                           # 更新日志
├── cache/                                   # ✅ 可清理
│   ├── health-check-cache.json
│   └── tmp/                                 # 临时文件
├── updates/                                 # ⚠️ 更新管理目录
│   ├── pending/                             # 下载中的更新
│   │   └── agentos-runtime-v0.4.2.tmp
│   ├── staging/                             # 已下载待应用
│   │   └── agentos-runtime-v0.4.2
│   └── pending_update.json                  # 待应用更新清单
└── agentos.db                               # ❌ 永远不可删除
```

### 目录用途说明

| 目录 | 用途 | 可被更新 | 可被清理 | 备份优先级 |
|------|------|---------|---------|----------|
| `models/` | Ollama 模型存储 | ❌ | ❌ | 高 |
| `config/` | 用户配置文件 | ❌ | ❌ | 高 |
| `logs/` | 运行日志 | ❌ | ✅ (7天) | 低 |
| `cache/` | 临时缓存 | ❌ | ✅ | 低 |
| `updates/` | 更新暂存 | ✅ | ✅ | 中 |
| `agentos.db` | 任务数据库 | ❌ | ❌ | 高 |

### 磁盘空间预估

| 组件 | 典型大小 | 最大预期 |
|------|---------|---------|
| `models/` (单模型) | 4-8 GB | 50 GB |
| `config/` | 10 KB | 100 KB |
| `logs/` | 50 MB | 500 MB |
| `cache/` | 100 MB | 1 GB |
| `updates/` | 200 MB | 500 MB |
| `agentos.db` | 10 MB | 1 GB |

⚠️ **最小磁盘空间要求**: 20 GB（用于至少一个模型）

---

## 路径访问约束

### 可更新路径（白名单）

以下路径可以被 `updater-helper` 在 App 退出后替换：

```
✅ resources/runtime/agentos-runtime(.exe)
✅ resources/runtime/version.json
✅ resources/ollama/ollama(.exe)
✅ resources/ollama/version.json
✅ resources/updater/manifest.json
```

**更新流程**：
1. 停止所有 sidecar 进程
2. App 退出
3. `updater-helper` 启动
4. 创建 `.bak` 备份
5. 替换文件
6. 验证成功 → 删除备份
7. 验证失败 → 回滚
8. 重启 App

### 不可更新路径（黑名单）

以下路径**永远不可被更新机制触及**：

```
❌ ~/.agentos/models/              # 用户下载的模型
❌ ~/.agentos/config/              # 用户配置
❌ ~/.agentos/agentos.db           # 任务数据库
❌ resources/licenses/             # 许可证文件（只读）
❌ MacOS/AgentOS(.exe)             # 主程序（通过 Tauri Updater）
```

### 运行时锁定

以下文件在 App 运行时**不可被修改**：

```
🔒 resources/runtime/agentos-runtime (进程运行中)
🔒 resources/ollama/ollama (进程运行中)
🔒 ~/.agentos/agentos.db (SQLite 锁)
```

**解决方案**：
- 更新必须在 App **完全退出**后应用
- 使用 `updater-helper` 独立进程处理替换
- 失败时自动回滚到 `.bak` 文件

---

## 平台差异

### 路径分隔符

| 平台 | 分隔符 | 示例 |
|------|-------|------|
| macOS/Linux | `/` | `~/.agentos/models/` |
| Windows | `\` | `%USERPROFILE%\.agentos\models\` |

**代码处理**：
```rust
use std::path::PathBuf;

fn get_user_data_dir() -> PathBuf {
    let home = std::env::var("HOME")  // macOS/Linux
        .or_else(|_| std::env::var("USERPROFILE"))  // Windows
        .expect("Cannot determine home directory");

    PathBuf::from(home).join(".agentos")
}
```

### 隐藏目录

| 平台 | 隐藏机制 |
|------|---------|
| macOS/Linux | 前缀 `.` (`.agentos`) |
| Windows | 需要设置 `FILE_ATTRIBUTE_HIDDEN` |

**Windows 实现**：
```rust
#[cfg(windows)]
fn hide_directory(path: &Path) -> std::io::Result<()> {
    use std::os::windows::fs::MetadataExt;
    use std::fs;

    let metadata = fs::metadata(path)?;
    let mut attrs = metadata.file_attributes();
    attrs |= 0x2; // FILE_ATTRIBUTE_HIDDEN
    // ... 设置属性
    Ok(())
}
```

### 权限管理

| 平台 | 可执行权限 |
|------|-----------|
| macOS/Linux | `chmod +x` (0755) |
| Windows | 无需设置 |

**跨平台代码**：
```rust
#[cfg(unix)]
fn set_executable(path: &Path) -> std::io::Result<()> {
    use std::os::unix::fs::PermissionsExt;
    use std::fs;

    let mut perms = fs::metadata(path)?.permissions();
    perms.set_mode(0o755);
    fs::set_permissions(path, perms)
}

#[cfg(windows)]
fn set_executable(_path: &Path) -> std::io::Result<()> {
    Ok(()) // Windows 不需要
}
```

---

## 冲突解决规则

### 场景 1: 模型目录已存在（迁移）

**问题**: 用户之前安装过 Ollama，已有 `~/.ollama/models/`

**解决**:
```
首次启动 → 检测 ~/.ollama/models/
 ↓
提示: "Existing Ollama models detected. Import them?"
 ├─ Yes → 创建符号链接: ~/.agentos/models -> ~/.ollama/models/
 └─ No  → 创建独立目录: ~/.agentos/models/
```

**实现**:
```rust
fn handle_existing_models() -> Result<(), Error> {
    let ollama_models = Path::new(&env::var("HOME")?).join(".ollama/models");
    let agentos_models = get_user_data_dir().join("models");

    if ollama_models.exists() && !agentos_models.exists() {
        // 提示用户选择
        if user_confirms_import() {
            #[cfg(unix)]
            std::os::unix::fs::symlink(&ollama_models, &agentos_models)?;

            #[cfg(windows)]
            std::os::windows::fs::symlink_dir(&ollama_models, &agentos_models)?;
        } else {
            std::fs::create_dir_all(&agentos_models)?;
        }
    }
    Ok(())
}
```

### 场景 2: 端口冲突

**问题**: 默认端口 8000/11434 被占用

**解决**:
```
启动时检测端口
 ↓
端口被占用 → 尝试备用端口范围
 ├─ 8001, 8002, ... 8010
 └─ 11435, 11436, ... 11444
 ↓
记录到 ~/.agentos/config/ports.json
```

**ports.json 格式**:
```json
{
  "agentos_runtime": {
    "default": 8000,
    "active": 8002,
    "last_checked": "2026-01-30T12:00:00Z"
  },
  "ollama_server": {
    "default": 11434,
    "active": 11434,
    "last_checked": "2026-01-30T12:00:00Z"
  }
}
```

### 场景 3: 磁盘空间不足

**问题**: 用户数据目录所在磁盘剩余空间 < 20 GB

**解决**:
```
首次启动 → 检测磁盘空间
 ↓
剩余 < 20 GB
 ↓
警告: "Low disk space. Recommend choosing a different location."
 ├─ Choose Different Location → 弹出目录选择器
 └─ Continue Anyway → 继续（记录警告）
```

**配置存储**:
```json
{
  "custom_model_path": "/Volumes/ExternalDrive/.agentos-models/",
  "disk_space_warning_dismissed": true,
  "timestamp": "2026-01-30T12:00:00Z"
}
```

### 场景 4: 更新失败导致文件损坏

**问题**: `updater-helper` 崩溃，二进制文件损坏

**检测**:
```
App 启动 → 健康检查失败
 ↓
检测 resources/runtime/agentos-runtime.bak 存在
 ↓
自动回滚
```

**实现**:
```rust
fn startup_health_check() -> Result<(), Error> {
    let runtime_path = get_runtime_path();
    let backup_path = format!("{}.bak", runtime_path.display());

    // 尝试启动 runtime
    match spawn_sidecar(&runtime_path) {
        Ok(_) => Ok(()),
        Err(_) => {
            if Path::new(&backup_path).exists() {
                log::warn!("Runtime corrupted, rolling back to backup");
                std::fs::copy(&backup_path, &runtime_path)?;
                spawn_sidecar(&runtime_path)?;
            }
            Ok(())
        }
    }
}
```

---

## 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-01-30 | 初始版本，冻结目录结构 | Claude |

---

## 附录：环境变量

### AgentOS Runtime 使用的环境变量

```bash
AGENTOS_DATA_DIR=~/.agentos
AGENTOS_CONFIG_DIR=~/.agentos/config
AGENTOS_LOG_DIR=~/.agentos/logs
AGENTOS_PORT=8000  # 或动态分配的端口
```

### Ollama 使用的环境变量

```bash
OLLAMA_MODELS=~/.agentos/models
OLLAMA_HOST=127.0.0.1:11434  # 或动态分配的端口
OLLAMA_KEEP_ALIVE=5m
```

---

**审阅状态**: 待审阅
**下一步**: 团队签字确认后冻结此文档
