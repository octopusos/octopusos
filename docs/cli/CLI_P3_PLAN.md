# P3 规划：可用性与可审计性增强

## P3 定位

**不扩功能，只增强可用性/可审计性**

P0-P2 已完成 CLI Task Control Plane 的核心功能闭环：
- ✅ P0: 基础设施（RunMode, PauseGate, Runner, CLI 主循环）
- ✅ P1: 真实 pipeline 集成
- ✅ P2: Approve/Continue 真实闭环

P3 目标：让系统"好用"和"可信赖"，而不是"能用"。

---

## P3 核心任务（2 项）

### P3-A: `agentos task trace --expand open_plan`

**目标**: 让 `trace` 命令能直接展示 open_plan proposal 摘要

#### 当前状态（P2）

```bash
$ agentos task trace <task_id>

Timeline:
  [runner_spawn] runner_xxx_123456 @ 2026-01-26T12:00:00
  [pipeline] stage_0_experimental_open_plan @ 2026-01-26T12:00:05
  [artifact] artifacts/<task_id>/open_plan.json @ 2026-01-26T12:00:06  # ← lineage 有指针
  [pause_checkpoint] open_plan @ 2026-01-26T12:00:07
  ...
```

**问题**: 用户看到 artifact 指针，但不知道 proposal 内容是什么。

#### P3-A 目标

```bash
$ agentos task trace <task_id> --expand open_plan

Timeline:
  ...
  [artifact] artifacts/<task_id>/open_plan.json @ 2026-01-26T12:00:06
  
  📄 Open Plan Proposal:
    Task ID: xxx
    Generated: 2026-01-26T12:00:06
    Pipeline Status: success
    Stages: 3 stages
      1. stage_intent: success
      2. stage_planning: success
      3. stage_open_plan: success
    
    Actions: 5 total
      - create_file: 2
      - modify_file: 2
      - run_command: 1
  
  [pause_checkpoint] open_plan @ 2026-01-26T12:00:07
  ...
```

#### 实施细节

**修改文件**: `agentos/cli/task.py` 的 `trace_task()` 函数

**实现步骤**:

1. **添加 `--expand` 选项**

```python
@task_group.command("trace")
@click.argument("task_id")
@click.option("--expand", type=click.Choice(["open_plan", "all"]), help="Expand specific artifacts")
def trace_task(task_id: str, expand: Optional[str]):
    """Show task execution trace"""
    # ... existing code ...
    
    # New: Expand artifacts if requested
    if expand:
        for entry in trace.timeline:
            if entry.kind == "artifact" and should_expand(entry, expand):
                display_artifact_content(entry)
```

2. **实现 `display_artifact_content()`**

```python
def display_artifact_content(entry: TaskLineageEntry):
    """Display artifact content inline"""
    from pathlib import Path
    import json
    
    artifact_path = Path("store") / entry.ref_id
    if not artifact_path.exists():
        console.print(f"[yellow]  ⚠️  Artifact not found: {artifact_path}[/yellow]")
        return
    
    with open(artifact_path, 'r') as f:
        data = json.load(f)
    
    # Display summary
    console.print(f"\n  📄 [bold cyan]Open Plan Proposal:[/bold cyan]")
    console.print(f"    Task ID: {data.get('task_id')}")
    console.print(f"    Generated: {data.get('generated_at')}")
    console.print(f"    Pipeline Status: {data.get('pipeline_status')}")
    
    stages = data.get('stages', [])
    console.print(f"    Stages: {len(stages)} stages")
    
    for i, stage in enumerate(stages[:3], 1):  # Show first 3
        console.print(f"      {i}. {stage.get('stage')}: {stage.get('status')}")
    
    if len(stages) > 3:
        console.print(f"      ... +{len(stages) - 3} more")
    
    # Future: Extract actions from stages
    # actions = extract_actions(stages)
    # console.print(f"    Actions: {len(actions)} total")
```

3. **辅助函数**

```python
def should_expand(entry: TaskLineageEntry, expand: str) -> bool:
    """Check if entry should be expanded"""
    if expand == "all":
        return entry.kind == "artifact"
    
    if expand == "open_plan":
        return (entry.kind == "artifact" and 
                entry.metadata and 
                entry.metadata.get("artifact_kind") == "open_plan")
    
    return False
```

#### 验收标准

