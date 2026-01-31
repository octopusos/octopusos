# Sentry Release Health 配置指南

## 📋 概述

AgentOS WebUI 已集成 Sentry Release Health 功能,用于监控应用的健康状况和发布质量。

## 🎯 功能特性

### 1. **Error Tracking (错误追踪)**
- 自动捕获前端和后端的未处理错误
- 捕获 Promise rejections
- 详细的错误堆栈和上下文信息
- 错误去重和聚合

### 2. **Performance Monitoring (性能监控)**
- 追踪 API 请求响应时间
- 监控页面加载性能
- 识别慢查询和性能瓶颈
- 分布式追踪(Distributed Tracing)

### 3. **Release Health (发布健康)**
- **Session Tracking** - 自动追踪用户会话
- **Crash-Free Sessions** - 无崩溃会话百分比
- **Crash-Free Users** - 无崩溃用户百分比
- **Adoption Rate** - 发布版本采用率
- **Session Status** - 会话状态(Healthy/Errored/Crashed/Abnormal)

### 4. **Session Replay (会话回放)**
- 记录用户交互的视频回放
- 自动捕获错误发生时的上下文
- 10% 正常会话采样
- 100% 错误会话采样

---

## 🏗️ 架构说明

### 前端 (Browser SDK)

**Session 定义**: 对于 Web 应用,每次页面加载创建一个 session。对于 SPA(单页应用),每次导航变化创建新 session。

**配置位置**: `agentos/webui/templates/index.html`

```javascript
Sentry.init({
    dsn: "...",
    environment: "development",
    release: "agentos-webui@0.3.2",

    // Auto Session Tracking
    autoSessionTracking: true,

    // Performance Monitoring
    tracesSampleRate: 1.0,  // 100% in dev

    // Session Replay
    replaysSessionSampleRate: 0.1,    // 10% normal sessions
    replaysOnErrorSampleRate: 1.0,    // 100% error sessions
});
```

### 后端 (Python SDK)

**Session 定义**: 对于 FastAPI 应用,每个 HTTP 请求对应一个 session(server-mode/request-mode)。

**配置位置**: `agentos/webui/app.py`

```python
sentry_sdk.init(
    dsn="...",
    environment="development",
    release="agentos-webui@0.3.2",

    # Auto Session Tracking (request-mode)
    auto_session_tracking=True,
    session_mode="request",

    # Performance Monitoring
    traces_sample_rate=1.0,  # 100% in dev
    profiles_sample_rate=1.0,  # 100% in dev
)
```

---

## 📊 Release Health 指标

### 1. **Sessions (会话)**

| 类型 | 描述 |
|------|------|
| **Active Sessions** | 最近 24 小时内启动的会话数 |
| **Active Users** | 最近 24 小时内至少启动一次应用的用户数 |
| **Crash Free Sessions** | 未以崩溃结束的会话百分比 |
| **Crash Free Users** | 未经历崩溃的用户百分比 |

### 2. **Session Status (会话状态)**

| 状态 | 描述 | Sentry Issue |
|------|------|--------------|
| **Healthy** | 正常结束,无错误 | ❌ 无 |
| **Errored** | 正常结束,但有处理的错误 | ✅ 有 |
| **Crashed** | 未处理的错误或崩溃 | ✅ 有 |
| **Abnormal** | 异常终止(电池耗尽、强制关闭等) | ❌ 无 |

### 3. **Adoption (采用率)**

- **Session Adoption** - 特定版本在最近 24 小时的会话数占比
- **User Adoption** - 特定版本在最近 24 小时的用户数占比

**Adoption Stages**:
- **Adopted** - 占比 ≥ 10%
- **Low Adoption** - 占比 < 10%
- **Replaced** - 曾经 ≥ 10%,现在 < 10%

---

## 🔧 环境变量配置

### 后端环境变量

```bash
# 启用/禁用 Sentry
SENTRY_ENABLED=true

# Sentry DSN (项目密钥)
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx

# 环境 (development/staging/production)
SENTRY_ENVIRONMENT=development

# 发布版本
SENTRY_RELEASE=agentos-webui@0.3.2

# Performance Monitoring 采样率 (0.0 - 1.0)
SENTRY_TRACES_SAMPLE_RATE=1.0    # 100% in dev, 0.1 in prod

# Profiling 采样率 (0.0 - 1.0)
SENTRY_PROFILES_SAMPLE_RATE=1.0  # 100% in dev, 0.1 in prod
```

### 前端配置

前端配置硬编码在 `index.html` 中,但可以通过模板变量注入:

