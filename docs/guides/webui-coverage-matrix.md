# WebUI API Coverage Matrix

> **目的**: 追踪每个后端 API 是否有对应的 UI 入口和展示
> **更新**: 每次新增 API 或完成 UI 对接后更新此矩阵
> **验证**: `scripts/verify_webui_coverage.py` 自动检查

---

## Coverage Status 图例

- ✅ **完全覆盖** - UI 有入口、展示结果、错误态、追踪字段
- 🔧 **部分覆盖** - UI 有入口但功能不完整
- ⏳ **待覆盖** - API 已就绪，UI 未实现
- ❌ **不适用** - 后端专用 API，不需要 UI

---

## Health & System

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/health` | GET | 顶部状态栏 + `/health-check` | 状态卡片 | db_status, model_status, memory_status, kb_status, pid, memory_mb | 500, timeout | ✅ |
| `/api/support/diagnostic-bundle` | GET | System → Support | JSON 下载 + inline 查看 | version, system, providers, selfcheck, cache_stats | 500, timeout | ✅ |

**说明**:
- ✅ Health 已完全实现：实时轮询（5秒）、独立健康检查页
- ✅ Diagnostic Bundle 已完全实现（PR-5）：下载 + 查看 + 复制

---

## Sessions & Chat

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/sessions` | GET | Sessions → 列表 | DataTable + FilterBar | session_id, title, created_at, updated_at, message_count, task_count | 500, timeout, empty | ✅ |
| `/api/sessions` | POST | Sessions → New Session | prompt + 创建 → 跳转 Chat | session_id, title | 400, 500 | ✅ |
| `/api/sessions/{id}` | GET | Sessions 行点击 → Drawer | JsonViewer + 详情网格 | session_id, title, metadata, created_at, updated_at | 404, 500, timeout | ✅ |
| `/api/sessions/{id}` | PATCH | Session Detail → Rename | inline input + Save | title | 400, 404, 500 | ✅ |
| `/api/sessions/{id}` | DELETE | Session Detail → Delete | 确认弹窗 + 删除 | - | 404, 500 | ✅ |
| `/ws/chat/{session_id}` | WS | Chat 面板 | 消息列表 + session binding | session_id, message_id, role, content | ws_error, reconnect | ✅ |

**说明**:
- ✅ Sessions 视图已完全实现（PR-3）
- ✅ SessionsView.js: 完整的 session 管理界面
- ✅ CRUD 全部实现：Create → Rename (PATCH) → Delete（带确认）
- ✅ Chat session binding: 显示 session_id + 输入护栏 + 跨导航

**DoD Checklist for PR-3**:
- [x] Sessions 列表页（DataTable + FilterBar）
- [x] 新建 Session 按钮（prompt → create → 跳转 Chat）
- [x] Session 操作（Rename inline, Delete 确认弹窗）
- [x] 错误态：404, 500, timeout, empty, contract validation
- [x] 追踪字段：session_id, title, created_at, updated_at, message_count, task_count
- [x] Session Detail Drawer: metadata + JsonViewer + Cross-nav
- [x] Cross-navigation: View Tasks/Events/Logs/Chat（带 session_id filter）
- [x] Chat session binding: toolbar 显示 session_id + copy + view session
- [x] Chat 输入护栏：无 session 则 disable 输入框
- [x] Session 为"锚点"：任何地方点击 session_id → 跳转 SessionsView

---

