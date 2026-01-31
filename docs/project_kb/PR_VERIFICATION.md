# ProjectKB PR 验证步骤

## 验证清单

在合并 PR 前，请按顺序执行以下验证步骤。

### 1. 初始化 / 刷新

```bash
agentos kb refresh
```

**期望输出**:
```
✓ Refresh complete!

Total files       <数字>
Changed files     <数字>
Total chunks      <数字>
New chunks        <数字>
Duration          <X.XX>s
```

**验证**: 无报错，文件数 > 0，chunks 数 > 0

---

### 2. 基础搜索（应返回 path+heading+line_range+score+boosts）

```bash
agentos kb search "JWT authentication" --top-k 5
```

**期望输出**:
```
🔍 Search: JWT authentication
Found X result(s)

[1] docs/architecture/auth_design.md
    Section: ## JWT Implementation
    Lines: L45-L68
    Score: 8.50
    Matched: JWT, authentication
    ...
```

**验证**:
- 每条结果包含 path
- 包含 heading (如果有)
- 包含 lines (格式: LX-LY)
- 包含 score
- 包含 matched terms

---

### 3. Explain 完整性

```bash
agentos kb search "authentication" --top-k 1 --explain
```

**期望输出** (explain 部分):
```
✓ Matched terms: authentication, auth
  Frequencies: authentication(3), auth(2)
  Boosts: doc_type=1.50x, recency=1.20x
```

**验证**:
- matched_terms 非空
- term_frequencies 显示
- document_boost 显示
- recency_boost 显示

---

### 4. 删除文件一致性

```bash
# 创建测试文件
echo "# Unique Test Document" > docs/test_delete_verification.md
echo "This document contains a unique phrase: DELETEME12345" >> docs/test_delete_verification.md

# 索引
agentos kb refresh

# 验证能找到
agentos kb search "DELETEME12345"
# 应返回 docs/test_delete_verification.md

# 删除文件
rm docs/test_delete_verification.md

# 重新索引
agentos kb refresh

# 验证找不到
agentos kb search "DELETEME12345"
# 应返回 0 results
```

**验证**: 删除后搜索应返回 "No results found"

---

### 5. 新鲜度权重

```bash
# 修改某个已索引的文档
touch docs/architecture/some_design.md

# 重新索引
agentos kb refresh

# 搜索相关内容
agentos kb search "design" --explain

# 检查 explain 输出
```

**验证**: 刚修改的文档应：
- 排名靠前
- explain 中 recency_boost > 1.0

---

### 6. 文档类型权重

```bash
# 搜索同时存在于多种文档类型中的关键词
agentos kb search "authentication"
```

**验证**: 
- ADR 文档应排名高于普通文档
- INDEX.md 应排名最低
- explain 显示 document_boost 差异

---

### 7. Scope 过滤

```bash
# 只搜索 architecture 目录
agentos kb search "API" --scope docs/architecture/
```

**验证**: 所有结果的 path 都以 `docs/architecture/` 开头

---

### 8. IntentBuilder 集成

```bash
# 触发知识查询
agentos intent build "如何实现 JWT 认证？"
```

**期望输出** (在 selection_evidence 中):
```json
{
  "kb_selections": [
    {
      "chunk_id": "chunk_xxx",
      "path": "docs/architecture/auth_design.md",
      "evidence_refs": ["kb:chunk_xxx:docs/...#L45-L68"]
    }
  ]
}
```

**验证**:
- kb_selections 非空
- evidence_refs 格式正确

---

### 9. Fail-safe 行为

```bash
# 移动数据库
mv store/registry.sqlite store/registry.sqlite.bak

# 尝试搜索
agentos kb search "test"
```

**期望输出**:
```
⚠️  ProjectKB Warning: ProjectKB not initialized
   Run 'agentos kb refresh' to initialize the index.

No results found for: test
```

**验证**: 
- 不崩溃
- 显示友好提示
- 返回空结果

```bash
# 恢复数据库
mv store/registry.sqlite.bak store/registry.sqlite
```

---

### 10. Gate 脚本执行

```bash
./scripts/gates/run_projectkb_gates.sh
```

**期望输出**:
```
======================================================================
Gate Summary
======================================================================
Passed: X
Failed: 0

✅ All gates PASSED
```

**验证**: 所有 gates 通过

---

### 11. 统计信息

```bash
agentos kb stats
```

**期望输出**:
```
ProjectKB Statistics

Total chunks      <数字>
Schema version    1.2
Last refresh      YYYY-MM-DD HH:MM:SS
Database          store/registry.sqlite
```

**验证**: 所有信息正确显示

---

### 12. 重复刷新幂等性

```bash
agentos kb refresh --full
CHUNKS1=$(agentos kb stats | grep "Total chunks" | awk '{print $3}')

agentos kb refresh --full
CHUNKS2=$(agentos kb stats | grep "Total chunks" | awk '{print $3}')

echo "First: $CHUNKS1, Second: $CHUNKS2"
```

**验证**: CHUNKS1 == CHUNKS2

---

## 快速验证脚本

```bash
#!/bin/bash
# 快速验证所有关键功能

set -e

echo "1. Refresh..."
agentos kb refresh > /dev/null

echo "2. Basic search..."
agentos kb search "test" --top-k 1 > /dev/null

echo "3. Explain..."
agentos kb search "test" --explain --top-k 1 | grep -q "Matched"

echo "4. Stats..."
agentos kb stats | grep -q "Total chunks"

echo "5. Gates..."
./scripts/gates/run_projectkb_gates.sh

echo ""
echo "✅ All verifications passed!"
```

保存为 `scripts/verify_projectkb.sh` 并执行。

---

## 失败处理

如果任何步骤失败：

1. **记录失败步骤编号**
2. **复制错误输出**
3. **检查对应 Gate (见 GATE_CHECKLIST.md)**
4. **修复后重新验证**

---

## 性能基准

在本地测试环境（示例配置）：

- **索引时间**: ~100 文档/秒
- **搜索延迟**: <20ms (本地测试)
- **刷新时间**: 
  - 全量: ~2s (50 文档)
  - 增量: <0.5s (5 文件变更)

注意: 实际性能取决于文档数量和硬件配置。

---

## 完成确认

所有 12 个验证步骤通过后，在 PR 中添加：

```
✅ ProjectKB Verification Complete

All 12 verification steps passed:
- [x] Refresh
- [x] Basic search
- [x] Explain completeness
- [x] Delete file cleanup
- [x] Freshness boost
- [x] Doc type weights
- [x] Scope filter
- [x] IntentBuilder integration
- [x] Fail-safe behavior
- [x] Gate scripts
- [x] Stats
- [x] Idempotence

Performance (local test):
- Files indexed: XX
- Total chunks: XXX
- Search latency: <XXms
```