```html
<script>
    const SENTRY_ENABLED = true;
    const SENTRY_DSN = "...";
    const SENTRY_ENVIRONMENT = "{{ sentry_environment }}";  // 从后端传递
    const SENTRY_RELEASE = "agentos-webui@0.3.2";
</script>
```

---

## 📈 在 Sentry 中查看 Release Health

### 1. **Releases 页面**

访问: `https://sentry.io/organizations/your-org/releases/`

可以看到:
- 所有发布版本列表
- Crash Free Sessions/Users 百分比
- Adoption 采用率
- Session 总数

### 2. **Release Details 页面**

点击某个版本,查看:
- **Overview** - 崩溃率、会话数、采用率趋势图
- **Issues** - 该版本相关的所有错误
- **Commits** - 代码变更(需配置 Git 集成)
- **Sessions** - 会话明细(Healthy/Errored/Crashed/Abnormal)

### 3. **Alerts (告警)**

可以设置:
- **Crash Rate Alerts** - 崩溃率超过阈值时告警
  - 例如: Crash Free Sessions < 95%
  - 例如: Crash Free Users < 98%
- **Issue Alerts** - 新错误或错误频率增加时告警

---

## 🧪 测试 Release Health

### 1. **触发正常会话**

```bash
# 前端: 访问页面,正常浏览
curl http://localhost:8080/

# 后端: 正常 API 请求
curl http://localhost:8080/api/health
```

在 Sentry 中应该看到 **Healthy** 状态的 session。

### 2. **触发 Errored 会话**

```javascript
// 前端: 手动捕获错误
try {
    throw new Error("Test handled error");
} catch (e) {
    Sentry.captureException(e);
}
```

在 Sentry 中应该看到 **Errored** 状态的 session。

### 3. **触发 Crashed 会话**

```javascript
// 前端: 未捕获的错误
throw new Error("Test unhandled error");

// 后端: API 返回 500
# 访问一个会触发错误的 endpoint
```

在 Sentry 中应该看到 **Crashed** 状态的 session,并有对应的 Issue。

---

## 🚀 生产环境建议

### 1. **采样率调整**

```bash
# 生产环境建议值
SENTRY_TRACES_SAMPLE_RATE=0.1      # 10% 性能追踪
SENTRY_PROFILES_SAMPLE_RATE=0.1    # 10% 性能分析
```

前端:
```javascript
tracesSampleRate: 0.1,              // 10% 性能追踪
replaysSessionSampleRate: 0.01,     // 1% 正常会话回放
replaysOnErrorSampleRate: 1.0,      // 100% 错误会话回放
```

### 2. **环境隔离**

- `development` - 开发环境,100% 采样
- `staging` - 测试环境,50% 采样
- `production` - 生产环境,10% 采样

### 3. **PII 数据保护**

后端已启用 `send_default_pii=True`,但可以通过 `before_send` 过滤敏感信息:

```python
def before_send(event, hint):
    # 过滤敏感 URL 参数
    if 'request' in event:
        event['request'].pop('cookies', None)
        # 移除敏感 header
    return event
```

### 4. **Release 版本管理**

建议使用 Git commit SHA 作为 release:

```bash
SENTRY_RELEASE=agentos-webui@$(git rev-parse --short HEAD)
```

---

## 📚 相关文档

- [Sentry Release Health 官方文档](https://docs.sentry.io/product/releases/health/)
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [Sentry JavaScript SDK](https://docs.sentry.io/platforms/javascript/)
- [FastAPI 集成指南](https://docs.sentry.io/platforms/python/guides/fastapi/)

---

## ✅ 验收清单

### 前端

- [ ] Sentry SDK 加载成功
- [ ] 控制台显示 "✓ Sentry initialized"
- [ ] 页面访问创建 session
- [ ] 未捕获错误被记录
- [ ] 性能追踪正常工作

### 后端

- [ ] 启动日志显示 "Sentry initialized"
- [ ] API 请求创建 session
- [ ] 未捕获异常被记录
- [ ] Health check 被过滤(不记录)
- [ ] 性能追踪正常工作

### Sentry Dashboard

- [ ] Releases 页面显示 `agentos-webui@0.3.2`
- [ ] Session 数据正常上报
- [ ] Crash Free Sessions/Users 指标正常
- [ ] Issues 页面显示错误
- [ ] Performance 页面显示事务

---

**实现完成时间**: 2026-01-28
**版本**: agentos-webui@0.3.2
**状态**: ✅ 已启用