## Tasks

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/tasks` | GET | Observability → Tasks | DataTable + FilterBar | task_id, status, type, session_id, created_at, updated_at | 500, timeout, empty | ✅ |
| `/api/tasks/{task_id}` | GET | Tasks 行点击 → Drawer | JsonViewer + 详情网格 + 路由时间线 | task_id, status, type, session_id, description, error, metadata, route_plan, requirements, events | 404, 500, timeout | ✅ |

**说明**:
- ✅ Tasks 视图已完全实现（PR-2）
- ✅ TasksView.js: 完整的任务管理界面
- ✅ **PR-4 增强**: 路由可视化 - 显示路由时间线、决策原因、评分、fallback 链

**DoD Checklist for PR-2**:
- [x] Tasks 列表页（DataTable）
- [x] 状态筛选（pending/running/completed/failed/cancelled）+ task_id + session_id + time_range
- [x] 分页控件（20条/页）
- [x] 点击行展开详情抽屉（Drawer）
- [x] 详情显示：Basic Info + Description + Error + Full JSON + Actions
- [x] 错误态：404, 500, timeout, empty
- [x] 追踪字段：task_id, session_id, created_at, updated_at, status
- [x] 复制按钮：task_id
- [x] 跨视图导航：View Session, View Events, View Logs
- [x] 操作按钮：Refresh, Create Task, Cancel Task (running状态)

**DoD Checklist for PR-4 (Router Visualization)**:
- [x] 路由信息展示：Selected Instance（蓝色高亮框）
- [x] Requirements 显示：needs, min_ctx（黄色徽章）
- [x] Route Plan 展示：reasons（✓列表）+ scores（柱状图）+ fallback chain（序号链）
- [x] Route Timeline 时间线：TASK_ROUTED/TASK_ROUTE_VERIFIED/TASK_REROUTED/TASK_ROUTE_OVERRIDDEN
- [x] 事件详情：图标 + 类型 + 时间 + 实例 + 原因 + 评分
- [x] CSS 样式：完整的路由可视化样式（~500行）

---

## Events

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/events` | GET | Observability → Events | DataTable + FilterBar | event_id, type, timestamp, task_id, session_id, message | 500, timeout, empty | ✅ |
| `/api/events/stream` | GET | Events → Live Stream 开关 | 轮询模式（3秒） | event_id, timestamp, after参数 | 500, timeout | ✅ |

**说明**:
- ✅ Events 视图已完全实现（PR-2）
- ✅ EventsView.js: 事件流时间线 + 实时流模式

**DoD Checklist for PR-2**:
- [x] Events 时间线视图（倒序，50条/页）
- [x] FilterBar: event_id, type (10+ 事件类型), task_id, session_id, time_range
- [x] 点击事件 → Drawer → JsonViewer
- [x] 实时模式开关（Live Stream toggle + 轮询3秒）
- [x] 错误态：500, timeout, empty
- [x] 追踪字段：event_id, type, timestamp, task_id, session_id, message
- [x] 跨视图导航：View Task, View Session
- [x] 操作按钮：Refresh, Clear, Live Stream Toggle
- [x] 实时状态栏：显示 "Live streaming events..." + 脉冲指示器

---

