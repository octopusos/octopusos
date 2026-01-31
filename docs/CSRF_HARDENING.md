# CSRF 硬校验加固说明

## 概述

本次加固实现了"硬拒绝"逻辑，确保即使前端遗漏 CSRF token 也无法绕过后端保护。

## 实施内容

### 1. 浏览器来源检测 (`_is_browser_request`)

新增方法检测请求是否来自浏览器：
- 检查 `Accept` header 是否包含 `text/html`
- 检查 `X-Requested-With` header（AJAX 请求标识）
- 检查是否携带 Cookies

### 2. 强制校验逻辑

在 `dispatch()` 方法中增强校验：

```python
# 浏览器来源的 API 请求必须有 CSRF token
if self.enforce_for_api and is_api_route and self._is_browser_request(request):
    request_token = self._get_request_token(request)

    if not self._validate_token(request, request_token):
        # 硬拒绝，返回 403
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "error_code": "CSRF_TOKEN_REQUIRED",
                "message": "CSRF token is required for this request",
                ...
            }
        )
```

### 3. API 白名单

新增 `api_whitelist` 配置，以下端点无需 CSRF token：
- `/api/health` - 健康检查
- `/api/csrf-token` - 获取 CSRF token 本身

### 4. 配置选项

新增 `enforce_for_api` 参数（默认为 `True`）：
- `True`: 对 API 端点强制校验 CSRF token
- `False`: 保持原有的宽松校验逻辑（向后兼容）

### 5. 增强日志记录

拒绝请求时记录详细信息：
```python
logger.warning(
    f"CSRF protection blocked request: "
    f"path={request.url.path}, method={request.method}, "
    f"has_token={bool(request_token)}, "
    f"client_ip={request.client.host if request.client else 'unknown'}"
)
```

## 错误响应格式

被拒绝的请求返回统一的 ErrorEnvelope 格式：

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
    },
    "timestamp": "2026-01-31T12:34:56.789Z"
}
```

## 使用方式

### 默认配置（推荐）

```python
from agentos.webui.middleware.csrf import add_csrf_protection

# 启用强制校验（默认）
add_csrf_protection(app)
```

### 自定义配置

```python
# 禁用强制校验（向后兼容）
add_csrf_protection(app, enforce_for_api=False)

# 添加额外的白名单路径
add_csrf_protection(
    app,
    exempt_paths=["/health", "/api/health", "/static/", "/custom/path/"]
)
```

## 测试验证

使用提供的测试脚本验证：

```bash
# 启动服务器
python -m agentos.webui.app

# 运行测试（在另一个终端）
python test_csrf_hardening.py
```

测试覆盖：
1. ✅ 无 token 的 API 请求返回 403
2. ✅ 白名单路由正常工作
3. ✅ 错误信息清晰可调试
4. ⚠️  有效 token 的请求通过（需要通过 WebUI 测试）

## 安全影响

### 加固前
- 前端遗漏 CSRF token → 请求仍可能成功
- 依赖前端开发者记住添加 token

### 加固后
- 前端遗漏 CSRF token → 请求被硬拒绝（403）
- 后端强制校验，无法绕过
- 清晰的错误信息帮助调试

## 注意事项

1. **向后兼容**：通过 `enforce_for_api=False` 可以禁用强制校验
2. **性能影响**：浏览器检测逻辑非常轻量，性能影响可忽略
3. **调试友好**：403 响应包含详细的调试信息
4. **日志记录**：所有被拒绝的请求都会记录到日志

## 相关文件

- `/agentos/webui/middleware/csrf.py` - CSRF 中间件实现
- `/test_csrf_hardening.py` - 测试脚本
- `/docs/CSRF_HARDENING.md` - 本文档

## 后续步骤

1. ✅ 后端硬校验加固完成
2. ⬜ 前端批量修复 60 处未保护请求
3. ⬜ 添加 Origin/Referer 同源检查
4. ⬜ 极高风险端点额外保护
5. ⬜ 全面测试验证
6. ⬜ 建立自动化防回归机制
