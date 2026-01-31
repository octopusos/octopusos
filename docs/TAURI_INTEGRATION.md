# Tauri 集成指南：AgentOS Runtime Sidecar

本指南详细说明如何将打包后的 AgentOS Runtime 集成到 Tauri Desktop 应用中。

## 概述

AgentOS Desktop 采用 Tauri + Rust + React 架构，其中 Python Runtime 作为 Sidecar 进程运行，提供后端 API 服务。

**架构图**:
```
┌─────────────────────────────────────────────────┐
│            Tauri Desktop 应用                    │
│  ┌─────────────────┐    ┌──────────────────┐   │
│  │   React 前端     │◄───│  Rust 后端        │   │
│  │   (Vite)        │    │  (Tauri Core)    │   │
│  └─────────────────┘    └──────────┬───────┘   │
│                                    │           │
│                         启动/管理   │           │
│                                    ▼           │
│                    ┌──────────────────────┐    │
│                    │  AgentOS Runtime     │    │
│                    │  (Python Sidecar)    │    │
│                    └──────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 第 1 步：准备 Runtime 二进制文件

### 1.1 构建 Runtime

```bash
cd /Users/pangge/PycharmProjects/AgentOS

# 激活虚拟环境
source .venv/bin/activate

# 构建 Runtime
python3 scripts/build_runtime.py

# 验证输出
ls -lh dist/agentos-runtime-*
```

### 1.2 Tauri 命名约定

Tauri 使用特定的文件命名格式来识别不同平台的 sidecar：

| 平台 | 源文件 | Tauri 目标文件名 |
|------|--------|------------------|
| macOS ARM64 | `agentos-runtime-macos-arm64` | `agentos-runtime-aarch64-apple-darwin` |
| macOS Intel | `agentos-runtime-macos-x64` | `agentos-runtime-x86_64-apple-darwin` |
| Windows x64 | `agentos-runtime-windows-x64.exe` | `agentos-runtime-x86_64-pc-windows-msvc.exe` |

---

## 第 2 步：复制到 Tauri 项目

### 2.1 创建 Sidecar 目录

```bash
mkdir -p /Users/pangge/PycharmProjects/AgentOS/desktop/src-tauri/binaries
```

### 2.2 复制并重命名二进制文件

**macOS ARM64** (当前平台):
```bash
cp /Users/pangge/PycharmProjects/AgentOS/dist/agentos-runtime-macos-arm64 \
   /Users/pangge/PycharmProjects/AgentOS/desktop/src-tauri/binaries/agentos-runtime-aarch64-apple-darwin
```

**macOS Intel** (如果已构建):
```bash
cp /Users/pangge/PycharmProjects/AgentOS/dist/agentos-runtime-macos-x64 \
   /Users/pangge/PycharmProjects/AgentOS/desktop/src-tauri/binaries/agentos-runtime-x86_64-apple-darwin
```

**Windows x64** (如果已构建):
```bash
cp /Users/pangge/PycharmProjects/AgentOS/dist/agentos-runtime-windows-x64.exe \
   /Users/pangge/PycharmProjects/AgentOS/desktop/src-tauri/binaries/agentos-runtime-x86_64-pc-windows-msvc.exe