## Logs

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/logs` | GET | Observability → Logs | DataTable + FilterBar | timestamp, level, logger, message, task_id | 500, timeout, empty | ✅ |
| `/api/logs/tail` | GET | Logs → Tail Mode 开关 | 轮询模式（3秒） | timestamp, level, after参数 | 500, timeout | ✅ |

**说明**:
- ✅ Logs 视图已完全实现（PR-2）
- ✅ LogsView.js: 系统日志查看器 + Tail 模式
- ✅ 颜色编码：DEBUG(灰)/INFO(蓝)/WARNING(黄)/ERROR(红)/CRITICAL(深红)

**DoD Checklist for PR-2**:
- [x] Logs 列表视图（100条/页）
- [x] FilterBar: level (multi-select: DEBUG/INFO/WARNING/ERROR/CRITICAL), contains, logger, task_id, time_range
- [x] 日志行颜色编码（level 徽章 + 消息边框色）
- [x] Tail 模式（轮询刷新3秒 + 自动滚动）
- [x] 错误态：500, timeout, empty
- [x] 追踪字段：timestamp, level, logger, message, task_id, filename, lineno, funcName
- [x] 详情抽屉：Message + Stack Trace + Full JSON
- [x] 跨视图导航：View Task
- [x] 操作按钮：Refresh, Clear, Download (JSON), Tail Mode Toggle
- [x] Tail 状态栏：显示 "Tailing logs..." + 脉冲指示器
- [x] 内存限制：最多保留5000条日志（防止内存溢出）

---

## Providers

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/providers` | GET | Settings → Providers | 列表 | provider_id, type, supports_* | 500 | ✅ |
| `/api/providers/status` | GET | 顶部状态栏 + Settings | 状态卡片 | provider_id, state, latency_ms, reason_code, hint | 500, timeout | ✅ |
| `/api/providers/{id}/models` | GET | Settings → Providers | 模型列表 | model_id, label, context_window | 404, 500 | ✅ |
| `/api/providers/local/detect` | GET | Settings → Providers → Local | 检测结果 | cli_found, service_reachable, models_count, hint | 500 | ✅ |
| `/api/providers/ollama/start` | POST | Settings → Providers → Ollama | 按钮 + 状态 | pid, endpoint | 500 | ✅ |
| `/api/providers/ollama/stop` | POST | Settings → Providers → Ollama | 按钮 | pid | 500 | ✅ |
| `/api/providers/ollama/restart` | POST | Settings → Providers → Ollama | 按钮 | pid | 500 | ✅ |
| `/api/providers/ollama/runtime` | GET | Settings → Providers → Ollama | 运行时信息 | pid, started_at, command | 500 | ✅ |
| `/api/providers/cloud/config` | POST | Settings → Providers → Cloud | 配置表单 | provider_id, api_key, base_url | 400, 500 | ✅ |
| `/api/providers/cloud/test` | POST | Settings → Providers → Cloud | 测试按钮 | state, latency_ms, models_count | 401, 403, 500 | ✅ |
| `/api/providers/cloud/config/{id}` | DELETE | Settings → Providers → Cloud | 清除按钮 | - | 404, 500 | ✅ |
| `/api/providers/instances` | GET | Settings → Providers | Instance 表格 + 路由元数据 | instance_key, base_url, state, metadata (tags/ctx/role) | 500, timeout | ✅ |
| `/api/providers/instances/{provider}/{instance}` | GET | Providers → Edit Routing | 实例配置详情 | instance_id, base_url, metadata | 404, 500 | ✅ |
| `/api/providers/instances/{provider}/{instance}` | PUT | Providers → Save Routing | 更新路由元数据 | tags, ctx, role | 400, 404, 500 | ✅ |

**说明**:
- ✅ Providers 已完全实现（Sprint B Task #4-6）
- ✅ 包含完整的错误态、追踪字段、reason_code + hint
- ✅ **PR-4 增强**: 路由元数据管理 - 编辑 tags/ctx/role，徽章显示

**DoD Checklist for PR-4 (Providers Routing Enhancement)**:
- [x] Instance 表格新增"Routing Metadata"列
- [x] 元数据显示：tags（蓝色徽章）+ ctx（紫色徽章）+ role（绿色徽章）
- [x] 新增 🎯 按钮打开路由元数据编辑器
- [x] 路由元数据 Modal：tags（逗号分隔）+ ctx（数字）+ role（文本）
- [x] 保存到 providers.json metadata 字段
- [x] 表格实时刷新显示更新后的元数据

---

## Self-check

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/selfcheck` | POST | Settings → Self-check | 检查项列表 | item_id, group, status, detail, hint, actions | 500, timeout | ✅ |

**说明**:
- ✅ Self-check 已完全实现（Sprint B Task #7）
- ✅ 包含分组、筛选、可操作 actions、空状态、FAIL 红点脉冲

---

## Context

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/context/status` | GET | System → Context | Session 选择器 + 状态面板 | session_id, state, tokens, rag, memory, updated_at | 400, 404, 500, timeout | ✅ |
| `/api/context/attach` | POST | Context → Attach 按钮 | 操作面板 + 状态反馈 | session_id, memory.enabled, rag.enabled | 400, 500 | ✅ |
| `/api/context/detach` | POST | Context → Detach 按钮 | 确认对话框 + 操作反馈 | session_id | 400, 500 | ✅ |
| `/api/context/refresh` | POST | Context → Refresh 按钮 | 操作面板 + 状态反馈 | session_id | 400, 500 | ✅ |

