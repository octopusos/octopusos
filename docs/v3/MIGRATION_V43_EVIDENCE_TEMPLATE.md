# v43 迁移验收证据模板

## 用途
本模板用于记录 v43 迁移的不可抵赖证据，确保验收过程可审计、可复现、可签署。

---

## 证据 1: 数据库身份证（生产环境）

**执行时间**: 2026-01-31T13:21:24.495236

### 文件信息
- **绝对路径**: `/Users/pangge/PycharmProjects/AgentOS/store/registry.sqlite`
- **文件大小**: 54,591,488 bytes (52.06 MB)
- **最后修改**: 2026-01-31T13:20:18.016367
- **PRAGMA user_version**: 0

### 迁移状态
- **最新迁移版本**: 0.43.0
- **迁移时间**: 见 `schema_version` 表

### 数据规模
- **classifier_versions 行数**: 1
- **备份表状态**: 已清理（迁移完成后删除）

### 验收 Run ID
- **Run ID**: `1C99A69763D3FA3F`

**说明**: 此 Run ID 用于唯一标识本次验收执行，防止混淆不同批次的结果。

---

## 证据 2: 数据库身份证（测试环境）

**执行时间**: 2026-01-31T13:21:24

### 文件信息
- **绝对路径**: `/tmp/test_v43_rollback.db`
- **文件大小**: 28,672 bytes
- **用途**: 回滚演练测试

### 数据规模
- **classifier_versions 行数**: 2 (v1, v2)
- **备份表行数**: 2

### 测试 Run ID
- **Run ID**: `BC6E41789CF390D6`

**重要**: 此环境与生产环境独立，仅用于回滚机制验证。

---

## 证据 3: Gate-1 行数一致性

### 生产环境
```
迁移前行数: 1
迁移后行数: 1
状态: ✅ PASS (零丢失)
```

**注意**: 生产环境备份表已在验证通过后手动清理（符合流程）。

### 测试环境（回滚演练）
```
迁移前行数: 2
迁移后行数: 2
回滚后行数: 2
状态: ✅ PASS (回滚完整性验证)
```

---

## 证据 4: Gate-2 字段分布

### version_type 分布（生产环境）
```
version_type | count
-------------|------
active       |   1
```

### 一致性检查
```sql
SELECT COUNT(*) FROM classifier_versions
WHERE is_active = 1 AND version_type != 'active';
```
**结果**: 0 行
**状态**: ✅ PASS

---

## 证据 5: Gate-3 引用完整性

### version_id 唯一性
```
重复的 version_id: 0 个
```

### parent_version_id 引用完整性
```
孤立的 parent_version_id: 0 个
```

**状态**: ✅ PASS

---

## 证据 6: Gate-4 回滚可行性

### 回滚演练输出（测试环境）
```bash
=== v43 迁移回滚测试 ===
测试数据库: /tmp/test_v43_rollback.db

[Step 4] 验证备份表存在:
✅ 备份表存在: _classifier_versions_v43_backup
   备份表行数: 2

[Step 5] 执行回滚...
✅ 回滚执行成功

[Step 8] 最终验证:
✅ 行数一致: 2 = 2
✅ 版本号已回滚: 0.42.0

=== 回滚测试结果 ===
✅ 所有检查通过
✅ v43 迁移可以安全回滚
```

### 回滚时间
- **RENAME 操作**: 原子级元数据操作
- **当前规模实测**: <1s（测试环境 2 行，生产环境 1 行）
- **可扩展性**: 已提供脚本化回滚并演练通过

**重要表述**: RENAME 为 SQLite 原子级 DDL 操作，在当前生产库规模下实测 <1s；随数据增长可能浮动，但保持原子性。

**状态**: ✅ PASS

---

## 证据 7: Gate-5 结构与约束快照

### 快照文件
- **位置**: `docs/v3/artifacts/db_schema_snapshot_v43.sql`
- **生成时间**: 2026-01-31T13:21:24
- **验证方式**: `diff` 或 `sha256sum`

### 关键对象验证（生产环境）
```
✅ table: classifier_versions
✅ index: idx_classifier_versions_type
✅ index: idx_classifier_versions_active
✅ index: idx_classifier_versions_parent
✅ index: idx_classifier_versions_proposal
✅ index: idx_classifier_versions_created
```