**测试**:
```python
def test_p3_a_trace_expand_open_plan():
    # 1. Create task with open_plan artifact
    # 2. Run: agentos task trace <task_id> --expand open_plan
    # 3. Assert output contains "Open Plan Proposal" section
    # 4. Assert output contains task_id, pipeline_status, stages count
```

**手动验证**:
```bash
# 1. 创建并运行 task 到 awaiting_approval
$ agentos task create "test task"
# ... wait for pause ...

# 2. 查看 trace（无 expand）
$ agentos task trace <task_id>
# 应该看到 [artifact] ... 但无详情

# 3. 查看 trace（有 expand）
$ agentos task trace <task_id> --expand open_plan
# 应该看到 "📄 Open Plan Proposal" 和摘要
```

#### 工作量估算

- **实现**: 2-3 小时
- **测试**: 1 小时
- **文档**: 30 分钟
- **总计**: 约 4 小时

---

### P3-B: 完善依赖安装与运行体验

**目标**: 让 CLI "开箱即用"，新用户不需要猜测如何初始化

#### 当前问题（P2）

用户克隆 repo 后：
```bash
$ git clone ...
$ cd AgentOS
$ agentos --help
zsh: command not found: agentos  # ← 依赖未安装

$ python -m agentos.cli.main --help
ModuleNotFoundError: No module named 'click'  # ← 同样问题
```

**原因**: 虽然 `pyproject.toml` 声明了依赖，但用户需要知道：
1. 安装依赖: `pip install -e .`
2. 初始化 DB: `python -m agentos.store.migrations migrate`
3. 运行 CLI: `agentos` 或 `python -m agentos.cli.main`

这些步骤没有文档化，新用户会卡住。

#### P3-B 目标

**统一入口**: 使用 `uv run` 提供一键运行体验

```bash
$ git clone ...
$ cd AgentOS

# 自动安装依赖 + 运行
$ uv run agentos --help
Usage: agentos [OPTIONS] COMMAND [ARGS]...
  ...
```

**初始化文档**: 明确初始化流程

#### 实施细节

**任务 1: 添加 `uv` 支持（如果尚未支持）**

检查 `pyproject.toml` 是否兼容 `uv`：
```toml
[project]
name = "agentos"
version = "0.3.0"
dependencies = [
    "click>=8.1.7",
    ...
]

[project.scripts]
agentos = "agentos.cli.main:cli"  # ✅ 已有
```

**验证**: `uv run agentos --help` 应该自动安装依赖并运行

**任务 2: 创建 `QUICKSTART.md` 文档**

```markdown
# AgentOS CLI 快速开始

## 前置要求

- Python 3.13+
- `uv` (推荐) 或 `pip`

## 方式 1: 使用 uv（推荐）

```bash
# 克隆 repo
git clone https://github.com/your-org/AgentOS.git
cd AgentOS

# 自动安装依赖并运行（uv 会处理一切）
uv run agentos --help

# 初始化数据库（首次运行）
uv run python -m agentos.store.migrations migrate

# 启动交互式 CLI
uv run agentos
```

## 方式 2: 使用 pip

```bash
# 克隆 repo
git clone https://github.com/your-org/AgentOS.git
cd AgentOS

# 安装依赖
pip install -e .

# 初始化数据库
python -m agentos.store.migrations migrate

# 启动 CLI
agentos
# 或
python -m agentos.cli.main
```

## 验证安装

```bash
# 检查版本
uv run agentos --version

# 查看帮助
uv run agentos --help

# 列出任务
uv run agentos task list
```

## 下一步

- 阅读 `docs/cli/CLI_TASK_CONTROL_PLANE.md` 了解核心概念
- 运行 `uv run agentos` 进入交互式主循环
- 创建第一个任务: New task → 输入需求 → 等待执行
```

**任务 3: 更新 `README.md`**

在项目根目录 `README.md` 中添加：

```markdown
# AgentOS

...

## 快速开始

```bash
# 使用 uv（推荐）
uv run agentos --help

# 或使用 pip
pip install -e .
agentos --help
```

详细文档: [QUICKSTART.md](./QUICKSTART.md)
```

**任务 4: 添加 DB 自动初始化（可选）**

修改 `cli/main.py`，在首次运行时自动检查并初始化 DB：