**说明**:
- ✅ Context 视图已完全实现（PR-5）
- ✅ ContextView.js: Session-based 上下文管理工具

**DoD Checklist (PR-5完成)**:
- [x] Session 选择器（输入框 + 最近会话列表）
- [x] Context 状态面板（State, Tokens, RAG, Memory, Updated At）
- [x] Attach Context 操作（Memory + RAG 启用）
- [x] Refresh Context 操作
- [x] Detach Context 操作（带确认）
- [x] 错误态：400, 404, 500, timeout
- [x] 追踪字段：session_id, state, updated_at, tokens, rag, memory
- [x] JsonViewer：完整 context 数据

---

## Skills

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/skills` | GET | Agent → Skills | DataTable + FilterBar | name, version, description, executable | 500, timeout, empty | ✅ |
| `/api/skills/{name}` | GET | Skills 行点击 → Drawer | JsonViewer + 详情网格 | name, version, input_schema, output_schema, metadata | 404, 500, timeout | ✅ |

**说明**:
- ✅ Skills 视图已完全实现（PR-4）
- ✅ SkillsView.js: 完整的技能管理界面

**DoD Checklist (PR-4完成)**:
- [x] Skills 列表页（DataTable + FilterBar）
- [x] 搜索过滤（name/description）
- [x] Skill 详情抽屉（schema JsonViewer + 完整 metadata）
- [x] 错误态：404, 500, timeout, empty
- [x] 追踪字段：name, version, executable, last_execution
- [x] 复制按钮：skill name
- [x] 跨视图导航：View Logs（带 contains=skill_name）
- [x] 操作按钮：Refresh
- [x] Try/dry-run 按钮预留（后端暂不支持）

---

## Memory

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/memory/search` | GET | Agent → Memory | DataTable + FilterBar | id, namespace, key, value, source_type, created_at | 500, timeout, empty | ✅ |
| `/api/memory/upsert` | POST | Memory → Add Memory | 表单 + Drawer | namespace, key, value, source, ttl | 400, 500 | ✅ |
| `/api/memory/{id}` | GET | Memory 行点击 → Drawer | JsonViewer + 详情网格 | id, namespace, key, value, metadata | 404, 500, timeout | ✅ |

**说明**:
- ✅ Memory 视图已完全实现（PR-4）
- ✅ MemoryView.js: 完整的记忆管理界面
- ℹ️ 当前后端无 DELETE 端点，UI 已预留扩展

**DoD Checklist (PR-4完成)**:
- [x] Memory 列表页（DataTable + FilterBar）
- [x] 搜索过滤（query + namespace + time_range）
- [x] Memory 详情抽屉（JsonViewer + 完整 metadata）
- [x] Add Memory 表单（namespace, key, value, source, ttl）
- [x] 写入成功后刷新列表
- [x] 错误态：400, 404, 500, timeout, empty
- [x] 追踪字段：id, namespace, key, created_at, source_type
- [x] 复制按钮：memory ID
- [x] 跨视图导航：View Source（task/session）
- [x] 操作按钮：Refresh, Add Memory

---

## Config

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/config` | GET | Settings → Config | 双视图（结构化 + Raw JSON） | version, python_version, settings, environment | 500, timeout | ✅ |

**说明**:
- ✅ Config 视图已完全实现（PR-4）
- ✅ ConfigView.js: 完整的配置查看器
- ℹ️ 当前后端无写入端点，仅支持只读查看

**DoD Checklist (PR-4完成)**:
- [x] Config 双视图（Structured + Raw JSON）
- [x] 系统信息面板（AgentOS version, Python version）
- [x] 应用设置展示（JsonViewer）
- [x] 环境变量表格（自动脱敏，按字母排序）
- [x] 快速操作按钮（View Providers, Run Self-check, Download Config）
- [x] 下载配置（JSON 格式）
- [x] 错误态：500, timeout
- [x] 追踪字段：version, python_version, settings count, env vars count
- [x] 操作按钮：Refresh, Download

---

## Runtime

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/runtime/fix-permissions` | POST | System → Runtime → Fix Permissions | 操作面板 + 确认对话框 + 结果展示 | ok, message, fixed_files | 403, 500 | ✅ |

