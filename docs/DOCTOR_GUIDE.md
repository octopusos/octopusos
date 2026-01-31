# AgentOS Doctor - 环境健康检查和自动修复

## 概述

`agentos doctor` 是 AgentOS 的环境诊断和自动修复工具，旨在让开发者**零决策**地完成环境配置。

### 设计哲学

1. **默认只读**：不加 `--fix` 时只检查，不修改任何系统状态
2. **明确的下一步**：清晰显示问题和修复命令
3. **一键修复**：`--fix` 自动执行所有必要的配置
4. **最小权限**：项目级操作不需要 admin token

## 快速开始

### 1. 检查环境（只读）

```bash
agentos doctor
```

输出示例：

```
项目根目录: /Users/you/AgentOS

AgentOS 环境检查

┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 状态 ┃ 检查项             ┃ 结果                                         ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│  ✅  │ uv                 │ uv 已安装: uv 0.4.0                          │
│  ❌  │ python-3.13        │ Python 3.13 未安装                           │
│      │                    │   • AgentOS 要求 Python 3.13+                │
│      │                    │   • 将使用 uv 自动安装                       │
│  ❌  │ venv               │ .venv 不存在                                 │
│  ❌  │ dependencies       │ 依赖未安装（.venv 不存在）                   │
│  ❌  │ pytest             │ pytest 不可用                                │
│  ✅  │ git                │ git 已安装: git version 2.39.0               │
│  ❌  │ imports            │ 无法测试模块导入                             │
└──────┴────────────────────┴──────────────────────────────────────────────┘

总计: 2 通过, 0 警告, 5 失败

建议修复步骤:

  • python-3.13: uv python install 3.13
  • venv: uv venv --python 3.13
  • dependencies: uv sync --all-extras
  • pytest: uv sync --all-extras
  • imports: uv sync --all-extras

一键自动修复:

  agentos doctor --fix
```

### 2. 自动修复（一键配置）

```bash
agentos doctor --fix
```

执行流程：

1. ✅ 检测到 uv 已安装
2. 🔧 安装 Python 3.13（如果缺失）
3. 🔧 创建 `.venv` 虚拟环境
4. 🔧 安装所有依赖（包括 dev、vector 扩展）
5. ✅ 验证环境配置

输出示例：

```
开始自动修复...

正在安装 Python 3.13...
✅ python-3.13: Python 3.13 安装成功
  路径: /Users/you/.local/share/uv/python/cpython-3.13.0-macos-aarch64-none

正在创建虚拟环境...
✅ venv: 虚拟环境创建成功
  路径: /Users/you/AgentOS/.venv

正在安装依赖...
✅ dependencies: 依赖安装成功
  已安装所有依赖（包括 pytest）

✅ pytest: 依赖安装成功
  已安装所有依赖（包括 pytest）

✅ imports: 核心模块可导入

✨ 所有修复完成！

下一步:
  1. 重新运行检查: agentos doctor
  2. 运行测试: uv run pytest -q
  3. 启动 AgentOS: uv run agentos --help
```

## 检查项详解

### P0 检查（必须通过）

| 检查项 | 说明 | 修复命令 | 需要 Admin |
|--------|------|----------|------------|
| `uv` | uv 包管理器是否安装 | `curl ... \| sh` (自动) | ❌ |
| `python-3.13` | Python 3.13+ 是否可用 | `uv python install 3.13` | ❌ |
| `venv` | `.venv` 虚拟环境是否存在 | `uv venv --python 3.13` | ❌ |
| `dependencies` | 项目依赖是否安装 | `uv sync --all-extras` | ❌ |

### P1 检查（重要）

| 检查项 | 说明 | 修复命令 | 需要 Admin |
|--------|------|----------|------------|
| `pytest` | 测试工具是否可用 | `uv sync --all-extras` | ❌ |
| `git` | Git 版本控制工具 | 手动安装 | ✅ |
| `imports` | 核心模块是否可导入 | `uv sync --all-extras` | ❌ |

## 命令选项

### `--fix`

自动修复所有检测到的问题（跳过需要 admin 权限的项）。

```bash
agentos doctor --fix
```

### `--python <version>`

指定 Python 版本（默认: 3.13）。

```bash
agentos doctor --fix --python 3.13
```

## 高级用法

### 仅检查特定项（未来）

```bash
agentos doctor --check uv,python,venv
```

### CI/CD 集成

```yaml
# .github/workflows/test.yml
- name: Setup environment
  run: |
    # Install uv first
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"

    # Auto-fix environment
    agentos doctor --fix

- name: Run tests
  run: uv run pytest -q
```

### 生成环境报告

```bash
# 生成详细报告（未来）
agentos doctor --report > environment-report.txt
```

## 与现有工具对比