```python
def ensure_db_initialized():
    """Ensure database is initialized before running CLI"""
    from agentos.store import get_db_path
    from pathlib import Path
    
    db_path = get_db_path()
    
    if not db_path.exists():
        console.print("[yellow]Database not found, initializing...[/yellow]")
        
        from agentos.store.migrations import migrate
        migrate()
        
        console.print("[green]✅ Database initialized[/green]")

@click.group()
def cli():
    """AgentOS CLI"""
    ensure_db_initialized()  # ← Auto-init
    pass
```

**注意**: 这是可选的，因为可能会在非预期时机创建 DB。建议先做文档化，P3 后期再考虑自动化。

#### 验收标准

**测试**:
```bash
# 1. 删除 store/registry.sqlite
$ rm -f store/registry.sqlite

# 2. 克隆 repo 到临时目录（模拟新用户）
$ git clone ... /tmp/agentos-test
$ cd /tmp/agentos-test

# 3. 运行 uv（无需预先安装依赖）
$ uv run agentos --help
# 应该输出帮助信息，不报错

# 4. 初始化 DB
$ uv run python -m agentos.store.migrations migrate
# 应该成功

# 5. 运行交互 CLI
$ uv run agentos
# 应该进入主菜单
```

**文档检查**:
- `QUICKSTART.md` 存在且完整
- `README.md` 包含快速开始链接
- 步骤可复现

#### 工作量估算

- **uv 集成验证**: 30 分钟
- **文档编写**: 1 小时
- **测试**: 1 小时
- **总计**: 约 2.5 小时

---

## P3 TechDebt 任务

### P3-DEBT-1: Lineage 写入失败处理

**优先级**: P1（影响审计完整性）

**实施**:
1. 添加 `AGENTOS_DEBUG` 环境变量支持
2. Debug 模式下 lineage 写入失败 raise
3. 生产模式下写入 `lineage_write_failed` audit
4. E2E 测试模拟 lineage 失败场景

**工作量**: 2-3 小时

**详见**: `CLI_ARCHITECTURE_CONTRACTS.md` - 铁律 2

---

## P3 时间线估算

| 任务 | 工作量 | 依赖 | 里程碑 |
|------|--------|------|--------|
| P3-A: trace --expand | 4h | 无 | M1: 可审计性增强 |
| P3-B: 运行体验 | 2.5h | 无 | M2: 开箱即用 |
| P3-DEBT-1: lineage 失败处理 | 3h | 无 | M3: TechDebt 清理 |
| **总计** | **9.5h** | - | **约 1-2 天** |

---

## P3 验收标准（守门员）

### 验收清单

- [ ] P3-A: `agentos task trace <id> --expand open_plan` 可显示 proposal 摘要
- [ ] P3-B: `uv run agentos --help` 开箱即用（无需预装依赖）
- [ ] `QUICKSTART.md` 文档存在且步骤可复现
- [ ] P3-DEBT-1: Debug 模式下 lineage 失败会 raise
- [ ] 所有 P0-P2 RED LINEs 仍然强制执行
- [ ] E2E 测试全部通过

### 不扩功能原则

**允许**:
- ✅ 增强现有命令的输出（如 `--expand`）
- ✅ 改进错误处理（如 lineage 失败）
- ✅ 优化安装/运行体验（如 `uv run`）

**禁止**:
- ❌ 新增 CLI 命令（如 `agentos task modify`）
- ❌ 新增运行模式（如 `semi_autonomous`）
- ❌ 修改核心状态机（如增加新 checkpoint）

---

## P3 完成后状态

- **P0**: ✅ 基础设施
- **P1**: ✅ 真实 pipeline
- **P2**: ✅ Approve/Continue 闭环
- **P3**: ✅ **可用性与可审计性增强**

**下一步**: 
- P4: 用户反馈驱动的 UX 优化
- 或: 冻结 CLI，投入生产验证

---

## 参考文档

- `CLI_ARCHITECTURE_CONTRACTS.md` - 架构铁律
- `CLI_P0_CLOSEOUT.md` - P0 实施总结
- `CLI_P1_COMPLETION.md` - P1 实施总结
- `CLI_P2_CLOSEOUT.md` - P2 实施总结

---

**创建日期**: 2026-01-26  
**状态**: 🟡 待实施  
**预计完成**: 1-2 天（约 9.5 小时）
