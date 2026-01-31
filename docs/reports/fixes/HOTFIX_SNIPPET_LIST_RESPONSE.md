# Hotfix: Snippet List Response Format

**Issue**: Snippet 列表不显示
**Date**: 2026-01-28
**Status**: ✅ Fixed

---

## 问题描述

### 症状
用户保存了代码片段后，Snippets 列表页面不显示任何内容。

### 错误信息
```
GET http://127.0.0.1:8080/api/snippets?limit=1000 422 (Unprocessable Content)
```

---

## 根本原因

### 问题 1: API 参数验证过严
**文件**: `agentos/webui/api/snippets.py:176`

API 限制 `limit` 参数最大值为 200，但前端请求了 1000。

```python
# Before:
limit: int = Query(50, ge=1, le=200, description="Max results")
```

### 问题 2: API 响应格式不匹配 ⭐ **主要问题**
**文件**: `agentos/webui/api/snippets.py:176-258`

**后端返回**:
```json
[
  { "id": "...", "title": "...", ... },
  { "id": "...", "title": "...", ... }
]
```

**前端期望**:
```json
{
  "snippets": [
    { "id": "...", "title": "...", ... }
  ]
}
```

**前端代码** (SnippetsView.js:303):
```javascript
this.snippets = response.data.snippets || [];
```

前端期望 `response.data.snippets`，但 API 直接返回数组，导致 `response.data.snippets` 为 `undefined`，列表为空。

---

## 修复方案

### Fix 1: 放宽 limit 参数限制

**文件**: `agentos/webui/api/snippets.py:176`

```python
# After:
limit: int = Query(50, ge=1, le=10000, description="Max results")
```

**理由**: 前端需要获取所有 snippets 来提取 tags 和 languages，1000 是合理的上限。

---

### Fix 2: 修改 API 响应格式 ⭐ **关键修复**

#### 步骤 1: 添加响应模型

**文件**: `agentos/webui/api/snippets.py:84`

```python
class SnippetListResponse(BaseModel):
    """Response for list snippets"""
    snippets: List[SnippetSummary]
```

#### 步骤 2: 修改返回类型

**文件**: `agentos/webui/api/snippets.py:176`

```python
# Before:
) -> List[SnippetSummary]:

# After:
) -> SnippetListResponse:
```

#### 步骤 3: 包装返回值

**文件**: `agentos/webui/api/snippets.py:258`

```python
# Before:
return summaries

# After:
return SnippetListResponse(snippets=summaries)
```

---

## 验证修复

### 1. 重启服务器

```bash
# 停止旧服务器
pkill -f "uvicorn agentos.webui.app:app"

# 启动新服务器
source .venv/bin/activate
uvicorn agentos.webui.app:app --host 127.0.0.1 --port 8080 --log-level warning
```

### 2. 运行测试脚本

```bash
python3 test_snippet_list_fix.py
```

**期望输出**:
```
Testing Snippets List API format...
Status: 200
Response keys: dict_keys(['snippets'])
✅ Response has 'snippets' key
✅ Number of snippets: X
✅ Sample snippet keys: dict_keys(['id', 'title', 'language', 'tags', 'created_at', 'code_preview'])
```

### 3. 浏览器测试

1. 刷新 http://localhost:8080
2. 导航到 Snippets 视图
3. 验证已保存的 snippets 正确显示
4. 创建新 snippet
5. 验证新 snippet 立即出现在列表中

---

## API 响应对比

### Before (错误)
```bash
curl http://localhost:8080/api/snippets?limit=10
```

**返回**:
```json
[
  {
    "id": "abc-123",
    "title": "Test Snippet",
    "language": "javascript",
    "tags": ["test"],
    "created_at": 1706484000,
    "code_preview": "console.log('hello')"
  }
]
```

**前端处理**:
```javascript
// response.data 是数组 [...]
// response.data.snippets 是 undefined ❌
this.snippets = response.data.snippets || [];  // 结果: []
```

---

### After (正确) ✅
```bash
curl http://localhost:8080/api/snippets?limit=10
```

**返回**:
```json
{
  "snippets": [
    {
      "id": "abc-123",
      "title": "Test Snippet",
      "language": "javascript",
      "tags": ["test"],
      "created_at": 1706484000,
      "code_preview": "console.log('hello')"
    }
  ]
}
```

**前端处理**:
```javascript
// response.data 是对象 { snippets: [...] }
// response.data.snippets 是数组 [...] ✅
this.snippets = response.data.snippets || [];  // 结果: [snippet1, snippet2, ...]
```

---

## 影响范围

### 修改的文件 (1)
- `agentos/webui/api/snippets.py`
  - 第 84 行: 添加 `SnippetListResponse` 模型
  - 第 176 行: 修改 `limit` 参数上限 (200 → 10000)
  - 第 176 行: 修改返回类型 (`List[SnippetSummary]` → `SnippetListResponse`)
  - 第 258 行: 包装返回值 (`return summaries` → `return SnippetListResponse(snippets=summaries)`)

### 影响的端点
- `GET /api/snippets` - Snippets 列表查询

### 不影响的端点
- `POST /api/snippets` - 创建 snippet
- `GET /api/snippets/{id}` - 获取单个 snippet
- `PATCH /api/snippets/{id}` - 更新 snippet
- `DELETE /api/snippets/{id}` - 删除 snippet
- `POST /api/snippets/{id}/preview` - 创建预览
- `POST /api/snippets/{id}/materialize` - 物化为任务

---

## 前后端契约

### API 响应格式标准

为保持一致性，所有列表类 API 应返回包装对象：

```typescript
// 标准列表响应格式
{
  "items_name": [
    { /* item 1 */ },
    { /* item 2 */ }
  ],
  "total"?: number,      // 可选: 总数
  "page"?: number,       // 可选: 当前页
  "page_size"?: number   // 可选: 页大小
}
```

**示例**:
- Snippets: `{ snippets: [...] }`
- Tasks: `{ tasks: [...] }`
- Sessions: `{ sessions: [...] }`

---

## 经验教训

### 1. 前后端契约要明确

在实施 Task 6-7（前端集成）时，前端代码假设 API 返回对象格式，但后端返回数组格式，导致不匹配。

**建议**:
- API 设计时先定义响应模型
- 前后端同步确认数据契约
- 使用 TypeScript 类型定义确保一致性

### 2. FastAPI 返回类型很重要

```python
# 返回 List[Model] → JSON: [...]
async def func() -> List[Model]:
    return [model1, model2]

# 返回 ResponseModel → JSON: { "field": [...] }
async def func() -> ResponseModel:
    return ResponseModel(field=[model1, model2])
```

### 3. 测试覆盖前后端集成

E2E 测试验证了后端逻辑，但没有测试前端如何解析响应。

**建议**:
- 添加前后端集成测试
- 测试实际的 HTTP 响应格式
- 验证前端能正确解析响应

---

## 状态

- ✅ Bug 已识别
- ✅ 修复已实施
- ✅ 测试脚本已创建
- ⏳ 等待服务器重启验证

---

**修复人员**: Claude Agent
**修复时间**: 2026-01-28
**文档版本**: v1.0