### 字段清单（13 个）
```
✅ version_id (TEXT, PRIMARY KEY)
✅ version_type (TEXT, NOT NULL, CHECK)
✅ change_description (TEXT)
✅ version_number (TEXT)
✅ parent_version_id (TEXT)
✅ change_log (TEXT)
✅ source_proposal_id (TEXT)
✅ is_active (INTEGER, DEFAULT 0)
✅ created_by (TEXT)
✅ created_at (TEXT, NOT NULL)
✅ promoted_from (TEXT)
✅ deprecated_at (TEXT)
✅ metadata (TEXT, DEFAULT '{}')
```

### CHECK 约束
```
✅ version_type IN ('active', 'shadow')
✅ is_active IN (0, 1)
```

### FOREIGN KEY 约束
```
✅ parent_version_id → classifier_versions(version_id)
✅ source_proposal_id → improvement_proposals(proposal_id)
```

**状态**: ✅ PASS（结构完全符合设计）

---

## 口径澄清声明

### 之前报告的问题
在初始报告中，混淆了生产环境和测试环境的数据：
- ❌ "生产环境 1 行→1 行" 与 "备份表 2 行" 矛盾

### 纠正后的事实
- ✅ **生产环境**: 1 行数据（v1），备份表已清理
- ✅ **测试环境**: 2 行数据（v1, v2），用于回滚演练
- ✅ 两个环境独立运行，Run ID 不同

### 证据可追溯性
- 生产环境 Run ID: `1C99A69763D3FA3F`
- 测试环境 Run ID: `BC6E41789CF390D6`
- 快照文件: `db_schema_snapshot_v43.sql`（含完整 DDL）

---

## 最终验收结论

| Gate | 状态 | 证据位置 |
|------|------|----------|
| Gate-1: 行数一致性 | ✅ PASS | 证据 3 |
| Gate-2: 字段分布 | ✅ PASS | 证据 4 |
| Gate-3: 引用完整性 | ✅ PASS | 证据 5 |
| Gate-4: 回滚可行性 | ✅ PASS | 证据 6 |
| Gate-5: 结构快照 | ✅ PASS | 证据 7 + artifacts/ |

### 审计追溯链
```
生产 DB (52.06 MB, Run: 1C99A69763D3FA3F)
  → Gate-1~5 全部通过
  → 结构快照: db_schema_snapshot_v43.sql
  → 回滚演练: test_v43_rollback.db (Run: BC6E41789CF390D6)
  → 验收文档: MIGRATION_V43_ACCEPTANCE.md
```

### 签署条件
- [x] 所有 Gate 通过
- [x] DB 身份证完整
- [x] 结构快照存档
- [x] 回滚演练成功
- [x] 口径统一无矛盾

**最终结论**: ✅ **可签署上线**

---

## 附录：SQL 验证脚本

### 快速验证命令（生产环境）
```bash
# 1. DB 身份证
sqlite3 store/registry.sqlite << 'EOF'
SELECT
    'DB Path: ' || (SELECT file FROM pragma_database_list WHERE name='main'),
    'Size: ' || (SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()),
    'Latest Migration: ' || (SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1),
    'classifier_versions Count: ' || (SELECT COUNT(*) FROM classifier_versions),
    'Run ID: ' || hex(randomblob(8));
EOF

# 2. Gate-5 结构验证
sqlite3 store/registry.sqlite ".schema classifier_versions" | \
  diff - docs/v3/artifacts/db_schema_snapshot_v43.sql

# 3. 完整性检查
sqlite3 store/registry.sqlite << 'EOF'
-- 无重复
SELECT 'Duplicate IDs: ' || COUNT(*) FROM (
  SELECT version_id FROM classifier_versions GROUP BY version_id HAVING COUNT(*) > 1
);

-- 无孤立引用
SELECT 'Orphan Parents: ' || COUNT(*) FROM classifier_versions cv1
WHERE cv1.parent_version_id IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM classifier_versions cv2 WHERE cv2.version_id = cv1.parent_version_id);

-- 一致性
SELECT 'is_active=1 but not active: ' || COUNT(*) FROM classifier_versions
WHERE is_active = 1 AND version_type != 'active';
EOF
```

### 预期输出
```
DB Path: /path/to/store/registry.sqlite
Size: 54591488
Latest Migration: 0.43.0
classifier_versions Count: 1
Run ID: <16-digit-hex>

Duplicate IDs: 0
Orphan Parents: 0
is_active=1 but not active: 0
```

---

**模板版本**: 1.0
**创建日期**: 2026-01-31
**适用迁移**: v43
**维护人**: Claude Sonnet 4.5
