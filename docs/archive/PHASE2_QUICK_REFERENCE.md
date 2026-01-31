# Phase 2 快速参考卡

## 构建 Runtime

```bash
# 1. 安装依赖
source .venv/bin/activate
pip install nuitka ordered-set zstandard

# 2. 构建
python3 scripts/build_runtime.py

# 3. 检查输出
ls -lh dist/agentos-runtime-*
```

**输出**: `dist/agentos-runtime-macos-arm64` (41 MB)

---

## 测试 Runtime

```bash
# 移除 Gatekeeper 限制（仅首次）
xattr -d com.apple.quarantine dist/agentos-runtime-*

# 运行测试
./scripts/test_runtime.sh
```

---

## 集成到 Tauri

```bash
# 1. 复制到 Tauri
mkdir -p desktop/src-tauri/binaries
cp dist/agentos-runtime-macos-arm64 \
   desktop/src-tauri/binaries/agentos-runtime-aarch64-apple-darwin

# 2. 配置 tauri.conf.json
{
  "tauri": {
    "bundle": {
      "externalBin": ["binaries/agentos-runtime"]
    }
  }
}

# 3. 测试
cd desktop
pnpm run tauri dev
```

---

## 文件路径速查

| 文件 | 路径 |
|------|------|
| 打包脚本 | `/Users/pangge/PycharmProjects/AgentOS/scripts/build_runtime.py` |
| 测试脚本 | `/Users/pangge/PycharmProjects/AgentOS/scripts/test_runtime.sh` |
| 输出文件 | `/Users/pangge/PycharmProjects/AgentOS/dist/agentos-runtime-*` |
| CI 配置 | `/Users/pangge/PycharmProjects/AgentOS/.github/workflows/build-runtime.yml` |
| 完成报告 | `/Users/pangge/PycharmProjects/AgentOS/PHASE2_COMPLETION_REPORT.md` |
| 构建指南 | `/Users/pangge/PycharmProjects/AgentOS/docs/BUILD_GUIDE.md` |
| Tauri 集成 | `/Users/pangge/PycharmProjects/AgentOS/docs/TAURI_INTEGRATION.md` |

---

## 平台命名对照表

| 平台 | 构建输出 | Tauri Sidecar 名称 |
|------|----------|-------------------|
| macOS ARM64 | `agentos-runtime-macos-arm64` | `agentos-runtime-aarch64-apple-darwin` |
| macOS Intel | `agentos-runtime-macos-x64` | `agentos-runtime-x86_64-apple-darwin` |
| Windows x64 | `agentos-runtime-windows-x64.exe` | `agentos-runtime-x86_64-pc-windows-msvc.exe` |

---

## 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| 文件大小 | < 50 MB | ✅ 41.34 MB |
| 压缩率 | - | ✅ 21.48% |
| 启动时间 | < 3 秒 | ⏸️ 待测试 |
| 构建时间 | - | ~21 分钟（首次） |

---

## 常见问题

### macOS: "cannot be opened"
```bash
xattr -d com.apple.quarantine dist/agentos-runtime-*
```

### Windows: "Windows protected"
点击 "More info" > "Run anyway"

### 构建失败: "cannot find -lpython"
```bash
brew reinstall python@3.13
```

---

## 下一步

1. **手动测试**: 移除 Gatekeeper 限制后运行测试脚本
2. **CI/CD**: Push 到 GitHub 触发多平台构建
3. **Tauri 集成**: 复制 Runtime 到 desktop 项目
4. **端到端测试**: 在 Tauri 中验证 Runtime 正常工作

---

**完整文档**: [PHASE2_COMPLETION_REPORT.md](PHASE2_COMPLETION_REPORT.md)