```

### 2.3 设置权限

```bash
chmod +x /Users/pangge/PycharmProjects/AgentOS/desktop/src-tauri/binaries/agentos-runtime-*
```

---

## 第 3 步：配置 Tauri

### 3.1 编辑 tauri.conf.json

**文件路径**: `desktop/src-tauri/tauri.conf.json`

在 `tauri.bundle` 配置中添加 `externalBin`:

```json
{
  "tauri": {
    "bundle": {
      "externalBin": [
        "binaries/agentos-runtime"
      ],
      "identifier": "com.agentos.desktop",
      "targets": "all"
    }
  }
}
```

**注意**:
- 只需指定基础名称 `agentos-runtime`
- Tauri 会自动根据平台添加后缀（如 `-aarch64-apple-darwin`）

### 3.2 完整配置示例

```json
{
  "build": {
    "beforeDevCommand": "pnpm dev",
    "beforeBuildCommand": "pnpm build",
    "devPath": "http://localhost:1420",
    "distDir": "../dist"
  },
  "package": {
    "productName": "AgentOS",
    "version": "0.3.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "all": false,
        "sidecar": true
      },
      "http": {
        "all": true,
        "request": true,
        "scope": ["http://127.0.0.1:*"]
      }
    },
    "bundle": {
      "active": true,
      "category": "DeveloperTool",
      "copyright": "",
      "externalBin": [
        "binaries/agentos-runtime"
      ],
      "identifier": "com.agentos.desktop",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ],
      "longDescription": "",
      "macOS": {
        "entitlements": null,
        "exceptionDomain": "",
        "frameworks": [],
        "providerShortName": null,
        "signingIdentity": null
      },
      "resources": [],
      "shortDescription": "",
      "targets": "all",
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "security": {
      "csp": null
    },
    "updater": {
      "active": false
    },
    "windows": [
      {
        "fullscreen": false,
        "height": 600,
        "resizable": true,
        "title": "AgentOS",
        "width": 800
      }
    ]
  }
}
```

---

## 第 4 步：Rust 后端实现

### 4.1 创建 Sidecar 管理模块

**文件路径**: `desktop/src-tauri/src/runtime.rs`

```rust
use tauri::api::process::{Command, CommandChild, CommandEvent};
use std::sync::Mutex;
use tauri::State;

pub struct RuntimeState {
    pub child: Mutex<Option<CommandChild>>,
}

#[tauri::command]
pub async fn start_runtime(
    port: u16,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    // 检查是否已经运行
    let mut child_guard = state.child.lock().unwrap();
    if child_guard.is_some() {
        return Err("Runtime already running".to_string());
    }

    // 启动 sidecar
    let (mut rx, child) = Command::new_sidecar("agentos-runtime")
        .map_err(|e| format!("Failed to create sidecar: {}", e))?
        .args(&[
            "web",
            "--host", "127.0.0.1",
            "--port", &port.to_string(),
        ])
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    // 存储 child 进程
    *child_guard = Some(child);

    // 异步监听输出
    tokio::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    log::info!("[Runtime] {}", line);
                }
                CommandEvent::Stderr(line) => {
                    log::warn!("[Runtime] {}", line);
                }
                CommandEvent::Error(err) => {
                    log::error!("[Runtime] Error: {}", err);
                }
                CommandEvent::Terminated(payload) => {
                    log::info!("[Runtime] Terminated: {:?}", payload);
                }
                _ => {}
            }
        }
    });

    Ok(format!("Runtime started on port {}", port))
}

#[tauri::command]
pub async fn stop_runtime(
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    let mut child_guard = state.child.lock().unwrap();

    if let Some(mut child) = child_guard.take() {
        child.kill()
            .map_err(|e| format!("Failed to kill runtime: {}", e))?;
        Ok("Runtime stopped".to_string())
    } else {
        Err("Runtime not running".to_string())
    }
}

#[tauri::command]
pub async fn runtime_status(
    state: State<'_, RuntimeState>,
) -> Result<bool, String> {
    let child_guard = state.child.lock().unwrap();
    Ok(child_guard.is_some())
}
```

### 4.2 注册命令和状态

**文件路径**: `desktop/src-tauri/src/main.rs`

```rust
mod runtime;

use runtime::{RuntimeState, start_runtime, stop_runtime, runtime_status};