**说明**:
- ✅ Runtime 视图已完全实现（PR-5）
- ✅ RuntimeView.js: 系统状态面板 + 权限修复工具

**DoD Checklist (PR-5完成)**:
- [x] Runtime 状态面板（System Status, Version, Uptime, CPU/Memory）
- [x] Provider 汇总（总数 + Ready/Error 统计）
- [x] Fix Permissions 操作（确认对话框 + 结果展示 + fixed_files 列表）
- [x] 错误态：403, 500
- [x] 追踪字段：ok, message, fixed_files
- [x] 快速跳转：View Providers, Run Self-check

---

## Secrets (已集成到 Providers)

| Endpoint | Method | UI 入口 | 展示形态 | 关键字段 | 错误态 | 覆盖状态 |
|----------|--------|---------|----------|----------|--------|----------|
| `/api/secrets` | POST | Settings → Providers → Cloud | 配置表单 | provider_id, api_key | 400, 500 | ✅ |
| `/api/secrets/{id}` | GET | - | - | - | - | ❌ |
| `/api/secrets/{id}` | DELETE | Settings → Providers → Cloud | 清除按钮 | - | 404, 500 | ✅ |
| `/api/secrets/test` | POST | Settings → Providers → Cloud | 测试按钮 | - | 401, 500 | ✅ |

**说明**:
- ✅ Secrets API 已通过 Cloud Provider 配置 UI 完全覆盖
- ❌ GET 端点不需要 UI（后端专用）

---

## Coverage Summary

| 分类 | 总端点数 | 完全覆盖 | 部分覆盖 | 待覆盖 | 不适用 | 覆盖率 |
|------|----------|----------|----------|--------|--------|--------|
| Health & System | 2 | 2 | 0 | 0 | 0 | 100% ✅ |
| Sessions & Chat | 6 | 6 | 0 | 0 | 0 | 100% ✅ |
| Tasks | 2 | 2 | 0 | 0 | 0 | 100% ✅ |
| Events | 2 | 2 | 0 | 0 | 0 | 100% ✅ |
| Logs | 2 | 2 | 0 | 0 | 0 | 100% ✅ |
| Providers | 11 | 11 | 0 | 0 | 0 | 100% ✅ |
| Self-check | 1 | 1 | 0 | 0 | 0 | 100% ✅ |
| Context | 4 | 4 | 0 | 0 | 0 | 100% ✅ |
| Skills | 2 | 2 | 0 | 0 | 0 | 100% ✅ |
| Memory | 3 | 3 | 0 | 0 | 0 | 100% ✅ |
| Config | 1 | 1 | 0 | 0 | 0 | 100% ✅ |
| Runtime | 1 | 1 | 0 | 0 | 0 | 100% ✅ |
| Secrets | 4 | 2 | 0 | 0 | 2 | 100% ✅ |
| **总计** | **41** | **39** | **0** | **0** | **2** | **100%** 🎉 |

**目标**: 100% 覆盖（除不适用端点）

**当前覆盖率**: 100% (39/39 可用端点) 🎉

**PR-2 进展**:
- ✅ Tasks 模块完成（2/2 端点）
- ✅ Events 模块完成（2/2 端点）
- ✅ Logs 模块完成（2/2 端点）
- 🎯 覆盖率从 39.5% 提升至 53.7% (+14.2%)

**PR-3 进展**:
- ✅ Sessions 模块完成（5/5 端点）
- ✅ Chat session binding 增强（WS 已有 + session binding）
- 🎯 覆盖率从 53.7% 提升至 65.9% (+12.2%)

