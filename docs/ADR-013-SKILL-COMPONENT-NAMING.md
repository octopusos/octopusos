# ADR-013: Skill Component Naming Contract

**Status**: ACCEPTED  
**Date**: 2026-02-01  
**Decision Maker**: Gate Review  
**Scope**: SkillOS Component Naming

---

## Decision

**组件名称冻结为：`skill`（单数）**

- ✅ 数据库路径：`~/.agentos/store/skill/db.sqlite`
- ✅ 缓存路径：`~/.agentos/store/skills_cache/`（复数，因为缓存多个 skills）
- ✅ 代码包名：`agentos.skills.*`（复数，因为是模块集合）
- ✅ API 路由：`/api/skills`（复数，RESTful 风格）
- ✅ CLI 命令：`agentos skill`（单数）

## Context

在实施过程中出现了 `skill` 和 `skills` 混用的情况。为了避免：
1. 第二数据库出现（`skill/db.sqlite` vs `skills/db.sqlite`）
2. 路径一致性问题
3. API contract 不稳定

必须做出明确的命名裁决。

## Rationale

### 为什么数据库用单数 `skill`？

1. **已实现成本**：代码已经使用 `skill`，改动成本高
2. **组件唯一性**：强调"SkillOS 是一个组件"，不是"多个 skills 组件"
3. **避免混淆**：与 `skills_cache` 区分（cache 是存储多个 skills）
4. **遵循现有模式**：
   - `memory` (不是 memories)
   - `brain` (不是 brains)
   - `agentos` (不是 agents)

### 为什么 API/CLI 用复数 `skills`？

1. **RESTful 约定**：`GET /api/skills` 返回多个资源
2. **用户友好**：`agentos skill list` 比 `agentos skills list` 更自然
3. **代码模块**：`agentos.skills` 表示"skills 相关的模块集合"

## Decision Rules

| 上下文 | 使用 | 示例 |
|--------|------|------|
| **Component DB** | `skill` (单数) | `component_db_path("skill")` |
| **数据库路径** | `skill` (单数) | `~/.agentos/store/skill/db.sqlite` |
| **缓存目录** | `skills_cache` (复数) | `~/.agentos/store/skills_cache/` |
| **Python 包** | `skills` (复数) | `from agentos.skills import ...` |
| **API 路由** | `skills` (复数) | `GET /api/skills` |
| **CLI 命令** | `skill` (单数) | `agentos skill list` |
| **UI 文案** | `Skills` (复数) | "Skills Marketplace" |
| **文档标题** | `Skill` 或 `Skills` | 根据语境（单个 skill vs 多个 skills）|

## Enforcement

### Gate 测试

```python
def test_no_second_skill_database():
    """确保不会出现第二个 skill 数据库"""
    store_path = Path.home() / ".agentos" / "store"
    
    # 只允许这两个路径
    allowed = {
        store_path / "skill" / "db.sqlite",
        store_path / "skills_cache"  # 目录，不是 db
    }
    
    # 查找所有 skill* 相关路径
    skill_paths = list(store_path.glob("skill*"))
    skill_dbs = list(store_path.glob("skill*/db.sqlite"))
    
    # 断言只有一个 skill db
    assert len(skill_dbs) == 1, f"发现多个 skill 数据库: {skill_dbs}"
    assert skill_dbs[0] == store_path / "skill" / "db.sqlite"
```

### 代码审查清单

在 PR review 时，检查：
- [ ] 没有使用 `component_db_path("skills")`（复数）
- [ ] 没有创建 `~/.agentos/store/skills/db.sqlite`
- [ ] API 路由使用 `/api/skills`（复数）
- [ ] CLI 命令使用 `agentos skill`（单数）
- [ ] Python import 使用 `from agentos.skills`（复数）

## Migration Path

如果未来需要改名，必须提供向后兼容：

```python
def component_db_path(component: str) -> Path:
    # 兼容旧路径
    if component == "skills":
        # 检查是否有旧数据
        old_path = store / "skills" / "db.sqlite"
        new_path = store / "skill" / "db.sqlite"
        if old_path.exists() and not new_path.exists():
            # 迁移提示
            logger.warning(f"发现旧路径 {old_path}，请迁移到 {new_path}")
        return new_path
    return store / component / "db.sqlite"
```

## Consequences

### Positive
- ✅ 路径一致性保证
- ✅ 避免第二数据库
- ✅ API contract 稳定
- ✅ 文档和代码一致

### Negative
- ⚠️ 单复数混用（但有明确规则）
- ⚠️ 需要在文档中解释命名约定

### Neutral
- ℹ️ 新开发者需要学习命名规则

## References

- 现有组件命名：memory, brain, agentos
- RESTful API 约定：复数资源名
- CLI 约定：单数命令（docker container, kubectl pod）

---

**Frozen**: 此决策已冻结，除非有重大架构变更，否则不得修改。