fn main() {
    tauri::Builder::default()
        .manage(RuntimeState {
            child: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            start_runtime,
            stop_runtime,
            runtime_status
        ])
        .setup(|app| {
            // 在应用启动时自动启动 Runtime
            let window = app.get_window("main").unwrap();
            tauri::async_runtime::spawn(async move {
                // 等待窗口准备好
                std::thread::sleep(std::time::Duration::from_secs(1));

                // 启动 Runtime（使用默认端口 8000）
                // 注意：这里需要通过 invoke 调用，或直接调用函数
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

---

## 第 5 步：前端集成

### 5.1 创建 Runtime API 模块

**文件路径**: `desktop/src/api/runtime.ts`

```typescript
import { invoke } from '@tauri-apps/api/tauri';

export interface RuntimeConfig {
  port: number;
}

export class RuntimeAPI {
  private config: RuntimeConfig;

  constructor(config: RuntimeConfig = { port: 8000 }) {
    this.config = config;
  }

  async start(): Promise<string> {
    try {
      return await invoke<string>('start_runtime', {
        port: this.config.port,
      });
    } catch (error) {
      throw new Error(`Failed to start runtime: ${error}`);
    }
  }

  async stop(): Promise<string> {
    try {
      return await invoke<string>('stop_runtime');
    } catch (error) {
      throw new Error(`Failed to stop runtime: ${error}`);
    }
  }

  async status(): Promise<boolean> {
    try {
      return await invoke<boolean>('runtime_status');
    } catch (error) {
      console.error('Failed to check runtime status:', error);
      return false;
    }
  }

  getApiUrl(): string {
    return `http://127.0.0.1:${this.config.port}`;
  }
}

export const runtime = new RuntimeAPI();
```

### 5.2 React 组件使用

**文件路径**: `desktop/src/App.tsx`

```tsx
import { useEffect, useState } from 'react';
import { runtime } from './api/runtime';

function App() {
  const [runtimeStatus, setRuntimeStatus] = useState<'stopped' | 'starting' | 'running'>('stopped');

  useEffect(() => {
    // 应用启动时启动 Runtime
    const startRuntime = async () => {
      setRuntimeStatus('starting');
      try {
        await runtime.start();
        setRuntimeStatus('running');
        console.log('Runtime started successfully');
      } catch (error) {
        console.error('Failed to start runtime:', error);
        setRuntimeStatus('stopped');
      }
    };

    startRuntime();

    // 清理：应用关闭时停止 Runtime
    return () => {
      runtime.stop().catch(console.error);
    };
  }, []);

  return (
    <div className="App">
      <header>
        <h1>AgentOS Desktop</h1>
        <div className="runtime-status">
          Status: {runtimeStatus}
        </div>
      </header>

      {runtimeStatus === 'running' && (
        <main>
          {/* 你的主要应用内容 */}
          <iframe
            src={runtime.getApiUrl()}
            style={{ width: '100%', height: '600px', border: 'none' }}
          />
        </main>
      )}

      {runtimeStatus === 'starting' && (
        <div>Loading AgentOS Runtime...</div>
      )}

      {runtimeStatus === 'stopped' && (
        <div>Failed to start Runtime. Please restart the application.</div>
      )}
    </div>
  );
}

export default App;
```

---

## 第 6 步：测试集成

### 6.1 开发模式测试

```bash
cd /Users/pangge/PycharmProjects/AgentOS/desktop

# 安装依赖
pnpm install

# 启动开发模式
pnpm run tauri dev
```

**预期行为**:
1. Tauri 窗口打开
2. Runtime 自动启动（控制台显示 "[Runtime]" 日志）
3. 前端显示 "Status: running"
4. 可以访问 http://127.0.0.1:8000

### 6.2 检查 Runtime 日志

在 Rust 控制台中查看：
```
[Runtime] INFO: Starting AgentOS WebUI server
[Runtime] INFO: Server running on http://127.0.0.1:8000
```

### 6.3 手动测试命令

打开浏览器开发者工具，在控制台执行：

```javascript
// 检查状态
await window.__TAURI__.invoke('runtime_status');
// 返回 true

// 停止 Runtime
await window.__TAURI__.invoke('stop_runtime');

// 重新启动
await window.__TAURI__.invoke('start_runtime', { port: 8000 });
```

---

## 第 7 步：构建发布版

### 7.1 构建应用

```bash
cd /Users/pangge/PycharmProjects/AgentOS/desktop

# 构建
pnpm run tauri build
```

### 7.2 检查输出

**macOS**:
```bash
ls -lh src-tauri/target/release/bundle/dmg/
# AgentOS_0.3.0_aarch64.dmg

ls -lh src-tauri/target/release/bundle/macos/
# AgentOS.app
```

**Windows**:
```powershell
dir src-tauri\target\release\bundle\msi\
# AgentOS_0.3.0_x64_en-US.msi
```

### 7.3 验证 Sidecar 包含

```bash
# macOS
ls -lh src-tauri/target/release/bundle/macos/AgentOS.app/Contents/MacOS/
# 应该包含 agentos-runtime-aarch64-apple-darwin

# Windows
dir src-tauri\target\release\bundle\msi\
# 应该包含 agentos-runtime-x86_64-pc-windows-msvc.exe
```

---

## 故障排除

### 问题 1: Sidecar 未找到

**错误信息**: `Failed to create sidecar: sidecar not found`

**解决方案**:
1. 检查文件是否存在：
   ```bash
   ls src-tauri/binaries/
   ```
2. 检查文件名是否符合 Tauri 命名约定
3. 检查 `tauri.conf.json` 中的 `externalBin` 配置

### 问题 2: 权限被拒绝

**错误信息**: `Permission denied when executing sidecar`

**解决方案**:
```bash
chmod +x src-tauri/binaries/agentos-runtime-*
```

### 问题 3: macOS Gatekeeper 阻止

**错误信息**: `"agentos-runtime" cannot be opened because the developer cannot be verified`

**解决方案**:
```bash
# 开发模式
xattr -d com.apple.quarantine src-tauri/binaries/agentos-runtime-*

# 生产模式：配置代码签名
codesign --sign "Developer ID Application: Your Name" \
         --force --deep \
         src-tauri/binaries/agentos-runtime-*
```

### 问题 4: Runtime 启动失败

**检查步骤**:

1. **验证 Runtime 独立运行**:
   ```bash
   ./src-tauri/binaries/agentos-runtime-aarch64-apple-darwin --version
   ```

2. **检查端口占用**:
   ```bash
   lsof -i:8000
   ```

3. **查看完整错误日志**:
   在 Rust `main.rs` 中启用日志：
   ```rust
   env_logger::init();
   ```

4. **测试数据库权限**:
   确保应用可以在用户目录创建数据库文件

### 问题 5: 启动时间过长

**优化方案**:

1. **使用健康检查等待**:
   ```typescript
   const waitForRuntime = async (maxRetries = 30) => {
     for (let i = 0; i < maxRetries; i++) {
       try {
         const response = await fetch(`${runtime.getApiUrl()}/health`);
         if (response.ok) return true;
       } catch (e) {
         // 继续等待
       }
       await new Promise(resolve => setTimeout(resolve, 1000));
     }
     return false;
   };
   ```

2. **显示启动进度**:
   ```tsx
   <div>Starting Runtime... {progress}/30 seconds</div>
   ```

---

## 高级配置

### 自定义数据库路径

```rust
let (mut rx, child) = Command::new_sidecar("agentos-runtime")
    .env("DATABASE_PATH", "/path/to/custom.db")
    .args(&["web", "--port", &port.to_string()])
    .spawn()?;
```

### 动态端口分配

```rust
use std::net::TcpListener;

fn find_available_port() -> u16 {
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    listener.local_addr().unwrap().port()
}

#[tauri::command]
pub async fn start_runtime_auto_port(
    state: State<'_, RuntimeState>,
) -> Result<u16, String> {
    let port = find_available_port();
    // ... 启动 Runtime
    Ok(port)
}
```

### 多实例支持

```rust
pub struct RuntimeState {
    pub instances: Mutex<HashMap<String, CommandChild>>,
}

#[tauri::command]
pub async fn start_runtime_instance(
    name: String,
    port: u16,
    state: State<'_, RuntimeState>,
) -> Result<String, String> {
    // ... 启动并存储实例
}
```

---

## 参考资源

- [Tauri Sidecar 官方文档](https://tauri.app/v1/guides/building/sidecar)
- [Tauri Command 系统](https://tauri.app/v1/guides/features/command)
- [Nuitka 打包指南](../docs/BUILD_GUIDE.md)
- [Phase 2 完成报告](../PHASE2_COMPLETION_REPORT.md)

---

**文档版本**: 1.0
**最后更新**: 2026-01-30
**测试环境**: macOS 14 (ARM64), Tauri 1.x
