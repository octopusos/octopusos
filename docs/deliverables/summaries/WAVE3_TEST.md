# Wave 3 测试说明

## 测试 OpenAI Agent 生成

Wave 3 实现了 OpenAI Structured Outputs 集成，可以从 FactPack 生成严格符合 schema 的 AgentSpec。

### 前置条件

需要设置 OpenAI API Key：

```bash
export OPENAI_API_KEY=sk-...
```

### 测试命令

```bash
# 1. 确保已有 FactPack
uv run agentos scan vite-example

# 2. 生成 Agent
uv run agentos generate agent frontend-engineer --project vite-example

# 3. 验证生成的 AgentSpec
uv run agentos verify artifacts/vite-example/spec/frontend-engineer.json
```

### 预期输出

生成的 AgentSpec 应包含：

- ✅ name: "frontend-engineer"
- ✅ role: 描述性角色
- ✅ mission: 清晰的使命陈述
- ✅ allowed_paths: 来自项目的真实路径
- ✅ forbidden_paths: 敏感路径（.env, .git/ 等）
- ✅ workflows: 至少 1 个工作流（含 steps + verification）
- ✅ commands: 来自 FactPack.commands（不编造）
- ✅ verification.schema_check: true
- ✅ verification.command_existence_check: true
- ✅ provenance: 引用 FactPack 中的 evidence IDs
- ✅ metadata: 包含 project_id, agent_type, generated_at

### 验证规则

生成器会自动检查：

1. **Schema 校验**: 生成的 JSON 必须完全符合 agent_spec.schema.json
2. **命令存在性**: 所有命令必须在 FactPack 中存在（禁止编造）
3. **Evidence 可追溯**: provenance 字段引用的 evidence IDs 必须真实

### 示例预期文件

参考 `tests/fixtures/valid_agent_spec.json` 了解完整结构。