| 工具 | 用途 | 安装依赖 | 配置环境 | 跨平台 |
|------|------|----------|----------|--------|
| `pip` | ✅ | ❌ | ❌ | ✅ |
| `poetry` | ✅ | ⚠️ (需要已有 Python) | ❌ | ✅ |
| `uv` | ✅ | ✅ | ❌ | ✅ |
| **`agentos doctor`** | ✅ | ✅ | ✅ | ✅ |

`agentos doctor` 的优势：
- **端到端自动化**：从安装 uv 到配置完整环境
- **零决策**：自动选择最佳配置（Python 3.13、.venv、all-extras）
- **可审计**：默认只读，显示将执行的命令

## 常见问题

### Q: 为什么需要 uv？

A: uv 是目前最快的 Python 包管理器，能够：
- 管理 Python 版本（无需 pyenv）
- 快速安装依赖（比 pip 快 10-100 倍）
- 跨平台一致性

### Q: 是否会修改系统 Python？

A: **不会**。所有操作都在项目目录或 uv 用户目录（`~/.local/share/uv`），不影响系统 Python。

### Q: --fix 会执行哪些操作？

A: 只读阶段会显示所有将执行的命令。`--fix` 只执行：
1. 安装 uv（如果缺失）
2. 安装 Python 3.13（使用 uv）
3. 创建 `.venv`
4. 安装依赖（`uv sync --all-extras`）

**不会**执行：
- 安装系统级软件（如 git）
- 修改系统配置文件
- 需要 sudo/admin 权限的操作

### Q: 已有 Python 3.14，是否需要降级？

A: 不需要。检查会通过（3.14 > 3.13）。

### Q: 能否在 CI 中使用？

A: 可以。建议先手动安装 uv，然后运行 `agentos doctor --fix`。

### Q: 如何回退？

```bash
# 删除虚拟环境
rm -rf .venv

# 重新配置
agentos doctor --fix
```

## 安全边界

### 无需 Admin Token 的操作

- 安装 uv（用户目录）
- 安装 Python（uv 管理）
- 创建 `.venv`（项目目录）
- 安装依赖（虚拟环境）

### 需要 Admin Token 的操作（会跳过）

- 安装 git（系统级）
- 修改系统 PATH
- 安装系统库

## 故障排除

### 1. uv 安装失败

```bash
# macOS/Linux 手动安装
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows 手动安装
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 使用 Homebrew（macOS）
brew install uv

# 使用 Cargo（已有 Rust）
cargo install uv
```

### 2. 依赖安装慢

```bash
# 使用国内镜像（如果在中国）
export UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
agentos doctor --fix
```

### 3. 权限错误

```bash
# 不要使用 sudo
# doctor 设计为用户级操作

# 如果看到权限错误，检查:
ls -la ~/.local/share/uv
ls -la .venv
```

### 4. 网络问题

```bash
# 检查能否访问 PyPI
curl -I https://pypi.org

# 使用代理
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
agentos doctor --fix
```

## 开发者指南

### 添加新的检查项

1. 在 `agentos/core/doctor/checks.py` 添加检查函数
2. 在 `run_all_checks()` 中注册
3. 添加单元测试

示例：

```python
def check_docker() -> CheckResult:
    """Check if Docker is available"""
    docker_path = shutil.which("docker")

    if docker_path:
        return CheckResult(
            name="docker",
            status=CheckStatus.PASS,
            summary=f"Docker 已安装: {docker_path}"
        )

    return CheckResult(
        name="docker",
        status=CheckStatus.WARN,
        summary="Docker 未安装",
        details=["Docker 是可选的，用于容器隔离执行"],
        needs_admin=True
    )
```

### 添加新的修复函数

1. 在 `agentos/core/doctor/fixes.py` 添加修复函数
2. 在 `apply_all_fixes()` 中注册
3. 添加单元测试

示例：

```python
def fix_docker() -> FixResult:
    """Install Docker"""
    # Docker 需要 admin，跳过自动安装
    return FixResult(
        check_name="docker",
        success=False,
        message="Docker 安装需要管理员权限",
        details=["请访问 https://docker.com 手动安装"]
    )
```

## 路线图

- [ ] 支持 `--check` 选择特定检查项
- [ ] 支持 `--report` 生成 JSON/Markdown 报告
- [ ] 支持 `--dry-run` 显示将执行的命令（不执行）
- [ ] 添加 Docker 检查
- [ ] 添加磁盘空间检查
- [ ] 添加网络连接检查（PyPI、GitHub）
- [ ] 支持配置文件（`.agentos/doctor.toml`）

## 参考

- [uv 官方文档](https://docs.astral.sh/uv/)
- [Python 3.13 发布说明](https://docs.python.org/3.13/whatsnew/3.13.html)
- [AgentOS 架构文档](./ARCHITECTURE.md)
