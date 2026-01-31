# Refresh Endpoint Quick Reference

## Task #22: POST /api/providers/refresh

### 端点信息

- **URL**: `/api/providers/refresh`
- **方法**: `POST`
- **Content-Type**: `application/json`
- **状态码**: `200 OK`

### 用法

#### 1. 刷新所有 providers

```bash
curl -X POST http://localhost:8000/api/providers/refresh
```

**响应**:
```json
{
  "status": "refresh_triggered",
  "scope": "all",
  "message": "All caches cleared, next status request will refresh"
}
```

#### 2. 刷新单个 provider

```bash
curl -X POST http://localhost:8000/api/providers/refresh?provider_id=ollama
```

**响应**:
```json
{
  "status": "refresh_triggered",
  "provider_id": "ollama",
  "message": "Cache cleared, next status request will refresh"
}
```

### 工作原理

1. **清除缓存**: 调用 `StatusStore.invalidate_provider()` 或 `invalidate_all_providers()`
2. **立即返回**: 返回 202 Accepted 语义（操作已接受）
3. **延迟探测**: 下次调用 `GET /api/providers/status` 时重新探测

### 前端集成

```javascript
// ProvidersView.js
async refreshStatus() {
    // 1. 触发刷新（清除缓存）
    await this.apiClient.post('/providers/refresh');

    // 2. 等待 1 秒
    setTimeout(async () => {
        // 3. 重新加载状态（触发探测）
        await this.loadInstances();
    }, 1000);
}
```

### 日志输出

```
INFO: Triggered refresh for all providers
INFO: Triggered refresh for provider: ollama
DEBUG: Invalidated cache for provider: ollama
DEBUG: Invalidated all provider caches (3 entries)
```

### 设计哲学

- **最小侵入**: 复用现有 StatusStore 缓存机制
- **异步语义**: 清除缓存 ≠ 立即探测
- **简单高效**: 避免复杂的后台任务调度

### 与其他端点的关系

```
POST /refresh          # 清除缓存
  ↓
GET /status            # 重新探测（缓存失效时）
  ↓
GET /{id}/models       # 获取模型（依赖 status）
```

### 典型场景

1. **用户手动刷新**: 点击 "Refresh All" 按钮
2. **Provider 启动后**: 启动 Ollama 后立即刷新状态
3. **配置变更后**: 修改 models 目录后刷新
4. **故障恢复**: Provider 恢复后手动刷新

### 性能考量

- **缓存清除**: < 1ms（内存操作）
- **实际探测**: 由 `GET /status` 触发（1-2s，取决于 provider 数量）
- **推荐间隔**: 至少 2 秒（避免过度探测）

### 错误处理

```javascript
try {
    await apiClient.post('/providers/refresh');
} catch (error) {
    Toast.error('Failed to refresh status');
    console.error(error);
}
```

### 测试命令

```bash
# 测试刷新所有
curl -v -X POST http://localhost:8000/api/providers/refresh

# 测试刷新单个
curl -v -X POST http://localhost:8000/api/providers/refresh?provider_id=ollama

# 验证效果（应看到新的探测）
curl http://localhost:8000/api/providers/status
```

### 相关文件

- Backend: `agentos/webui/api/providers.py` (line ~253)
- StatusStore: `agentos/core/status_store.py` (line ~168)
- Frontend: `agentos/webui/static/js/views/ProvidersView.js` (line ~1671)

---

**实施完成**: 2026-01-29
**任务**: Task #22: P0.4补充 - 添加 refresh 端点
