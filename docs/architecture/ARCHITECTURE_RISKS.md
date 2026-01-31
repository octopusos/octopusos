# AgentOS 架构风险管理与演进策略

## 文档目的

本文档记录 AgentOS 在 0.1.0 完成后识别的 5 个关键架构风险点及应对策略。这些不是当前缺陷，而是**必然会遇到的演进挑战**。

---

## ⚠️ 风险 1: Schema 演进策略

### 问题描述

当前 Schema 没有版本机制，未来会遇到：
- AgentSpec v0.2 / v0.3 需要新字段
- 旧 artifacts 无法识别
- Renderer/Verifier 不知道如何处理

### 何时会炸

- 第一次需要 breaking change（如重命名字段、改变必填规则）
- 尝试渲染 6 个月前生成的 agent.md

### 应对策略

#### 1. Schema 版本化（立即执行）

在所有 schema 中添加 `$version` 字段：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$version": "1.0.0",
  "title": "FactPack",
  ...
}
```

在数据中添加 `schema_version`：

```json
{
  "schema_version": "1.0.0",
  "project_id": "...",
  ...
}
```

#### 2. 版本兼容策略

**Semver 规则**:
- `major.minor.patch`
- `major` 变化 = breaking change（拒绝处理或升级）
- `minor` 变化 = 新增可选字段（向后兼容）
- `patch` 变化 = 文档修正（无影响）

**Verifier 行为**:
```python
def validate_with_version(data: dict, schema_name: str):
    data_version = parse_version(data.get("schema_version", "0.0.0"))
    schema_version = parse_version(CURRENT_SCHEMA_VERSION)
    
    if data_version.major != schema_version.major:
        raise IncompatibleSchemaError(
            f"Major version mismatch: {data_version} vs {schema_version}"
        )
    
    # Minor/patch differences are OK
    return validate(data, schema)
```

**Renderer 行为**:
```python
SUPPORTED_VERSIONS = ["1.0.0", "1.1.0"]

def render(agent_spec: dict):
    version = agent_spec.get("schema_version")
    if version not in SUPPORTED_VERSIONS:
        raise UnsupportedVersionError(f"Cannot render version {version}")
    
    # Use version-specific template if needed
    template = get_template(version)
    return template.render(**agent_spec)
