# CSRF 硬校验加固 - 快速参考

## 一句话总结
后端现在会硬拒绝所有来自浏览器且缺少 CSRF token 的 API 请求（返回 403）。

## 关键变更

### 行为变更
```
加固前: 缺少 token → 可能通过（取决于实现）
加固后: 缺少 token → 硬拒绝 403 CSRF_TOKEN_REQUIRED
```

### 错误响应
```json
{
    "ok": false,
    "error_code": "CSRF_TOKEN_REQUIRED",
    "message": "CSRF token is required for this request",
    "details": {
        "hint": "Include X-CSRF-Token header with a valid token",
        "endpoint": "/api/sessions",
        "method": "POST",
        "reason": "Browser-initiated API requests must include CSRF token"
    }
}
```

## 配置选项

### 默认配置（推荐）
```python
add_csrf_protection(app)
# 等同于
add_csrf_protection(app, enforce_for_api=True)
```

### 禁用强制校验（不推荐）
```python
add_csrf_protection(app, enforce_for_api=False)
```

### 自定义白名单
```python
add_csrf_protection(
    app,
    exempt_paths=["/health", "/api/health", "/static/", "/custom/"]
)
```

## API 白名单

以下端点无需 CSRF token：
- `/api/health` - 健康检查
- `/api/csrf-token` - 获取 token

## 浏览器请求判定标准

满足以下任一条件即判定为浏览器请求：
1. `Accept` header 包含 `text/html`
2. 有 `X-Requested-With` header
3. 请求携带 Cookies

## 测试方法

### 快速测试
```bash
# 启动服务器
python -m agentos.webui.app

# 运行测试（新终端）
python test_csrf_hardening.py
```

### 手动测试
```bash
# 应该被拒绝（有 Cookie 模拟浏览器）
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Cookie: test=value" \
  -d '{"title":"test"}'

# 应该返回 403 + CSRF_TOKEN_REQUIRED
```

## 日志示例

被拒绝的请求会记录：
```
WARNING - CSRF protection blocked request:
  path=/api/sessions, method=POST,
  has_token=False, client_ip=127.0.0.1
```

## 影响范围

### 受影响的请求
- ✅ POST/PUT/PATCH/DELETE 到 `/api/*` 且来自浏览器

### 不受影响的请求
- ❌ GET/HEAD/OPTIONS 请求（安全方法）
- ❌ 非 `/api/*` 路径
- ❌ 非浏览器请求（如 CLI、脚本）
- ❌ 白名单路径

## 前端修复指南

### 正确的请求方式
```javascript
// 获取 CSRF token（从 cookie）
const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1];

// 发送请求时包含 token
fetch('/api/sessions', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken  // 关键：必须包含
    },
    body: JSON.stringify({title: 'test'})
});
```

### 使用 CSRFHandler（推荐）
```javascript
// 使用项目提供的 CSRFHandler
import { CSRFHandler } from './csrf-handler.js';

// 自动处理 CSRF token
const response = await CSRFHandler.fetch('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({title: 'test'})
});
```

## 故障排查

### 问题：收到 403 CSRF_TOKEN_REQUIRED
**原因**: 请求缺少或包含无效的 CSRF token

**解决方法**:
1. 检查请求是否包含 `X-CSRF-Token` header
2. 验证 token 值是否正确（从 `csrf_token` cookie 获取）
3. 检查 session 是否有效

### 问题：白名单路径仍被拒绝
**原因**: 路径未正确匹配白名单

**解决方法**:
1. 检查路径是否以白名单前缀开头
2. 添加自定义白名单路径到配置

### 问题：非浏览器请求被拒绝
**原因**: 请求携带了 Cookies 或特定 headers

**解决方法**:
1. 移除不必要的 Cookies
2. 不要设置 `Accept: text/html`
3. 添加路径到白名单

## 文件位置

- **中间件实现**: `/agentos/webui/middleware/csrf.py`
- **测试脚本**: `/test_csrf_hardening.py`
- **详细文档**: `/docs/CSRF_HARDENING.md`
- **变更总结**: `/docs/CSRF_HARDENING_SUMMARY.md`
- **本快速参考**: `/docs/CSRF_HARDENING_QUICK_REF.md`

## 相关任务

- ✅ #5: 后端 CSRF 硬校验加固（已完成）
- ⬜ #7: 前端批量修复 60 处未保护请求
- ⬜ #6: 添加 Origin/Referer 同源检查
- ⬜ #8: 极高风险端点额外保护
- ⬜ #10: 全面测试验证
- ⬜ #11: 建立自动化防回归机制
