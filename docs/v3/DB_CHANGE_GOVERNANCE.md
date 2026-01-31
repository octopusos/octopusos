# 数据库变更治理模板

**模板版本**: 1.0
**最后更新**: 2026-01-31
**来源**: v43 迁移实践抽象

---

## 适用范围

本模板适用于**所有不可逆或影响核心状态的数据库变更**，包括但不限于：

- ✅ DDL 变更（表结构、索引、约束）
- ✅ 数据迁移（字段合并、类型转换、数据推断）
- ✅ 约束增强（新增 CHECK、FOREIGN KEY、NOT NULL）
- ✅ 表重命名或拆分/合并
- ✅ 影响多个系统的共享表修改

**不适用场景**（可简化流程）：
- ❌ 仅新增表（不影响现有数据）
- ❌ 新增可选字段（允许 NULL）
- ❌ 新增索引（纯性能优化，无语义变更）

---

## 阶段 0：变更申请

### 0.1 变更描述（Change Description）

**迁移编号**: vXX
**申请人**: [姓名/系统名]
**申请日期**: YYYY-MM-DD

**变更目标**（用一句话说明）:
<!-- 示例：合并 Shadow Evaluation 和 Version Management 的 classifier_versions 表结构 -->

**影响范围**:
- [ ] 表：`table_name`
- [ ] 受影响代码模块：`module_a`, `module_b`
- [ ] 依赖系统：System A, System B

**变更原因**:
<!-- 为什么需要这个变更？解决什么问题？ -->

---

### 0.2 风险自评（Risk Self-Assessment）

| 风险维度 | 评估 | 说明 |
|----------|------|------|
| 数据丢失风险 | 高/中/低 | 是否涉及 DROP/DELETE？ |
| 可回滚性 | 高/中/低 | 备份策略是什么？ |
| 多系统冲突 | 高/中/低 | 是否有多个系统写同一表？ |
| 推断逻辑风险 | 高/中/低 | 是否需要推断新字段值？ |
| 锁定时间 | 高/中/低 | 预计锁表时间？ |

**红线检查**（任一违反则需升级审批）:
- [ ] 无生产环境备份
- [ ] 无回滚方案
- [ ] 涉及 DROP 且无 RENAME 替代

---

## 阶段 1：设计与审查

### 1.1 迁移策略选择

**策略类型**:
- [ ] 方案 A：原地修改（ALTER TABLE）
- [ ] 方案 B：RENAME + 重建（推荐，可回滚）
- [ ] 方案 C：新表 + 渐进迁移
- [ ] 方案 D：其他（说明）

**选择理由**:
<!-- 为什么选择这个策略？权衡了什么？ -->

---

### 1.2 SQL 脚本设计

**迁移脚本**: `agentos/store/migrations/schema_vXX_<description>.sql`

**关键步骤**:
```sql
-- Step 1: 幂等性检查
-- （如果备份表已存在，说明迁移已执行过，直接跳过）

-- Step 2: 备份（使用 RENAME，避免 DROP）
ALTER TABLE <table_name> RENAME TO _<table_name>_vXX_backup;

-- Step 3: 创建新表（完整 DDL）
CREATE TABLE <table_name> (
    -- 主键
    id TEXT PRIMARY KEY,

    -- 业务字段
    field1 TEXT NOT NULL,
    field2 INTEGER DEFAULT 0,

    -- 约束
    CHECK (field1 IN ('value1', 'value2')),
    FOREIGN KEY (parent_id) REFERENCES parent_table(id)
);

-- Step 4: 数据迁移（带推断逻辑说明）
INSERT INTO <table_name> (id, field1, field2)
SELECT
    id,
    CASE
        WHEN condition1 THEN 'value1'
        WHEN condition2 THEN 'value2'
        ELSE 'default'
    END as field1,
    old_field2
FROM _<table_name>_vXX_backup;

-- Step 5: 索引创建
CREATE INDEX idx_<table_name>_field1 ON <table_name>(field1);

-- Step 6: 版本记录
INSERT INTO schema_version (version, applied_at)
VALUES ('0.XX.0', CURRENT_TIMESTAMP);
```

**回滚脚本**: `agentos/store/migrations/rollback_vXX.sql`

```sql
BEGIN TRANSACTION;

-- Step 1: 删除新表
DROP TABLE IF EXISTS <table_name>;

-- Step 2: 恢复备份
ALTER TABLE _<table_name>_vXX_backup RENAME TO <table_name>;

-- Step 3: 回退版本号
DELETE FROM schema_version WHERE version = '0.XX.0';

COMMIT;
```

---

