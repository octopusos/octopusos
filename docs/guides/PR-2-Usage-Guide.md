# PR-2: Chat→Task Router Integration - Usage Guide

## 快速开始

### 1. 运行数据库迁移

首先需要运行 migration 添加路由字段到 tasks 表：

```bash
# 方法1: 使用测试脚本（会自动检测并运行迁移）
python3 test_pr2_router.py

# 方法2: 手动运行迁移
sqlite3 ~/.agentos/agentos.db < agentos/store/migrations/v12_task_routing.sql
```

### 2. 配置 Provider Instances

确保 `~/.agentos/config/providers.json` 中配置了实例的 metadata（tags、ctx、model）：

```json
{
  "providers": {
    "llamacpp": {
      "enabled": true,
      "instances": [
        {
          "id": "qwen3-coder-30b",
          "base_url": "http://127.0.0.1:11435",
          "enabled": true,
          "metadata": {
            "tags": ["coding", "frontend", "backend", "big_ctx"],
            "ctx": 8192,
            "model": "Qwen3-Coder-30B-Q8"
          }
        },
        {
          "id": "glm47flash-q8",
          "base_url": "http://127.0.0.1:11436",
          "enabled": true,
          "metadata": {
            "tags": ["general", "fast"],
            "ctx": 4096,
            "model": "GLM-4-7B-Flash-Q8"
          }
        }
      ]
    },
    "ollama": {
      "enabled": true,
      "instances": [
        {
          "id": "default",
          "base_url": "http://127.0.0.1:11434",
          "enabled": true,
          "metadata": {
            "tags": ["general"],
            "ctx": 4096
          }
        }
      ]
    }
  }
}
```

**Metadata 字段说明：**
- `tags`: 能力标签列表（coding, frontend, backend, data, testing, general, fast, big_ctx 等）
- `ctx`: 上下文窗口大小
- `model`: 模型名称（可选，用于显示）

### 3. 测试路由功能

#### 3.1 使用测试脚本

```bash
python3 test_pr2_router.py
```

测试脚本会验证：
- 数据库迁移
- 需求提取
- Router 核心
- Task 创建时路由
- 手动路由覆盖

#### 3.2 Chat 中创建 Task

启动 WebUI：

```bash
agentos webui
```

在 Chat 界面输入：

```
/task 实现一个 React 登录组件
```

期望输出：

```
✓ Created task: abc123def456... - 实现一个 React 登录组件

Task is now linked to this chat session.

**Routing:**
- Selected: `llamacpp:qwen3-coder-30b`
- Score: 0.92
- Reasons: READY, tags_match=coding,frontend, ctx>=4096
- Fallback: llamacpp:glm47flash-q8, ollama:default
```

#### 3.3 API 测试

**查询 Task 路由信息：**

```bash
curl http://localhost:8000/api/tasks/{task_id}/route
```

响应示例：

```json
{
  "task_id": "01JXX123...",
  "selected": "llamacpp:qwen3-coder-30b",
  "fallback": ["llamacpp:glm47flash-q8", "ollama:default"],
  "scores": {
    "llamacpp:qwen3-coder-30b": 0.92,
    "llamacpp:glm47flash-q8": 0.73,
    "ollama:default": 0.40
  },
  "reasons": ["READY", "tags_match=coding,frontend", "ctx>=8192", "latency_best"],
  "router_version": "v1",
  "timestamp": "2026-01-28T01:30:00.000Z",
  "requirements": {
    "needs": ["coding", "frontend"],
    "prefer": ["local"],
    "min_ctx": 4096,
    "latency_class": "normal"
  }
}
```

**手动覆盖路由：**

```bash
curl -X POST http://localhost:8000/api/tasks/{task_id}/route \
  -H "Content-Type: application/json" \
  -d '{"instance_id": "ollama:default"}'
```

### 4. 查看审计事件

```sql
sqlite3 ~/.agentos/agentos.db

SELECT
  event_type,
  level,
  payload,
  created_at
FROM task_audits
WHERE task_id = 'YOUR_TASK_ID'
ORDER BY created_at;
```

