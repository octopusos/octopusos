# P1-B Task 2: Autocomplete API - Quick Reference

## 新增 API 端点

### GET /api/brain/autocomplete

**功能**: 提供认知安全的 autocomplete 建议

#### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prefix` | string | ✅ Yes | - | 用户输入的前缀 |
| `limit` | integer | ❌ No | 10 | 最多返回的建议数量（1-50） |
| `entity_types` | string | ❌ No | - | 限制实体类型，逗号分隔（如 `file,capability`） |
| `include_warnings` | boolean | ❌ No | false | 是否包含中等风险盲区 |

#### 响应格式

```json
{
  "ok": true,
  "data": {
    "suggestions": [
      {
        "entity_type": "file",
        "entity_key": "agentos/core/task/manager.py",
        "entity_name": "manager.py",
        "safety_level": "safe",
        "evidence_count": 15,
        "coverage_sources": ["git", "doc", "code"],
        "is_blind_spot": false,
        "blind_spot_severity": null,
        "blind_spot_reason": null,
        "display_text": "file:agentos/core/task/manager.py",
        "hint_text": "✅ 3/3 sources covered (git+doc+code)"
      }
    ],
    "total_matches": 25,
    "filtered_out": 15,
    "filter_reason": "Filtered out 15 entities: 10 unverified, 5 high-risk blind spots",
    "graph_version": "v_abc123_20260130",
    "computed_at": "2026-01-30T12:00:00Z"
  },
  "error": null
}
```

#### 示例请求

##### 1. 基本用法
```bash
curl "http://localhost:5000/api/brain/autocomplete?prefix=task"
```

##### 2. 限制返回数量
```bash
curl "http://localhost:5000/api/brain/autocomplete?prefix=file&limit=5"
```

##### 3. 过滤实体类型
```bash
curl "http://localhost:5000/api/brain/autocomplete?prefix=agen&entity_types=file,capability"
```

##### 4. 包含警告级别的盲区
```bash
curl "http://localhost:5000/api/brain/autocomplete?prefix=gov&include_warnings=true"
```

## Safety Level 说明

| Level | 值 | 说明 |
|-------|-----|------|
| ✅ SAFE | "safe" | 满足所有 4 条认知标准，无盲区风险 |
| ⚠️ WARNING | "warning" | 中等盲区风险（severity 0.4-0.7） |
| 🚨 DANGEROUS | "dangerous" | 高盲区风险（severity >= 0.7），默认不返回 |
| ❓ UNVERIFIED | "unverified" | 无证据或未索引，永远不返回 |

## 认知过滤标准

Autocomplete 只建议满足**所有 4 条**标准的实体：

1. ✅ **Indexed**: 实体存在于 entities 表
2. ✅ **Has Evidence**: >= 1 条 Evidence 记录
3. ✅ **Coverage != 0**: 至少一种证据类型（Git/Doc/Code）
4. ✅ **Not High-Risk**: Blind Spot 严重度 < 0.7

## 错误处理

### 索引不存在
```json
{
  "ok": false,
  "data": null,
  "error": "BrainOS index not found. Build index first."
}
```

### 缺少必需参数
HTTP 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["query", "prefix"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## 测试方法

### 1. 快速测试（推荐）
```bash
# 确保 WebUI 正在运行
python -m agentos.cli.webui

# 运行 curl 测试脚本
./test_autocomplete_curl.sh
```

### 2. 完整测试套件
```bash
# 确保 WebUI 正在运行
python -m agentos.cli.webui

# 运行 Python 测试
python test_autocomplete_api.py
```

### 3. 手动测试
```bash
# 基本测试
curl "http://localhost:5000/api/brain/autocomplete?prefix=task" | python3 -m json.tool

# 验证过滤
curl "http://localhost:5000/api/brain/autocomplete?prefix=file&limit=3" | python3 -m json.tool
```

## 实现文件

| 文件 | 行数 | 说明 |
|------|------|------|
| `agentos/webui/api/brain.py` | 677-785 | 新增 autocomplete 端点 |
| `agentos/webui/api/brain.py` | 27-38 | 导入语句更新 |
| `agentos/webui/api/brain.py` | 1-18 | 文档字符串更新 |

## 日志输出示例

```
INFO - Autocomplete request: prefix='task', limit=10, entity_types='None', include_warnings=False
DEBUG - Parsed entity types: None
INFO - Autocomplete completed: 5 suggestions (15 filtered out of 20 total)
```

## 性能特性

- ⚡ **快速查询**: 利用 SQLite 索引进行前缀匹配
- 🔒 **连接管理**: 每个请求独立连接，确保线程安全
- 📊 **智能过滤**: 认知过滤器高效筛选安全实体
- 🎯 **限制控制**: 支持 1-50 条结果限制，防止过载

## 下一步

✅ **Task 2 已完成**

➡️ **Task 3**: 前端集成（IntentWorkbenchView.js autocomplete 组件）

---

**快速启动**:
```bash
# 1. 启动 WebUI
python -m agentos.cli.webui

# 2. 测试端点
curl "http://localhost:5000/api/brain/autocomplete?prefix=task"

# 3. 验证通过 ✅
```