### 1.3 风险识别与缓解矩阵

| 风险编号 | 风险描述 | 缓解措施 | 验证方式 | 状态 |
|----------|----------|----------|----------|------|
| R1 | DROP 窗口期失败 | 使用 RENAME 而非 DROP | 回滚演练 | ⏳ |
| R2 | 字段推断错误 | 多条件检查 + 人工审核样本 | Gate-2 分布检查 | ⏳ |
| R3 | 多系统写冲突 | 字段权限矩阵 + ORM 限制 | 代码审查 | ⏳ |
| R4 | 唯一性破坏 | PRIMARY KEY/UNIQUE 约束 | Gate-3 完整性检查 | ⏳ |
| R5 | 约束不生效 | NOT NULL + CHECK 约束 | Gate-2 + Gate-5 | ⏳ |
| R6 | 迁移不幂等 | 备份表检测 | 重跑测试 | ⏳ |

---

## 阶段 2：测试与验证

### 2.1 环境准备

| 环境 | 数据库路径 | 数据规模 | 用途 | Run ID |
|------|-----------|---------|------|--------|
| **测试** | `/tmp/test_vXX.db` | N 行 | 回滚演练 | `<16位十六进制>` |
| **生产** | `/path/to/registry.sqlite` | M 行 | 实际迁移 | `<16位十六进制>` |

**生成 Run ID**:
```bash
echo "Run ID: $(sqlite3 /tmp/test.db "SELECT hex(randomblob(8))")"
```

---

### 2.2 Gate 检查清单

#### Gate-1: 行数一致性（零丢失）

**目标**: 确保 `before_count = after_count`

```sql
SELECT
    (SELECT COUNT(*) FROM _<table_name>_vXX_backup) as before_count,
    (SELECT COUNT(*) FROM <table_name>) as after_count,
    CASE WHEN (SELECT COUNT(*) FROM _<table_name>_vXX_backup) =
              (SELECT COUNT(*) FROM <table_name>)
    THEN '✅ PASS' ELSE '❌ FAIL' END as status;
```

**预期**: `before_count | after_count | status` = `N | N | ✅ PASS`

---

#### Gate-2: 关键字段分布

**目标**: 验证新字段值的合法性和分布合理性

```sql
-- 检查新字段分布
SELECT new_field, COUNT(*) as count
FROM <table_name>
GROUP BY new_field;

-- 检查 NULL 值（如果字段为 NOT NULL）
SELECT COUNT(*) FROM <table_name> WHERE new_field IS NULL;
```

**预期**:
- 所有值在合法范围内
- NOT NULL 字段无 NULL 值

---

#### Gate-3: 唯一性与引用完整性

**目标**: 验证主键唯一性和外键引用完整性

```sql
-- 检查主键重复
SELECT id, COUNT(*) as count
FROM <table_name>
GROUP BY id
HAVING COUNT(*) > 1;

-- 检查孤立外键
SELECT t1.id, t1.parent_id as orphan_parent
FROM <table_name> t1
WHERE t1.parent_id IS NOT NULL
AND NOT EXISTS (
    SELECT 1 FROM parent_table t2
    WHERE t2.id = t1.parent_id
);
```

**预期**:
- 无重复主键（0 行）
- 无孤立外键（0 行）

---

#### Gate-4: 回滚可行性（最重要）

**目标**: 验证迁移可以安全回滚

**测试步骤**:
```bash
# 1. 执行迁移
sqlite3 /tmp/test_vXX.db < agentos/store/migrations/schema_vXX_*.sql

# 2. 验证迁移成功
sqlite3 /tmp/test_vXX.db "SELECT COUNT(*) FROM <table_name>"

# 3. 执行回滚
sqlite3 /tmp/test_vXX.db < agentos/store/migrations/rollback_vXX.sql

# 4. 验证数据恢复
sqlite3 /tmp/test_vXX.db "SELECT COUNT(*) FROM <table_name>"
```

**预期**: 回滚后数据完整恢复到迁移前状态

**测试脚本**: `scripts/tests/test_vXX_rollback.sh`

---

#### Gate-5: 结构快照（可审计性）

**目标**: 生成可验证的表结构快照

**生成快照**:
```bash
# 导出完整 DDL
sqlite3 store/registry.sqlite ".schema <table_name>" > \
  docs/v3/artifacts/db_schema_snapshot_vXX.sql

# 追加索引定义
sqlite3 store/registry.sqlite << 'SQL' >> docs/v3/artifacts/db_schema_snapshot_vXX.sql
SELECT sql || ';' FROM sqlite_master
WHERE type='index'
AND tbl_name='<table_name>'
AND sql IS NOT NULL;
SQL

# 生成 SHA256 哈希
shasum -a 256 docs/v3/artifacts/db_schema_snapshot_vXX.sql
```

