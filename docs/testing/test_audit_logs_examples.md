# Audit Middleware 日志示例

## 概述
本文档展示 audit middleware 在不同场景下的日志输出，验证 best-effort 审计策略的实现。

## 1. 成功场景 - DEBUG 级别日志

### 正常审计记录成功
```
2026-01-29 17:46:08,284 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=system, event=task_started, status=success, duration=1ms
```

**特点**：
- 日志级别：DEBUG
- 包含关键信息：task_id、event_type、status、duration
- 不干扰生产环境日志（DEBUG 默认关闭）

### 失败请求的审计（业务层失败）
```
2026-01-29 17:46:08,963 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=system, event=task_started, status=failed, duration=1ms
```

**特点**：
- 即使业务请求失败（500），审计仍然记录成功
- status=failed 标识业务失败，但审计本身成功

## 2. 超时场景 - WARNING 级别日志

### 审计系统繁忙导致超时
```
2026-01-29 17:46:08,857 - agentos.webui.middleware.audit - WARNING - Audit timeout (system busy, audit dropped): task=None, path=/api/tasks/test123/start, error=Queue full
```

**特点**：
- 日志级别：WARNING（不是 ERROR）
- 明确标注 "audit dropped" 表示审计被丢弃
- 包含上下文：task_id、path、具体错误信息
- 业务请求不受影响，继续正常返回

**触发条件**：
- SQLiteWriter 队列满（默认 1000）
- 数据库写入超时（默认 30s）

## 3. 异常场景 - WARNING 级别日志

### 审计服务内部异常
```
2026-01-29 17:46:08,748 - agentos.webui.middleware.audit - WARNING - Audit failed (best-effort, dropped): task=None, path=/api/tasks/test123/start, error=Database error
```

**特点**：
- 日志级别：WARNING（不是 ERROR）
- 明确标注 "best-effort, dropped"
- 包含完整上下文信息

### DEBUG 模式下的详细堆栈
```
2026-01-29 17:46:08,748 - agentos.webui.middleware.audit - DEBUG - Audit failure details:
Traceback (most recent call last):
  File "/Users/pangge/PycharmProjects/AgentOS/agentos/webui/middleware/audit.py", line 290, in _record_audit
    audit_service.record_operation(
    ...
Exception: Database error
```

**特点**：
- 仅在 DEBUG 模式输出完整堆栈
- 使用 `logger.isEnabledFor(logging.DEBUG)` 条件判断
- 生产环境不会输出堆栈（避免日志泛滥）

## 4. 并发场景 - 批量日志

### 50 个并发请求的审计日志
```
2026-01-29 17:46:08,284 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=task0, event=task_started, status=success, duration=10ms
2026-01-29 17:46:08,286 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=task1, event=task_started, status=success, duration=12ms
2026-01-29 17:46:08,288 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=task2, event=task_started, status=success, duration=14ms
...
2026-01-29 17:46:08,539 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=task49, event=task_started, status=success, duration=135ms
```

**性能指标**：
- 总时间：157.02ms（50 个请求）
- 平均耗时：78.97ms/请求
- 并发处理：无阻塞（SQLiteWriter 内部串行化）

**关键观察**：
- 每个请求的 duration 逐渐增加（10ms → 135ms）
- 说明审计写入是串行的，但**不阻塞业务响应**
- 业务请求在 1-2ms 内返回，审计异步完成

## 5. 降级场景 - audit_service 内部降级

### Task 不存在时的降级日志
```
2026-01-29 17:46:08,284 - agentos.core.task.audit_service - WARNING - Audit dropped: task_id=system not found in tasks table. This is expected if task creation failed or audit arrived before task. Event: task_started
2026-01-29 17:46:08,284 - agentos.core.task.audit_service - INFO - Recorded audit: task=system, repo=None, operation=post, status=success
```

**特点**：
- TaskAuditService 内部降级逻辑（Task #5）
- WARNING 日志说明原因：task 不存在
- 仍然记录审计事件到 task_events 表（降级）

## 6. 不审计场景 - GET 请求

### GET 请求无审计日志
```
✅ GET request completed in 1.33ms
✅ No audit logs should appear (GET is not audited)
```

