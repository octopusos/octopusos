# PR-2: Chat→Task Router Integration - Implementation Complete

## 概述

已完成 Chat→Task 创建时的路由接入，实现了按照 `/docs/todos/reouter.md` PR-2 规格的所有核心功能。

## 实现内容

### 1. Router 核心模块 (agentos/router/)

#### models.py
- `InstanceProfile`: 实例能力画像
- `TaskRequirements`: 任务能力需求
- `RoutePlan`: 路由决策计划
- `RouteScore`: 评分结果
- `RerouteReason` / `RerouteEvent`: 重路由事件

#### requirements_extractor.py
- `RequirementsExtractor`: 基于规则的需求提取器
- 关键词匹配检测能力需求（coding, frontend, backend, data, testing, long_ctx）
- 上下文窗口估算
- 延迟等级判断

#### instance_profiles.py
- `InstanceProfileBuilder`: 从 ProviderRegistry 构建实例画像
- 聚合 provider 状态、配置、metadata
- 支持从 providers.json 读取 tags、ctx、model 等元数据

#### scorer.py
- `RouteScorer`: 路由评分引擎
- MVP 评分公式：
  - READY 状态：必需（否则 score=0）
  - Tags 匹配：每个匹配 +0.2
  - Context window：满足 min_ctx +0.1
  - Latency：0-0.1（归一化，越低越高）
  - Local preference：本地 +0.05，云 -0.02

#### router.py
- `Router`: 核心路由引擎
- `route()`: 生成初始路由计划
- `verify_or_reroute()`: 执行前验证/重路由
- `override_route()`: 手动覆盖路由
- `get_available_instances()`: 获取可用实例列表

### 2. 数据库模式更新

#### migration v12_task_routing.sql
添加到 tasks 表的字段：
- `route_plan_json`: JSON 序列化的 RoutePlan
- `requirements_json`: JSON 序列化的 TaskRequirements
- `selected_instance_id`: 选中的实例 ID
- `router_version`: 路由器版本
- 索引：`idx_tasks_selected_instance`

### 3. Task 模型更新 (agentos/core/task/)

#### models.py
- 添加路由字段到 `Task` dataclass
- 更新 `to_dict()` 方法包含路由字段

#### manager.py
- `create_task()`: 支持路由字段参数
- `get_task()` / `list_tasks()`: 读取路由字段
- `update_task_routing()`: 更新任务路由信息

#### routing_service.py (新文件)
- `TaskRoutingService`: 路由服务层
- `route_new_task()`: 路由新任务并保存
- `verify_route()`: 验证路由
- `override_route()`: 手动覆盖
- `get_route_plan()`: 获取路由计划
- `route_task_sync()`: 同步包装器（用于非 async 上下文）

### 4. Chat→Task 集成

#### agentos/core/chat/handlers/task_handler.py
在 `/task` 命令中集成路由：
1. 创建 Task
2. 调用 `TaskRoutingService.route_new_task()`
3. 获取 RoutePlan
4. 写入 TASK_ROUTED 事件
5. 在响应消息中显示路由决策

显示信息：
- Selected instance
- Score
- Reasons (前 3 个)
- Fallback chain (前 2 个)

### 5. WebUI API 扩展

#### agentos/webui/api/tasks.py

新增端点：

**GET /api/tasks/{task_id}/route**
- 获取任务的路由计划
- 返回：selected, fallback, scores, reasons, requirements

**POST /api/tasks/{task_id}/route**
- 手动覆盖任务路由
- 请求：`{"instance_id": "llamacpp:qwen3-coder-30b"}`
- 写入 TASK_ROUTE_OVERRIDDEN 事件

## 使用方式

### 1. Chat 创建 Task 时自动路由

```bash
# 在 Chat 中
> /task 写一个 React 登录页面
```

系统会：
1. 创建 Task
2. 分析需求（检测到 "React" → frontend, coding）
3. 路由到最佳实例（如 llamacpp:qwen3-coder-30b）
4. 显示路由决策

