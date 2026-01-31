# Intent Builder Authoring Guide (v0.9.4)

## 📝 NL 输入编写指南

### NL Request 结构

```yaml
id: nl_req_[a-z0-9_]{6,64}    # 唯一标识符
schema_version: "0.9.4"        # Schema 版本
project_id: "项目名称"          # 项目 ID
input_text: |                  # 自然语言输入（核心）
  你的任务描述...
context_hints:                 # 可选：上下文提示
  files: [...]                 # 相关文件列表
  modules: [...]               # 相关模块列表
  areas: [...]                 # 技术领域
created_at: "ISO8601 时间戳"
checksum: "SHA-256"
lineage:                       # 血缘关系
  introduced_in: "0.9.4"
  derived_from: []
  supersedes: []
```

### input_text 编写技巧

#### ✅ 好的输入

```yaml
input_text: |
  实现用户个人资料更新功能：
  - 添加 PATCH /api/users/profile API
  - 支持字段：name, email, avatar_url
  - 需要 JWT 身份验证
  - 添加参数验证（email 格式、name 长度）
  - 添加单元测试和集成测试
```

**好在哪里**：
- ✅ 使用明确的动词（实现、添加）
- ✅ 列出具体的子任务
- ✅ 包含技术细节（API 路径、字段名）
- ✅ 明确约束（身份验证、验证规则）

#### ❌ 糟糕的输入

```yaml
input_text: "可能需要优化一下用户功能"
```

**问题**：
- ❌ 动词模糊（"可能"、"优化"）
- ❌ 目标不明确（"用户功能"太宽泛）
- ❌ 没有具体操作

### context_hints 使用

#### files - 指定相关文件

```yaml
context_hints:
  files:
    - "src/services/UserService.ts"
    - "src/api/routes/users.ts"
```

**作用**：
- 限制 Builder 关注的范围
- 生成更精准的 `scope.targets.files`

#### modules - 指定相关模块

```yaml
context_hints:
  modules:
    - "user_service"
    - "api_routes"
```

**作用**：
- 帮助选择相关 agents
- 影响 workflow 选择

#### areas - 指定技术领域

```yaml
context_hints:
  areas:
    - "backend"
    - "tests"
```

**可选值**：`frontend`, `backend`, `infra`, `docs`, `tests`, `ops`, `security`, `data`

**作用**：
- 影响风险评估
- 选择匹配的 agents
- 决定 `requires_review` 内容

### 如何触发提问

Builder 在以下情况会生成问题：

#### 1. 缺失操作（Ambiguity: missing_actions）

```yaml
input_text: "关于用户系统"
```

→ 问题：`"没有检测到明确的操作，请说明具体任务"`

#### 2. 模糊规格（Ambiguity: vague_specification）

```yaml
input_text: "可能需要某种形式的优化"
```

→ 问题：`"输入包含模糊术语，请提供更具体的需求"`

#### 3. 过多操作（Ambiguity: too_many_actions）

```yaml
input_text: |
  实现用户注册、登录、注销、个人资料、密码重置、
  邮箱验证、双因素认证、权限管理、角色系统、
  审计日志、会话管理、API 令牌...
```

→ 问题：`"检测到 {N} 个操作，是否需要分阶段或优先级排序？"`

### Policy 选择指南

| 场景 | 推荐 Policy | 理由 |
|------|------------|------|
| 文档/注释 | `full_auto` | 低风险，无歧义 |
| 新增 API endpoint | `semi_auto` | 中风险，大部分明确 |
| 数据库迁移 | `interactive` 或 `semi_auto` | 高风险，需要确认 |
| 重构核心模块 | `interactive` | 高风险，可能有歧义 |
| 添加单元测试 | `full_auto` 或 `semi_auto` | 低-中风险 |

**约束**：
- `high`/`critical` 风险 **不能** 使用 `full_auto`（Schema 强制）
- `full_auto` **必须** `question_budget=0`（RED LINE）

### Evidence Refs 格式

Builder 自动生成证据引用，格式：

#### nl_input（NL 输入片段）

```
nl_input:start:end
```

示例：`nl_input:0:100`（输入的前 100 个字符）

#### registry（Registry 内容）

```
registry:content_id:version
```

示例：`registry:documentation:1.0.0`

#### rule（规则引用）

```
rule:rule_id
```

示例：`rule:r02_lineage_required`

#### context_hint（上下文提示）

```
context_hint:type:value
```

示例：`context_hint:areas:backend,tests`

### 3 个完整示例

#### 示例 1：低风险（文档）