**特点**：
- GET、HEAD、OPTIONS 等读操作不触发审计
- 减少日志量，只审计写操作

## 7. 错误级别对比表

| 场景 | 原日志级别 | 新日志级别 | 改进说明 |
|-----|----------|----------|---------|
| 审计成功 | DEBUG | DEBUG | 无变化，避免生产日志泛滥 |
| 审计超时 | ERROR | WARNING | 降级为 WARNING，不是系统错误 |
| 审计异常 | ERROR | WARNING | 降级为 WARNING，best-effort 策略 |
| 详细堆栈 | 总是输出 | 仅 DEBUG 模式 | 条件输出，减少噪音 |

## 8. 日志聚合建议

### 监控告警规则
```yaml
# 审计超时告警（系统繁忙）
- name: audit_timeout_rate
  query: 'agentos.webui.middleware.audit WARNING "Audit timeout"'
  threshold: "> 10% in 5min"
  severity: warning

# 审计失败告警（可能有 bug）
- name: audit_failure_rate
  query: 'agentos.webui.middleware.audit WARNING "Audit failed"'
  threshold: "> 5% in 5min"
  severity: error
```

### 日志采样策略
- **DEBUG 日志**：生产环境关闭，开发/测试开启
- **WARNING 日志**：保留，用于监控审计健康度
- **INFO 日志**：TaskAuditService 层输出，记录成功率

## 9. 性能影响分析

### 测试场景：50 并发请求
- **业务响应时间**：1-2ms（不受审计影响）
- **审计完成时间**：10-135ms（异步完成，串行写入）
- **系统吞吐量**：不受影响（best-effort 策略）

### 关键结论
1. ✅ 审计失败不会导致业务请求失败
2. ✅ 审计延迟不会阻塞业务响应
3. ✅ 高并发场景下审计自动串行化（SQLiteWriter）
4. ✅ 超时/失败时审计被丢弃，不影响系统稳定性

## 10. 与其他组件的日志协同

### 完整调用链日志
```
# 1. Middleware 接收请求
2026-01-29 17:46:08,276 - agentos.webui.middleware.audit - DEBUG - Processing request: POST /api/tasks/test123/start

# 2. 业务逻辑执行（假设）
2026-01-29 17:46:08,277 - agentos.core.task.service - INFO - Task test123 started

# 3. Writer 写入数据库（假设）
2026-01-29 17:46:08,278 - agentos.core.db.writer - DEBUG - Write operation queued: tasks UPDATE

# 4. Audit Service 记录审计
2026-01-29 17:46:08,284 - agentos.core.task.audit_service - INFO - Recorded audit: task=test123, repo=None, operation=post, status=success

# 5. Middleware 完成审计
2026-01-29 17:46:08,284 - agentos.webui.middleware.audit - DEBUG - Recorded audit: task=test123, event=task_started, status=success, duration=1ms
```

**日志链特点**：
- 每个组件独立日志
- 通过 task_id、timestamp 关联
- 降级逻辑在各层独立处理

## 总结

### 改进前 vs 改进后

| 方面 | 改进前 | 改进后 |
|-----|-------|-------|
| 异常处理 | 笼统的 Exception catch | 区分 TimeoutError 和 Exception |
| 日志级别 | 全部 ERROR | TimeoutError=WARNING, Exception=WARNING |
| 日志信息 | 简单错误消息 | 包含 task_id、path、错误类型 |
| 堆栈输出 | 总是输出 | 仅 DEBUG 模式输出 |
| 语义表达 | "Failed to record audit" | "Audit timeout (system busy, audit dropped)" 或 "Audit failed (best-effort, dropped)" |
| 监控友好性 | 难以区分超时和错误 | 可精确监控不同失败类型 |

### 最佳实践总结
1. ✅ **Best-effort 策略**：审计失败不影响业务
2. ✅ **分级日志**：WARNING 用于审计失败，DEBUG 用于成功
3. ✅ **上下文丰富**：日志包含 task_id、path、error
4. ✅ **条件堆栈**：仅开发环境输出详细堆栈
5. ✅ **语义清晰**：日志消息明确表达 "audit dropped"
6. ✅ **监控友好**：可基于日志建立告警规则