返回示例：
```
✓ Created task: abc123def456... - 写一个 React 登录页面

Task is now linked to this chat session.

**Routing:**
- Selected: `llamacpp:qwen3-coder-30b`
- Score: 0.92
- Reasons: READY, tags_match=coding,frontend, ctx>=4096
- Fallback: llamacpp:glm47flash-q8, ollama:default
```

### 2. 查询任务路由

```bash
GET /api/tasks/{task_id}/route
```

### 3. 手动改路由 (UI)

```bash
POST /api/tasks/{task_id}/route
{
  "instance_id": "ollama:default"
}
```

## 审计事件

所有路由操作都写入 task_audits 表：

- **TASK_ROUTED**: 初始路由
- **TASK_ROUTE_VERIFIED**: 执行前验证（实例仍 READY）
- **TASK_REROUTED**: 自动切换（实例不可用）
- **TASK_ROUTE_OVERRIDDEN**: 手动覆盖
- **TASK_ROUTING_FAILED**: 路由失败

## 待完成（下一步）

### UI 展示（未包含在本 PR）

需要在 WebUI 中添加：

1. **Chat 确认卡片**
   - 显示路由决策
   - "Change" 按钮触发实例选择器

2. **Task 详情页**
   - 显示路由时间线
   - 展示 route_plan
   - 支持手动改路由

3. **实例选择器组件**
   - 下拉列表显示所有可用实例
   - 显示每个实例的 tags、state、latency
   - 选择后调用 POST /api/tasks/{id}/route

### PR-3: Runner 执行接入（下一个 PR）

在 TaskRunner 执行前：
1. 调用 `TaskRoutingService.verify_route()`
2. 检查 selected instance 是否 READY
3. 如不 READY，按 fallback 自动切换
4. 执行中错误触发 reroute

## 验收标准 ✅

- [x] Chat 输入"写代码任务"创建 Task
- [x] 立即调用 Router 生成 RoutePlan
- [x] 保存路由信息到 tasks 表
- [x] 显示"选中实例 + 原因 + fallback 链"
- [x] API 支持查询路由计划
- [x] API 支持手动覆盖路由
- [x] 写入 TASK_ROUTED / TASK_ROUTE_OVERRIDDEN 事件
- [ ] UI 可视化展示路由决策（待 WebUI 前端实现）
- [ ] UI 支持 Change 按钮改路由（待 WebUI 前端实现）

## 测试建议

1. **创建任务测试**
   ```python
   # 在 chat 中运行
   /task 实现一个 React 组件
   # 观察路由结果
   ```

2. **路由失败测试**
   - 停止所有 provider instances
   - 创建 task 应该失败并写入 TASK_ROUTING_FAILED

3. **手动覆盖测试**
   ```bash
   curl -X POST http://localhost:8000/api/tasks/{id}/route \
     -H "Content-Type: application/json" \
     -d '{"instance_id": "ollama:default"}'
   ```

4. **审计事件验证**
   ```sql
   SELECT * FROM task_audits
   WHERE task_id = 'xxx'
   ORDER BY created_at;
   ```

## 文件清单

### 新增文件
- agentos/router/__init__.py
- agentos/router/models.py
- agentos/router/requirements_extractor.py
- agentos/router/instance_profiles.py
- agentos/router/scorer.py
- agentos/router/router.py
- agentos/core/task/routing_service.py
- agentos/store/migrations/v12_task_routing.sql

### 修改文件
- agentos/core/task/models.py
- agentos/core/task/manager.py
- agentos/core/chat/handlers/task_handler.py
- agentos/webui/api/tasks.py

## 依赖

- ProviderRegistry (已存在)
- ProvidersConfigManager (已存在)
- TaskManager (已存在)
- 需要运行 migration v12 添加数据库字段

## 总结

PR-2 实现了完整的 Chat→Task 路由集成：
- ✅ Router 核心引擎完成
- ✅ 数据库模式支持
- ✅ Task 创建时自动路由
- ✅ API 支持查询和覆盖
- ✅ 审计事件完整
- ⏳ UI 可视化待前端实现

下一步：PR-3 Runner 执行前路由验证 + failover