审计事件类型：
- `TASK_ROUTED`: 初始路由（level: info）
- `TASK_ROUTE_VERIFIED`: 执行前验证（level: info）
- `TASK_REROUTED`: 自动重路由（level: warn）
- `TASK_ROUTE_OVERRIDDEN`: 手动覆盖（level: info）
- `TASK_ROUTING_FAILED`: 路由失败（level: error）

## 路由逻辑说明

### 需求提取（Requirements Extraction）

基于关键词匹配检测任务需求：

| 能力 | 关键词示例 |
|-----|---------|
| coding | code, implement, fix, bug, function, class, api |
| frontend | react, vue, angular, html, css, component, mui |
| backend | server, api, endpoint, database, sql |
| data | analysis, pandas, csv, etl, transform |
| testing | test, pytest, jest, coverage |
| long_ctx | long, large, multiple files, summary |

### 评分公式（Scoring）

总分 = 状态分 + 标签分 + 上下文分 + 延迟分 + 偏好分

- **状态分**: READY=1.0, 否则=0（硬门槛）
- **标签分**: 每个匹配的 tag +0.2
- **上下文分**: ctx >= min_ctx +0.1, ctx 未知 +0.02
- **延迟分**: <50ms=0.1, <200ms=0.05, <500ms=0.02, >=500ms=0
- **偏好分**: local +0.05, cloud -0.02

### Fallback Chain

选择 top 3 得分的实例：
1. **selected**: 最高分
2. **fallback[0]**: 第二高分
3. **fallback[1]**: 第三高分

## 故障排查

### 问题1: 路由失败 "No provider instances available"

**原因**: 没有可用的 provider instances

**解决**:
1. 检查 providers 是否运行：
   ```bash
   curl http://localhost:11434/v1/models  # Ollama
   curl http://localhost:11435/v1/models  # llama.cpp
   ```

2. 检查 ProviderRegistry 状态：
   ```bash
   curl http://localhost:8000/api/providers/status
   ```

### 问题2: 所有实例 score=0

**原因**: 所有实例都不 READY

**解决**:
1. 启动至少一个 provider instance
2. 确保 fingerprint 探测成功

### 问题3: 路由选择了错误的实例

**原因**: metadata 中 tags 配置不准确

**解决**:
1. 编辑 `~/.agentos/config/providers.json`
2. 添加/修改 `metadata.tags`
3. 重启 WebUI

### 问题4: Migration 失败

**原因**: 数据库被锁定或权限问题

**解决**:
1. 停止 WebUI
2. 手动运行迁移：
   ```bash
   sqlite3 ~/.agentos/agentos.db < agentos/store/migrations/v12_task_routing.sql
   ```

## 下一步

### 前端 UI 实现

需要在 WebUI 中添加：

1. **Chat Task 创建卡片** (`static/js/main.js`)
   - 解析 `/task` 命令响应中的 `routing` 字段
   - 显示 selected, score, reasons, fallback
   - 添加 "Change Instance" 按钮

2. **Task 详情页**
   - 添加 "Routing" section
   - 显示 route timeline（TASK_ROUTED → TASK_ROUTE_VERIFIED → TASK_REROUTED）
   - 支持点击 "Change" 打开实例选择器

3. **实例选择器组件**
   - 从 `/api/providers/status` 获取可用实例
   - 显示每个实例的 state、tags、latency、model
   - 选择后调用 POST `/api/tasks/{id}/route`

### PR-3: Runner 执行集成

在 TaskRunner 中集成：

```python
# agentos/core/runner/task_runner.py

async def run_task(self, task_id: str):
    # 1. Verify route before execution
    routing_service = TaskRoutingService()
    plan, reroute_event = await routing_service.verify_route(task_id)

    if reroute_event:
        logger.warning(f"Task rerouted: {reroute_event.to_dict()}")

    # 2. Use plan.selected as provider instance
    provider = registry.get(plan.selected)

    # 3. Execute with selected instance
    # ...
```

## 参考

- [reouter.md](/docs/todos/reouter.md) - Router 规格文档
- [PR-2-Chat-Task-Routing-Complete.md](PR-2-Chat-Task-Routing-Complete.md) - 实现总结
- [webui-coverage-matrix.md](webui-coverage-matrix.md) - WebUI 功能矩阵