```yaml
id: nl_req_low_risk_doc
schema_version: "0.9.4"
project_id: "agentos"
input_text: |
  为 IntentBuilder 类添加完整的文档注释：
  - 类级别的 docstring
  - 每个公共方法的参数和返回值说明
  - 使用示例
context_hints:
  files: ["agentos/core/intent_builder/builder.py"]
  areas: ["docs"]
created_at: "2026-01-25T10:00:00Z"
checksum: "..."
lineage:
  introduced_in: "0.9.4"
  derived_from: []
  supersedes: []
```

**预期输出**：
- risk: `low`
- workflows: `[documentation]`
- agents: `[technical_writer]`
- question_pack: `null`（无歧义）

#### 示例 2：中风险（API）

```yaml
id: nl_req_medium_risk_api
schema_version: "0.9.4"
project_id: "agentos"
input_text: |
  实现 Builder 历史记录查询 API：
  - GET /api/builder/history
  - GET /api/builder/history/:id
  - 支持分页和过滤
  - 添加单元测试
context_hints:
  modules: ["api", "builder_service"]
  areas: ["backend", "tests"]
created_at: "2026-01-25T11:00:00Z"
checksum: "..."
lineage:
  introduced_in: "0.9.4"
  derived_from: []
  supersedes: []
```

**预期输出**：
- risk: `medium`
- workflows: `[api_design, testing_strategy]`
- agents: `[backend_engineer, qa_engineer]`
- question_pack: 可能有 1-2 个澄清问题

#### 示例 3：高风险（数据库）

```yaml
id: nl_req_high_risk_db
schema_version: "0.9.4"
project_id: "agentos"
input_text: |
  添加 Builder 输出持久化：
  - 新增 builder_outputs 表
  - 新增 builder_selections 表
  - 添加索引
  - 编写迁移脚本（向后兼容）
  - 更新 Builder 保存输出到 DB
  - 添加回滚方案
context_hints:
  modules: ["database", "builder_service", "migrations"]
  areas: ["backend", "data", "security"]
created_at: "2026-01-25T12:00:00Z"
checksum: "..."
lineage:
  introduced_in: "0.9.4"
  derived_from: []
  supersedes: []
```

**预期输出**：
- risk: `high`
- mode: `interactive` 或 `semi_auto`（**不能** `full_auto`）
- workflows: `[database_migration, security_review]`
- agents: `[backend_engineer, security_engineer]`
- requires_review: `[data, security, architecture]`
- question_pack: 多个关键问题（迁移策略、回滚计划等）

## 🧪 测试你的 NL 输入

### 1. 运行 explain

```bash
agentos builder explain --input my_request.yaml
```

检查：
- 解析的 goal 是否正确
- 检测到的 actions 是否完整
- 风险级别是否合理
- 是否有预期的歧义

### 2. 运行 Builder

```bash
agentos builder run --input my_request.yaml --out outputs/
```

### 3. 验证输出

```bash
agentos builder validate --file outputs/my_output.json
```

### 4. 检查生成的 Intent

查看 `execution_intent` 中的：
- `selected_workflows`: 是否匹配预期
- `selected_agents`: 是否覆盖所需角色
- `planned_commands`: 是否合理
- `risk.overall`: 是否符合预期
- `interaction.mode`: 是否符合策略

## ⚠️ 常见问题

### Q: 为什么 Builder 没有选择我期望的 workflow？

**A**: 可能原因：
1. workflow 不在 Registry 中（Builder 不编造）
2. NL 输入关键词不匹配
3. 使用 `explain` 查看匹配分数

**解决**：
- 添加更明确的关键词
- 使用 `context_hints.areas` 引导
- 检查 Registry 中是否有该 workflow

### Q: 为什么 Builder 生成了很多问题？

**A**: 可能原因：
1. input_text 包含模糊术语（"可能"、"某种"）
2. 操作过多（>10 个）
3. 使用了 `interactive` 策略

**解决**：
- 使用明确的动词和具体的任务
- 拆分成多个 NL 请求
- 使用 `semi_auto` 或 `full_auto` 策略

### Q: 为什么 full_auto 模式失败？

**A**: 可能原因：
1. 风险级别是 `high` 或 `critical`（Schema 禁止）
2. Builder 检测到歧义（自动降级到 semi_auto）

**解决**：
- 对高风险任务使用 `semi_auto` 或 `interactive`
- 提供更明确的 input_text

## 📚 参考资料

- [V094_INTENT_BUILDER_README.md](./V094_INTENT_BUILDER_README.md) - 概览
- [nl_request.schema.json](../../agentos/schemas/execution/nl_request.schema.json) - Schema 规范
- [intent_builder_output.schema.json](../../agentos/schemas/execution/intent_builder_output.schema.json) - 输出 Schema

---

**版本**: 0.9.4  
**最后更新**: 2026-01-25
