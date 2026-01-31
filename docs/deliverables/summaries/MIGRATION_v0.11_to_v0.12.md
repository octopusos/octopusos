# AgentOS v0.12 升级指南

## 从 v0.11 升级到 v0.12

### 重大变更

#### 1. AnswerPack 人机协作升级

**新功能**:
- Textual TUI 全屏界面 (`--ui tui`)
- LLM 辅助建议 (`--llm`)
- 多轮问答支持（最大深度3层）

**向后兼容**:
- CLI 模式仍然默认启用
- 旧的 `agentos answers create` 命令继续工作

**迁移步骤**:
```bash
# 安装新依赖
uv sync

# 旧方式（仍然工作）
agentos answers create --from question_pack.json --out answer_pack.json

# 新方式（TUI + LLM）
agentos answers create --from question_pack.json --out answer_pack.json --ui tui --llm
```

#### 2. Executor 并行执行

**重大变更**:
- 新增 `AsyncExecutorEngine` 支持并行执行
- 旧的 `ExecutorEngine` 仍然存在（线性执行）
- DAG 调度器自动处理依赖

**向后兼容**:
- 默认使用旧引擎，保持线性执行
- 通过 `use_dag=True` 启用并行

**迁移步骤**:
```python
# 旧方式（仍然工作）
from agentos.core.executor import ExecutorEngine
engine = ExecutorEngine(repo_path, output_dir)
result = engine.execute(execution_request, sandbox_policy)

# 新方式（并行执行）
from agentos.core.executor.async_engine import AsyncExecutorEngine, execute_async
engine = AsyncExecutorEngine(repo_path, output_dir)
result = execute_async(engine, execution_request, sandbox_policy, use_dag=True)
```

#### 3. 容器沙箱支持

**新功能**:
- 自动检测 Docker/Podman
- 高风险操作需要容器
- 自动降级到 worktree

**Allowlist 扩展**:
```python
# 新增操作类型
- npm_install (MEDIUM risk)
- pip_install (MEDIUM risk)
- set_env (MEDIUM risk)
- unset_env (MEDIUM risk)
```

**风险等级**:
- SAFE: 只读操作
- LOW: 文件修改
- MEDIUM: 包安装、环境变量（需要容器）
- HIGH: 系统级变更（需要容器）

#### 4. Tool Adapter 生态

**新功能**:
- Codex Adapter
- Adapter Registry (工厂模式)
- 重试策略（3次 + 指数退避）
- 成本优化器

**使用方式**:
```python
# 旧方式（硬编码）
if tool_type == "claude_cli":
    adapter = ClaudeCliAdapter()
elif tool_type == "opencode":
    adapter = OpenCodeAdapter()

# 新方式（注册表）
from agentos.ext.tools.adapter_registry import get_adapter
adapter = get_adapter(tool_type)

# 带重试
from agentos.ext.tools.retry_policy import RetryableAdapter
adapter = get_adapter(tool_type, retry_config=RetryConfig(max_retries=3))

# 成本优化
from agentos.ext.tools.cost_optimizer import CostOptimizer
optimizer = CostOptimizer(budget_usd=10.0)
tool_type = optimizer.select_tool(task_size=150, urgency="normal")
```

### Schema 版本变更

| Schema | v0.11 | v0.12 | Breaking? |
|--------|-------|-------|-----------|
| AnswerPack | 0.11.0 | 0.12.0 | No |
| ExecutionResult | 0.11.1 | 0.12.0 | No |
| ToolResultPack | 0.11.x | 0.12.0 | No |

**新增字段**:
- AnswerPack: `llm_suggestions`, `multi_round`
- ExecutionResult: `dag_graph`, `execution_mode`
- ToolResultPack: `retry_count`, `retry_metadata`

所有新字段为可选，保持向后兼容。

### 依赖更新

**新增依赖**:
```toml
[project.dependencies]
textual = ">=0.47.0"        # TUI 支持
anthropic = ">=0.18.0"      # Claude API
docker = ">=6.1.0"          # 容器支持
```

**安装**:
```bash
uv sync
```

### 配置迁移

#### 环境变量

**新增**:
```bash
# LLM 支持
export ANTHROPIC_API_KEY=sk-ant-...  # Claude API key

# 容器支持（可选）
export AGENTOS_PREFER_ENGINE=docker  # 或 podman
```

#### CLI 参数

**新增选项**:
```bash
# AnswerPack
--ui [cli|tui]                 # UI 模式
--llm / --no-llm               # LLM 建议
--llm-provider [openai|anthropic]

# Executor（通过代码配置）
use_dag=True                   # 启用 DAG 并行
max_concurrency=5              # 最大并发数
```

### 功能对比

| 功能 | v0.11 | v0.12 |
|------|-------|-------|
| AnswerPack CLI | ✅ | ✅ |
| AnswerPack TUI | ❌ | ✅ |
| LLM 建议 | ❌ | ✅ |
| 多轮问答 | ❌ | ✅ |
| 线性执行 | ✅ | ✅ |
| 并行执行 | ❌ | ✅ |
| Worktree 沙箱 | ✅ | ✅ |
| 容器沙箱 | ❌ | ✅ |
| Claude CLI | ✅ | ✅ |
| OpenCode | ✅ | ✅ |
| Codex | ❌ | ✅ |
| 重试机制 | ❌ | ✅ |
| 成本优化 | ❌ | ✅ |

### 故障排除

#### TUI 不启动
```bash
# 检查 textual 安装
python -c "import textual; print(textual.__version__)"

# 降级到 CLI
agentos answers create --ui cli ...
```

#### LLM 建议失败
```bash
# 检查 API keys
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# 禁用 LLM
agentos answers create --no-llm ...
```

#### 容器不可用
```bash
# 检查 Docker/Podman
docker --version
podman --version

# 系统会自动降级到 worktree
```

#### 并行执行失败
```python
# 禁用 DAG，使用线性执行
result = execute_async(engine, ..., use_dag=False)
```

### 性能优化

**v0.12 性能提升**:
- 并行执行：3-5x 提速（无依赖操作）
- TUI 响应：即时反馈（vs CLI 逐题等待）
- 容器缓存：第二次执行快 2x

### 已知限制

1. **多轮问答深度限制为 3 层** (RED LINE)
2. **容器需要 Docker/Podman**（自动降级）
3. **成本优化基于预估值**（实际成本可能不同）
4. **并行执行最大 5 并发**（可配置）

### 回滚指南

如果 v0.12 有问题，可以回滚：

```bash
# 回滚代码
git checkout <v0.11_commit_hash>

# 回滚依赖
uv sync

# 清理 v0.12 产物
rm -rf outputs/v12_*
```

### 下一步

1. 运行 Phase 1-3 Gates 验证
2. 运行集成测试
3. 更新 CI/CD 配置
4. 更新文档链接

### 支持

遇到问题请查看:
- Gates 脚本：`scripts/gates/run_v12_phase*_gates.sh`
- 测试：`tests/test_phase*.py`
- 文档：`docs/guides/` 和 `docs/architecture/`

---

**版本**: v0.12.0
**发布日期**: 2026-01-25
**兼容性**: v0.11.x 向后兼容