```

#### 3. 升级工具（未来）

```bash
# 自动升级旧 artifacts
uv run agentos migrate upgrade artifacts/my-project/spec/*.json --to 1.1.0
```

---

## ⚠️ 风险 2: Adapter 爆炸

### 问题描述

当前 2 个 Adapter（Vite+React, .NET）很优雅，但未来会：
- 10+ adapters（Next.js, Nuxt, Django, FastAPI, Terraform...）
- Adapter 之间功能重叠（都是 frontend 但细节不同）
- Orchestrator 不知道选哪个

### 何时会炸

- 第 5-6 个 Adapter 时开始混乱
- Monorepo 项目同时匹配多个 Adapter
- 需要 "frontend but not React" 这种组合查询

### 应对策略

#### 1. Capability Matrix（立即设计）

每个 Adapter 必须声明 capabilities：

```python
class ViteReactAdapter(BaseAdapter):
    @property
    def capabilities(self) -> dict[str, Any]:
        return {
            "project_type": ["frontend"],
            "framework": ["vite"],
            "language": ["typescript", "javascript"],
            "build_system": ["vite"],
            "package_manager": ["npm", "yarn", "pnpm"],
            "features": ["hot_reload", "tree_shaking", "jsx"],
            "confidence": 0.95  # 识别置信度
        }
```

#### 2. Adapter 选择策略

**Orchestrator 使用 capability 而非名称**:

```python
# ❌ 不要这样
if adapter.name == "vite-react":
    ...

# ✅ 应该这样
if "frontend" in adapter.capabilities["project_type"]:
    if "typescript" in adapter.capabilities["language"]:
        ...
```

**多 Adapter 匹配时按置信度排序**:

```python
matched_adapters = [
    adapter for adapter in ADAPTERS
    if adapter.detect(repo_root)
]

# 按置信度排序
matched_adapters.sort(
    key=lambda a: a.capabilities.get("confidence", 0.5),
    reverse=True
)

# 使用最高置信度的 Adapter
best_adapter = matched_adapters[0]
```

#### 3. Adapter Registry（未来）

```python
# 集中式注册
ADAPTER_REGISTRY = {
    "frontend": {
        "vite-react": ViteReactAdapter,
        "next": NextAdapter,
        "nuxt": NuxtAdapter,
    },
    "backend": {
        "dotnet": DotnetAdapter,
        "fastapi": FastAPIAdapter,
    }
}

# 按需加载
def get_adapter(project_type: str, framework: str):
    return ADAPTER_REGISTRY[project_type][framework]()
```

---

## ⚠️ 风险 3: Orchestrator 并发与锁

### 问题描述

当前 SQLite lease 机制是对的，但细节未完善：
- 多实例同时跑（CI + cron）
- Lease 过期后如何接管
- 失败重试策略

### 何时会炸

- 同一项目在 CI 和 cron 中同时触发
- Worker 崩溃导致 lease 永久占用
- 高并发场景（10+ workers）

### 应对策略

#### 1. Lease 细化（立即完善）

**当前实现**（已有基础）:
```sql
-- runs 表中已有 lease_until 字段
SELECT id, project_id FROM runs
WHERE status = 'QUEUED'
  AND (lease_until IS NULL OR lease_until < NOW())
```

**需要添加**:

```sql
-- 添加 lease_holder 字段
ALTER TABLE runs ADD COLUMN lease_holder TEXT;

-- 添加 retry_count 字段
ALTER TABLE runs ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE runs ADD COLUMN max_retries INTEGER DEFAULT 3;
```

**Lease 获取逻辑**:

```python
def acquire_lease(run_id: int, worker_id: str, lease_duration: int = 300):
    """
    获取任务 lease
    
    Args:
        run_id: 任务 ID
        worker_id: 当前 worker ID（如 hostname:pid）
        lease_duration: Lease 持续时间（秒）
    
    Returns:
        True if acquired, False if already leased
    """
    now = datetime.now(timezone.utc)
    lease_until = now + timedelta(seconds=lease_duration)
    
    cursor.execute("""
        UPDATE runs
        SET lease_holder = ?,
            lease_until = ?,
            status = 'RUNNING'
        WHERE id = ?
          AND (lease_until IS NULL OR lease_until < ?)
    """, (worker_id, lease_until, run_id, now))
    
    return cursor.rowcount > 0
```

#### 2. 重试策略

```python
def should_retry(run: dict) -> bool:
    return run["retry_count"] < run["max_retries"]

def handle_failure(run_id: int, error: str):
    run = get_run(run_id)
    
    if should_retry(run):
        # 重新入队
        cursor.execute("""
            UPDATE runs
            SET status = 'QUEUED',
                retry_count = retry_count + 1,
                lease_holder = NULL,
                lease_until = NULL,
                error = ?
            WHERE id = ?
        """, (error, run_id))
    else:
        # 最终失败
        cursor.execute("""
            UPDATE runs
            SET status = 'FAILED',
                error = ?
            WHERE id = ?
        """, (error, run_id))
```

#### 3. Worker 健康检查（未来）

```python
# Worker 定期更新心跳
def heartbeat(worker_id: str):
    cursor.execute("""
        UPDATE runs
        SET lease_until = datetime('now', '+300 seconds')
        WHERE lease_holder = ?
          AND status = 'RUNNING'
    """, (worker_id,))
```

---

## ⚠️ 风险 4: OpenAI 依赖

### 问题描述

当前设计已经很好：
- 无 OpenAI → scan/verify/orchestrate 仍可用
- 只有 generate 需要 OpenAI

但需要防止：
- OpenAI API 变更
- 成本爆炸
- 需要本地模型替代

### 何时会炸

- OpenAI 价格上涨 10x
- 合规要求禁止外部 API
- 需要离线部署

### 应对策略（当前设计已足够好）

#### 1. LLM 抽象层（未来可选）

```python
class LLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        pass

class OpenAIProvider(LLMProvider):
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        # 当前实现
        pass

class OllamaProvider(LLMProvider):
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        # 本地模型（如 Llama 3）
        pass

# 配置选择
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
provider = get_provider(LLM_PROVIDER)
```

#### 2. 成本控制

```python
# 在生成前估算 token 成本
def estimate_cost(factpack: dict) -> float:
    input_tokens = estimate_tokens(json.dumps(factpack))
    output_tokens = 2000  # 预估
    
    cost = (input_tokens / 1000) * 0.01 + (output_tokens / 1000) * 0.03
    
    if cost > MAX_COST_PER_GENERATION:
        raise CostLimitExceeded(f"Estimated cost ${cost:.2f} exceeds limit")
    
    return cost
```

#### 3. 缓存策略

```python
# FactPack hash 相同 → 复用 AgentSpec
def get_or_generate(factpack: dict, agent_type: str) -> dict:
    factpack_hash = compute_hash(factpack)
    
    cached = get_from_cache(factpack_hash, agent_type)
    if cached:
        return cached
    
    agent_spec = builder.generate(factpack, agent_type)
    save_to_cache(factpack_hash, agent_type, agent_spec)
    return agent_spec
```

---

## ⚠️ 风险 5: 产品化思维

### 问题描述

AgentOS 已经不是 side tool，而是**可以成为工程体系中枢**。

### 战略意义

**当前能力**:
- 扫描任意项目 → 理解技术栈
- 生成 Agent 规范 → 定义角色和职责
- 编排执行 → 自动化工作流

**未来潜力**:
- SkyLink 多 Agent 协同（每个 Portal 一个 Agent）
- OPS 自动化（发布、监控、回滚）
- CI/CD 增强（智能决策）
- 知识图谱（项目依赖、技术债务）

### 产品化路径

#### Phase 1: 稳定核心（当前）
- ✅ 基础功能完整
- ✅ 架构清晰可扩展
- ⏳ 生产环境验证

#### Phase 2: 增强能力（1-3 月）
- Agent 真正执行（不只是生成规范）
- Web UI（可视化管理）
- 多 LLM 支持
- 更多 Adapters

#### Phase 3: 生态系统（3-6 月）
- Agent 市场（预定义模板）
- Plugin 系统
- 企业功能（RBAC、审计）
- SaaS 版本

#### Phase 4: 平台化（6-12 月）
- 成为其他系统的基座
- API 网关
- 分布式部署
- 持续学习

---

## 实施优先级

### 立即执行（本周）

1. ✅ **创建本文档**（风险意识）
2. 🔄 **Schema 版本化**（添加 version 字段）
3. 🔄 **Adapter Capability Matrix**（定义接口）

### 近期执行（1 月内）

4. **Lease 细化**（添加 retry_count, lease_holder）
5. **成本监控**（添加 token 估算）
6. **第一次生产验证**（在真实项目中使用）

### 中期规划（3 月内）

7. **LLM 抽象层**（支持本地模型）
8. **Adapter Registry**（集中式管理）
9. **Schema 升级工具**（migrate 命令）

### 长期愿景（6-12 月）

10. **Web UI**
11. **Agent 执行引擎**
12. **平台化基础设施**

---

## 决策记录

### ADR-001: Schema 必须版本化

**日期**: 2026-01-25  
**状态**: 已批准  
**决策**: 所有 JSON Schema 和数据必须包含 version 字段  
**影响**: 需要更新所有 schemas 和 validators

### ADR-002: Adapter 使用 Capability 而非名称

**日期**: 2026-01-25  
**状态**: 已批准  
**决策**: Orchestrator 通过 capabilities 选择 Adapter  
**影响**: 需要为所有 Adapter 添加 capabilities 属性

### ADR-003: OpenAI 是可选依赖

**日期**: 2026-01-25  
**状态**: 已批准  
**决策**: 系统核心功能不依赖 OpenAI，只有 generate 需要  
**影响**: 无，当前设计已符合

---

## 总结

这 5 个风险点不是缺陷，而是**成长的必然挑战**。关键是：

1. **提前识别**（✅ 已完成）
2. **设计预留空间**（✅ 当前架构支持）
3. **渐进式演进**（🔄 按优先级执行）

AgentOS 已经具备成为工程中枢的基础，接下来的演进要**保持架构优雅，避免技术债务累积**。

---

**文档维护**: 每次遇到新风险或解决方案时更新  
**审核周期**: 每季度回顾一次  
**责任人**: 架构负责人