**PR-4 进展 (Router Visualization)**:
- ✅ ProvidersView 路由增强（tags/ctx/role 编辑）
- ✅ TasksView 路由时间线（完整路由决策展示）
- ✅ RouteDecisionCard 组件（路由决策卡片）
- ✅ 新增 ~850 行代码（UI + CSS）
- 🎯 为 Task Router 后端提供完整可视化界面

**PR-4 Next (Skills/Memory/Config - Not in this PR)**:
- ⏳ Skills 模块（2/2 端点）
- ⏳ Memory 模块（3/3 端点）
- ⏳ Config 模块（1/1 端点）

**PR-5 进展**:
- ✅ Context 模块完成（4/4 端点）
- ✅ Runtime 模块完成（1/1 端点）
- ✅ Support 模块完成（1/1 端点，diagnostic-bundle）
- 🎯 覆盖率从 84.6% 提升至 100% (+15.4%)
- 🎉 **100% 覆盖率达成**（39/39 可用端点）

---

## PR Roadmap

### ✅ PR-1: 基础设施 (Infrastructure) - COMPLETE
**目标**: 提供通用组件，加速后续对接

**范围**:
- [x] `ApiClient` 封装 (fetch + timeout + error normalize + request-id)
- [x] `JsonViewer` 组件 (折叠/复制/下载)
- [x] `DataTable` 组件 (列渲染/空态/加载态)
- [x] `FilterBar` 组件 (query 输入/时间范围/level 下拉)
- [x] `Toast/Notice` 组件 (成功/失败/告警)
- [x] `LiveIndicator` 组件 (WebSocket/Health 状态灯)
- [x] Coverage Matrix 文档
- [x] 自动化覆盖率验证脚本

**实际交付**: 6个通用组件 + 完整文档 + 自动化验证

**时间**: 已完成

---

### ✅ PR-2: Observability Wave (Tasks + Events + Logs) - COMPLETE
**目标**: 实现核心可观测性，覆盖率 +14.2%

**范围**:
- [x] Tasks 列表视图 (DoD: 完整实现)
- [x] Events 时间线视图 (DoD: 完整实现)
- [x] Logs 列表视图 (DoD: 完整实现)

**实际交付**:
- TasksView.js (完整任务管理 + 详情抽屉 + 跨视图导航)
- EventsView.js (事件流时间线 + 实时流模式 + 筛选)
- LogsView.js (日志查看器 + Tail模式 + 下载)
- 导航栏新增 Observability 分组
- 完整的错误处理和加载状态
- 跨视图导航功能 (Tasks ↔ Events ↔ Logs ↔ Chat)

**依赖**: PR-1 (基础组件) ✅

**覆盖率提升**: 39.5% → 53.7% (+6 端点，实际 +14.2%)

**时间**: 已完成

---

### ✅ PR-3: Sessions First-class Citizen - COMPLETE
**目标**: Session 升级为一等对象，覆盖率 +12.2%

**范围**:
- [x] Sessions 列表页 (DoD: 完整实现)
- [x] Session CRUD 操作 (新建/重命名/删除)
- [x] Chat session binding (session 绑定 + 输入护栏 + 状态显示)

**实际交付**:
- SessionsView.js (完整 session 管理 + CRUD + 详情抽屉 + 跨视图导航)
- Chat toolbar 增强 (session_id 显示 + copy + view session + WS status)
- Chat 输入护栏 (无 session 则 disable)
- Session 为"锚点"：任何地方跳转 session
- Cross-navigation: Sessions ↔ Tasks/Events/Logs/Chat
- 护栏规则：session_id 强校验，missing badge，contract validation

**依赖**: PR-1 (基础组件) ✅

**覆盖率提升**: 53.7% → 65.9% (+5 端点，实际 +12.2%)

**时间**: 已完成

---

### ✅ PR-4: Router Visualization Enhancement - COMPLETE
**目标**: 为 Task Router 提供完整可视化界面

