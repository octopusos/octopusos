# Classifier Versions Table 设计文档

## 问题背景

在 v3 实施中（commit 624114d），两个独立任务为了不同目的都需要记录 classifier 版本信息，导致表结构冲突：

- **Task #28** (Shadow Evaluation): 需要区分 active/shadow 决策
- **Task #10** (Version Management): 需要版本历史和回滚链

## 解决方案：统一表结构（v43 迁移）

采用**方案 1：合并表结构**，将两个概念统一到一个表中：

### 表结构

```sql
CREATE TABLE classifier_versions (
    version_id TEXT PRIMARY KEY,

    -- 【语义层】Shadow Evaluation / Decision Semantics
    version_type TEXT NOT NULL,      -- "active" | "shadow"
    change_description TEXT,

    -- 【治理层】Version Management / Evolution Governance
    version_number TEXT,             -- "1.0", "2.0"
    parent_version_id TEXT,          -- 回滚链
    change_log TEXT,
    source_proposal_id TEXT,
    is_active INTEGER DEFAULT 0,
    created_by TEXT,

    -- 【通用】
    created_at TEXT NOT NULL,
    promoted_from TEXT,
    deprecated_at TEXT,
    metadata TEXT DEFAULT '{}'
);
```

## 两层语义

### 1. 语义层（Shadow Evaluation）

**用途**: 区分 active 和 shadow classifier 实例

**使用场景**:
- `decision_candidate_store.py` - 保存决策时记录来自哪个 classifier
- `shadow_registry.py` - 验证只有 shadow 类型的 classifier 可以注册
- `shadow_classifier.py` - 运行时判断决策角色

**关键字段**:
- `version_type`: "active" | "shadow"
- `change_description`: 这个版本改了什么（简短）

**示例**:
```python
# Shadow classifier
ClassifierVersion(
    version_id="v2-shadow-expand-keywords",
    version_type="shadow",
    change_description="Expanded local_deterministic keywords"
)

# Active classifier
ClassifierVersion(
    version_id="v1",
    version_type="active"
)
```

### 2. 治理层（Version Management）

**用途**: 版本演进、回滚、提案管理

**使用场景**:
- `classifier_version_manager.py` - 创建新版本、管理版本历史
- `classifier_migrate.py` - Shadow → Active 迁移
- `improvement_proposals.py` - 关联改进提案到版本

**关键字段**:
- `version_number`: 语义化版本号 "1.0", "2.0"
- `parent_version_id`: 父版本（回滚链）
- `is_active`: 当前是否激活
- `change_log`: 详细变更日志
- `source_proposal_id`: 来源提案

**示例**:
```python
# 从提案创建新版本
conn.execute("""
    INSERT INTO classifier_versions (
        version_id, version_number, parent_version_id,
        change_log, source_proposal_id, is_active,
        version_type, created_by, created_at
    ) VALUES (
        'v2', '2.0', 'v1',
        'Expanded keywords based on BP-017',
        'BP-017', 0,
        'shadow', 'system', CURRENT_TIMESTAMP
    )
""")
```

## 典型生命周期

一个 classifier version 从 shadow 到 active 的完整生命周期：

```
1. 创建 Shadow 版本（来自提案）
   version_id: v2
   version_type: shadow
   version_number: 2.0
   parent_version_id: v1
   is_active: 0

2. Shadow 评估期（并行运行，不影响用户）
   - decision_candidates 表记录所有决策
   - Reality Alignment Score 评估效果

3. 人工审查通过 → 迁移为 Active
   UPDATE classifier_versions SET
       version_type = 'active',
       is_active = 1,
       promoted_from = 'v2-shadow'
   WHERE version_id = 'v2'

4. 如果需要回滚
   - parent_version_id 指向 v1
   - 可以一键恢复到父版本
```

## 迁移历史

- **v40**: 创建基础 `classifier_versions` 表（语义层）
- **v41**: 创建 `improvement_proposals` 表
- **v42**: 创建 `version_rollback_history` 表（治理层）
- **v43**: **合并 v40 + v42 字段到统一表**

## 设计原则

1. **不是妥协，是统一**
   一个 classifier 在任意时刻既有运行语义（active/shadow），也有演进位置（version graph）

2. **字段职责清晰**
   - `version_type` 用于运行时决策绑定
   - `is_active` 用于治理和迁移管理
   - 两者不混用

3. **Shadow → Active 迁移自然**
   ```sql
   UPDATE classifier_versions SET
       version_type = 'active',
       is_active = 1
   ```

4. **向后兼容**
   - v40 的数据可以补齐 NULL 字段继续使用
   - v42 的数据可以推断 `version_type` (is_active=1 → active)

## 测试验证

✅ Shadow Evaluation 路径正常工作
✅ Version Management 路径正常工作
✅ Pydantic 模型兼容数据库表
✅ 数据迁移无丢失

## 相关文件

- 迁移文件: `agentos/store/migrations/schema_v43_merge_classifier_versions.sql`
- 数据模型: `agentos/core/chat/models/decision_candidate.py`
- Shadow Registry: `agentos/core/chat/shadow_registry.py`
- Version Manager: `agentos/core/brain/classifier_version_manager.py`