**快照哈希**: `<SHA256值>`

**验证命令**:
```bash
sqlite3 store/registry.sqlite ".schema <table_name>" | \
  diff - docs/v3/artifacts/db_schema_snapshot_vXX.sql
```

---

### 2.3 DB 身份证（不可抵赖的证据）

为每个环境生成唯一身份证：

**生产环境**:
```bash
sqlite3 store/registry.sqlite << 'SQL'
SELECT
    '=== DB 身份证（生产环境）===' as header
UNION ALL SELECT ''
UNION ALL SELECT 'Run ID: ' || hex(randomblob(8))
UNION ALL SELECT 'Database: ' || (SELECT file FROM pragma_database_list WHERE name='main')
UNION ALL SELECT 'File Size: ' || (SELECT page_count * page_size / 1024.0 / 1024.0 || ' MB' FROM pragma_page_count(), pragma_page_size())
UNION ALL SELECT 'Schema Version: ' || (SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1)
UNION ALL SELECT 'Row Count (<table_name>): ' || CAST((SELECT COUNT(*) FROM <table_name>) as TEXT);
SQL
```

**测试环境**: （同上，使用测试数据库路径）

---

## 阶段 3：执行与监控

### 3.1 前置检查

```bash
# 1. 检查 WAL checkpoint（确保无长事务）
sqlite3 store/registry.sqlite "PRAGMA wal_checkpoint(FULL)"
# 预期输出: 0|0|0

# 2. 备份数据库（可选，二次保险）
cp store/registry.sqlite store/registry.sqlite.before-vXX-$(date +%Y%m%d-%H%M%S)

# 3. 检查磁盘空间
df -h store/
```

---

### 3.2 执行迁移（带重试逻辑）

```bash
#!/bin/bash
# 执行 vXX 迁移（带锁重试）

MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if sqlite3 store/registry.sqlite < agentos/store/migrations/schema_vXX_*.sql; then
        echo "✅ 迁移成功"
        break
    else
        EXIT_CODE=$?
        RETRY_COUNT=$((RETRY_COUNT + 1))

        if [ $EXIT_CODE -eq 5 ]; then
            echo "⚠️  数据库锁定，等待 5 秒后重试 ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 5
        else
            echo "❌ 迁移失败（非锁定错误，退出码: $EXIT_CODE）"
            exit $EXIT_CODE
        fi
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ 达到最大重试次数，请在维护窗口执行"
    exit 1
fi
```

---

### 3.3 执行后验证

```bash
# 运行所有 Gate 检查
sqlite3 store/registry.sqlite << 'EOF'
-- Gate-1: 行数一致性
SELECT 'Gate-1: ' ||
  CASE WHEN (SELECT COUNT(*) FROM _<table_name>_vXX_backup) =
            (SELECT COUNT(*) FROM <table_name>)
  THEN '✅ PASS' ELSE '❌ FAIL' END;

-- Gate-2: NULL 值检查
SELECT 'Gate-2: ' ||
  CASE WHEN (SELECT COUNT(*) FROM <table_name> WHERE new_field IS NULL) = 0
  THEN '✅ PASS' ELSE '❌ FAIL' END;

-- Gate-3: 主键重复检查
SELECT 'Gate-3: ' ||
  CASE WHEN (SELECT COUNT(*) FROM (
    SELECT id FROM <table_name> GROUP BY id HAVING COUNT(*) > 1
  )) = 0
  THEN '✅ PASS' ELSE '❌ FAIL' END;
EOF

# 验证结构快照
shasum -a 256 docs/v3/artifacts/db_schema_snapshot_vXX.sql
# 预期: <SHA256值>
```

---

### 3.4 监控建议

**迁移后 24 小时内**:
- [ ] 监控受影响功能的正常运行
- [ ] 检查数据库大小变化
- [ ] 检查 SQLite 错误日志
- [ ] 观察应用层日志中的数据库错误

**异常处理**:
如发现任何异常：
1. 立即回滚（使用回滚脚本）
2. 记录错误日志和现象
3. 运行 Gate 检查定位问题
4. 修正后重新迁移

---

## 阶段 4：清理与归档

### 4.1 备份表清理条件

**必须全部满足**:
- [ ] 所有 Gate 检查通过
- [ ] 生产环境运行 24 小时无异常
- [ ] 受影响功能验证通过
- [ ] 数据库备份已在其他位置保存（可选）