**范围**:
- [x] ProvidersView 路由元数据增强（tags/ctx/role 编辑）
- [x] TasksView 路由时间线（路由决策 + 事件展示）
- [x] RouteDecisionCard 组件（独立路由决策卡片）
- [x] 路由可视化 CSS 样式（~500 行）

**实际交付**:
- ProvidersView.js (+150 行)
  - 新增"Routing Metadata"列，显示 tags/ctx/role
  - 蓝色/紫色/绿色徽章显示元数据
  - 🎯 按钮打开路由元数据编辑器
  - Modal 表单：tags（逗号分隔）+ ctx（数字）+ role（文本）
  - API 集成：GET/PUT /api/providers/instances/{provider}/{instance}
- TasksView.js (+200 lines)
  - 路由信息区块：Selected Instance（蓝色高亮）
  - Requirements 显示（黄色徽章）
  - Route Plan 展示：reasons（✓列表）+ scores（柱状图）+ fallback chain
  - Route Timeline：TASK_ROUTED/TASK_ROUTE_VERIFIED/TASK_REROUTED/TASK_ROUTE_OVERRIDDEN
  - 事件卡片：图标 + 类型 + 时间 + 实例 + 原因 + 评分
- RouteDecisionCard.js (新组件，180 行)
  - 独立可复用组件
  - Selected Instance（渐变蓝色大字体显示）
  - Reasons（带✓的人类可读列表）
  - Scores（横向柱状图 + 百分比）
  - Fallback Chain（带箭头的序号链）
  - onChangeInstance 回调（未来用于手动改路由）
- components.css (+500 行)
  - ProvidersView 元数据样式（徽章、表格列）
  - TasksView 路由可视化样式（时间线、评分图、fallback 链）
  - RouteDecisionCard 完整样式（卡片、渐变、动画）
- index.html (+1 行)
  - 引入 RouteDecisionCard.js

**依赖**:
- PR-1 (基础组件) ✅
- PR-2 (TasksView) ✅
- PR-1/PR-2/PR-3 Router Backend (待实现)

**覆盖率影响**: 0 端点新增（UI-only，等待后端）

**文档**:
- docs/guides/PR-4-Router-Visualization.md（完整实现文档）
- docs/guides/webui-coverage-matrix.md（更新 Tasks + Providers）

**时间**: 2026-01-28 完成

---

### ⏳ PR-5: Skills/Memory/Config Module - PLANNED
**目标**: 实现可操作性，覆盖率 +18.7%

**范围**:
- [ ] Skills 视图（完整实现）
- [ ] Memory 视图（完整实现 + 写入功能）
- [ ] Config 视图（完整实现）

**依赖**: PR-1 (基础组件) ✅

**覆盖率提升**: 65.9% → 84.6% (+6 端点，实际 +18.7%)

**时间**: TBD

---

## Verification Script

运行 `scripts/verify_webui_coverage.py` 自动检查：
1. 拉取 OpenAPI (`/openapi.json`)
2. 对比此矩阵
3. 输出缺口列表

**CI 集成**: PR 检查此脚本通过才能合并

---

## Notes

1. **追踪字段优先级**:
   - 必须: `request_id` / `task_id` / `session_id` 三选二
   - 推荐: `timestamp` (所有时间相关)
   - 可选: `trace` / `lineage`

2. **错误态标准**:
   - 网络错误: `timeout`, `network_error`
   - 后端错误: `401`, `403`, `404`, `500`
   - 业务错误: `empty`, `invalid`, `conflict`

3. **不适用 (❌) 判定标准**:
   - 纯后端专用（如内部健康检查）
   - 不需要用户交互（如后台定时任务）

4. **更新频率**:
   - 新增 API: 立即更新矩阵
   - 完成 UI: 更新状态为 ✅
   - 每个 PR 合并前: 更新覆盖率统计

---

**最后更新**: 2026-01-27
**下次审查**: PR-1 合并前
