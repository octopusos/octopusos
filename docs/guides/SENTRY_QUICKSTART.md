# Sentry Release Health - 快速开始

## ✅ 已完成的配置

### 1. **前端配置** (index.html)
- ✅ Sentry Browser SDK (v8.46.0)
- ✅ Auto Session Tracking
- ✅ Performance Monitoring (100%)
- ✅ Session Replay (10% normal, 100% error)
- ✅ Error Tracking

### 2. **后端配置** (app.py)
- ✅ Sentry Python SDK
- ✅ FastAPI Integration
- ✅ Auto Session Tracking (request-mode)
- ✅ Performance Monitoring (100%)
- ✅ Profiling (100%)
- ✅ Error Tracking

---

## 🚀 启动步骤

### 1. 重启 WebUI 服务器

```bash
# 停止当前服务器 (Ctrl+C)
# 重新启动
agentos webui start
```

### 2. 访问页面

```bash
# 打开浏览器
http://localhost:8080/
```

### 3. 检查 Sentry 初始化

**前端**: 打开浏览器控制台,应该看到:
```
✓ Sentry initialized: development agentos-webui@0.3.2
```

**后端**: 查看服务器日志,应该看到:
```
INFO: Sentry initialized: agentos-webui@0.3.2 (env: development, traces: 100.0%, profiles: 100.0%, sessions: enabled)
```

---

## 📊 查看 Release Health 数据

### 1. 登录 Sentry

访问: https://sentry.io/organizations/your-org/

### 2. 进入 Releases 页面

路径: **Projects → AgentOS WebUI → Releases**

### 3. 查看版本 `agentos-webui@0.3.2`

点击版本号,查看:
- **Crash Free Sessions** - 无崩溃会话百分比
- **Crash Free Users** - 无崩溃用户百分比
- **Adoption** - 版本采用率
- **Session Chart** - 会话状态分布(Healthy/Errored/Crashed)

---

## 🧪 测试功能

### 测试 1: 正常会话

```bash
# 访问页面,正常浏览
# 在 Sentry 中应该看到 Healthy session
curl http://localhost:8080/
```

### 测试 2: 触发错误

在浏览器控制台执行:
```javascript
// 触发未捕获错误 (Crashed session)
throw new Error("Test crash");

// 或者触发捕获错误 (Errored session)
try {
    throw new Error("Test error");
} catch (e) {
    Sentry.captureException(e);
}
```

### 测试 3: 查看 Issues

在 Sentry 中:
1. 进入 **Issues** 页面
2. 应该看到刚才触发的错误
3. 点击错误查看详细信息(堆栈、环境、Session Replay)

---

## 🔧 环境变量

### 开发环境 (默认)

```bash
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=development
SENTRY_TRACES_SAMPLE_RATE=1.0
SENTRY_PROFILES_SAMPLE_RATE=1.0
```

### 生产环境 (建议)

```bash
SENTRY_ENABLED=true
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1    # 10%
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10%
```

前端采样率在 `index.html` 中修改:
```javascript
tracesSampleRate: 0.1,
replaysSessionSampleRate: 0.01,  // 1%
```

---

## 📈 关键指标

| 指标 | 含义 | 目标 |
|------|------|------|
| **Crash Free Sessions** | 无崩溃会话百分比 | ≥ 99% |
| **Crash Free Users** | 无崩溃用户百分比 | ≥ 99.5% |
| **Adoption** | 最新版本采用率 | ≥ 80% |
| **Session Count** | 总会话数 | 监控增长 |

---

## 🚨 告警设置

### 1. 创建 Crash Rate Alert

在 Sentry 中:
1. **Alerts → Create Alert → Crash Rate**
2. 设置条件:
   - **Crash Free Sessions** < 95%
   - 或 **Crash Free Users** < 98%
3. 设置通知渠道(Email/Slack/PagerDuty)

### 2. 创建 Issue Alert

1. **Alerts → Create Alert → Issue**
2. 设置条件:
   - 新错误出现
   - 错误频率增加 100%
3. 设置通知渠道

---

## 📝 注意事项

### 1. Health Check 过滤

Health check 请求已被过滤,不会创建 session:
- ✅ `/health`
- ✅ `/api/health`

### 2. Session 模式

- **前端**: Application-mode (每次页面加载 = 1 session)
- **后端**: Request-mode (每个 API 请求 = 1 session)

### 3. 数据延迟

Session 数据可能有 5-10 分钟延迟,耐心等待。

---

## 📚 更多信息

详细文档: [SENTRY_RELEASE_HEALTH.md](./SENTRY_RELEASE_HEALTH.md)

---

**快速开始完成时间**: 2026-01-28