**清理命令**:
```sql
DROP TABLE IF EXISTS _<table_name>_vXX_backup;
```

---

### 4.2 文档归档

所有文档归档到 `docs/v3/` 目录：

```
docs/v3/
├── MIGRATION_VXX_ACCEPTANCE.md          ← 验收报告
├── MIGRATION_VXX_EVIDENCE_TEMPLATE.md   ← 完整证据
├── VXX_RISK_MITIGATION_SUMMARY.md       ← 风险缓解总结
├── VXX_FINAL_SUMMARY.md                 ← 最终总结
├── FINAL_SIGN_OFF_CHECKLIST_VXX.md      ← 签署清单
└── artifacts/
    └── db_schema_snapshot_vXX.sql       ← 结构快照
```

---

### 4.3 签署清单

| 角色 | 姓名 | 日期 | 签名 |
|------|------|------|------|
| 迁移执行人 | [姓名] | YYYY-MM-DD | ⏳ |
| 守门员审查 | [姓名] | YYYY-MM-DD | ⏳ |
| 技术审批 | [姓名] | YYYY-MM-DD | ⏳ |
| 上线批准 | [姓名] | YYYY-MM-DD | ⏳ |

---

## 附录 A：快速验证命令

### 单命令完整性检查

```bash
sqlite3 store/registry.sqlite << 'EOF'
.mode column
.headers on

-- 基本信息
SELECT 'Database:' as Check, file as Value
FROM pragma_database_list WHERE name='main'
UNION ALL
SELECT 'Migration:', version FROM schema_version
ORDER BY applied_at DESC LIMIT 1
UNION ALL
SELECT 'Row Count:', CAST(COUNT(*) as TEXT) FROM <table_name>
UNION ALL
SELECT 'Duplicates:', CAST(COUNT(*) as TEXT) FROM (
  SELECT id FROM <table_name> GROUP BY id HAVING COUNT(*) > 1
);
EOF
```

---

## 附录 B：环境对比总表模板

| 环境 | 数据库路径 | user_version | 迁移版本 (before→after) | 行数 (before→after) | 备份表行数 | Run ID |
|------|-----------|--------------|------------------------|-------------------|-----------|--------|
| **生产** | `/path/to/registry.sqlite` | 0 | 0.XX.0 → 0.XX.0 | N → N | 已清理 | `<16位>` |
| **测试** | `/tmp/test_vXX.db` | 0 | 0.XX.0 → 0.XX.0 → 0.XX.0 (回滚) | M → M → M | M | `<16位>` |

---

## 附录 C：口径严谨性自查

在编写验收报告时，避免以下不严谨表述：

| 不严谨表述 | 严谨表述 |
|------------|----------|
| "回滚时间 < 1 秒" | "RENAME 为原子级操作；在当前规模实测 <1s；已演练通过" |
| "备份表 2 行" | "生产环境已清理；测试环境备份 2 行" |
| "迁移完成" | "生产环境: 1→1；测试环境: 2→2" |
| "保证零丢失" | "Gate-1 验证通过：before_count = after_count" |

**原则**:
- 时间/性能表述加上"当前规模实测"限定
- 环境相关数据明确标注环境名称
- 用证据支撑结论，而非断言

---

## 附录 D：守门员审查清单

守门员审查时需确认以下 10 个关键点：

| # | 检查项 | 检查方式 | 状态 |
|---|--------|----------|------|
| 1 | DB 身份证完整 | 包含 Run ID + 路径 + 大小 | ⏳ |
| 2 | Gate-1~5 全部通过 | 验收报告有完整输出 | ⏳ |
| 3 | 回滚演练成功 | 测试脚本执行记录 | ⏳ |
| 4 | 结构快照 + SHA256 | 快照文件存在且哈希可验证 | ⏳ |
| 5 | Run ID 对应关系表 | 环境对比总表完整 | ⏳ |
| 6 | 并发/锁处理说明 | Runbook 有重试逻辑 | ⏳ |
| 7 | 风险缓解完整 | 每个风险点有缓解措施 | ⏳ |
| 8 | 口径无矛盾 | 行数/环境/时间表述一致 | ⏳ |
| 9 | 表述严谨 | 无绝对保证，有限定条件 | ⏳ |
| 10 | 证据可追溯 | 所有证据有来源和验证方式 | ⏳ |

**签署条件**: 全部 10 项 ✅

---

## 哲学陈述

> **This migration governance is signed off not because it worked once, but because it can be proven, reproduced, and rolled back.**

---

**模板维护者**: Claude Sonnet 4.5
**版本历史**:
- v1.0 (2026-01-31): 初始版本，基于 v43 迁移实践抽象
