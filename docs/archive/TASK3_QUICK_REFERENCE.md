# P1-A Task 3: API 端点集成 - 快速参考

## 新增 API 端点

### 1. Coverage 端点

```
GET /api/brain/coverage
```

**返回示例**:
```json
{
  "ok": true,
  "data": {
    "total_files": 3140,
    "covered_files": 2258,
    "code_coverage": 0.719,
    "doc_coverage": 0.682,
    "dependency_coverage": 0.068,
    "uncovered_files": [...],
    "evidence_distribution": {...}
  }
}
```

### 2. Blind Spots 端点

```
GET /api/brain/blind-spots?threshold=5&max_results=50
```

**参数**:
- `threshold`: 高 fan-in 阈值 (默认 5)
- `max_results`: 最大返回数量 (默认 50)

**返回示例**:
```json
{
  "ok": true,
  "data": {
    "total_blind_spots": 17,
    "by_type": {...},
    "by_severity": {...},
    "blind_spots": [...]
  }
}
```

### 3. coverage_info 字段

所有查询端点（why/impact/trace/subgraph）现在都包含：

```json
{
  "data": {
    "coverage_info": {
      "evidence_sources": ["git", "doc", "code"],
      "source_coverage": 1.0,
      "explanation": "..."
    },
    ...
  }
}
```

---

## 测试命令

```bash
# 覆盖率
curl http://localhost:5000/api/brain/coverage | jq .

# 盲区
curl http://localhost:5000/api/brain/blind-spots | jq .

# Why 查询（验证 coverage_info）
curl -X POST http://localhost:5000/api/brain/query/why \
  -H "Content-Type: application/json" \
  -d '{"seed": "file:agentos/core/task/manager.py"}' | jq .data.coverage_info
```

---

## 关键函数

### compute_result_coverage_info(result)
计算查询结果的覆盖信息

**逻辑**:
- 从 evidence 中提取 source_type
- 分类为 git/doc/code
- 计算 source_coverage = source_count / 3.0

### generate_coverage_explanation(sources)
生成用户友好的覆盖说明

**逻辑**:
- 3 sources → "based on all sources"
- 2 sources → "based on X/Y. Missing: Z"
- 1 source → "based only on X. Limited coverage"
- 0 sources → "No evidence sources found"

---

## 文件位置

- **API 实现**: `agentos/webui/api/brain.py`
- **Coverage 引擎**: `agentos/core/brain/service/coverage.py`
- **Blind Spot 引擎**: `agentos/core/brain/service/blind_spot.py`
- **测试脚本**: `test_task3_api.py`
- **手动测试**: `test_task3_curl.sh`

---

## 错误处理

所有端点都使用统一的错误格式：

```json
{
  "ok": false,
  "data": null,
  "error": "BrainOS index not found. Build index first."
}
```

---

## 性能指标

- **Coverage 计算**: ~50ms (3140 文件)
- **Blind Spot 检测**: ~8ms (17 盲区)
- **SQL 查询**: 7 次 (Coverage), 3 次 (Blind Spots)
- **内存占用**: 最小（流式处理）

---

## 下一步集成

**前端开发** (Task 4):
1. 在 Dashboard 中展示覆盖率指标
2. 在 Blind Spots 视图中展示盲区列表
3. 在查询结果中展示 coverage_info

**端到端测试** (Task 5):
1. 测试完整的用户流程
2. 验证数据一致性
3. 性能基准测试
