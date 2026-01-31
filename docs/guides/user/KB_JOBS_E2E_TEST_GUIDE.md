# Knowledge Jobs 页面 - 端到端测试指南与验收清单

## 文档概述

本文档提供 Knowledge Jobs 页面的完整端到端测试方案，包括测试环境准备、详细测试场景、验收标准、问题排查和测试报告模板。

**版本**: v1.0
**创建日期**: 2026-01-28
**组件**: AgentOS WebUI - Knowledge Jobs
**状态**: ✅ 后端已修复 | ✅ 前端已优化 | 🔍 待验收

---

## 1. 测试环境准备

### 1.1 启动服务器

```bash
# 方法一: 直接启动 FastAPI 应用
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.app

# 方法二: 使用 uvicorn (推荐，支持热重载)
uvicorn agentos.webui.app:app --reload --host 0.0.0.0 --port 8000
```

**预期输出**:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     AgentOS WebUI starting...
INFO:     SQLiteSessionStore initialized successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 1.2 访问 Web 界面

1. 打开浏览器（推荐 Chrome/Edge/Firefox）
2. 访问: `http://localhost:8000`
3. 在左侧导航栏找到 **Knowledge** 菜单
4. 点击 **Jobs** 子菜单

### 1.3 开发者工具配置

**打开开发者工具**:
- Windows/Linux: `F12` 或 `Ctrl+Shift+I`
- macOS: `Cmd+Option+I`

**配置检查项**:

1. **Console 标签页**:
   - 清空历史日志
   - 启用所有日志级别 (Verbose)
   - 观察 WebSocket 连接日志

2. **Network 标签页**:
   - 启用 "Preserve log"
   - 观察 API 请求 (`/api/knowledge/jobs`)
   - 检查 WebSocket 连接 (`/ws/events`)

3. **关键日志标识**:
   ```
   ✅ "KnowledgeJobsView: WebSocket connected"
   ✅ "KnowledgeJobsView: WebSocket message received"
   ⚠️  检查是否有 404/500 错误
   ```

---

## 2. 测试场景清单

### 场景 1: 创建 Incremental Job

**操作步骤**:
1. 点击 **Incremental** 按钮
2. 观察页面响应和 Toast 提示
3. 观察 Jobs 列表自动刷新
4. 监控状态流转

**预期结果**:

| 阶段 | 状态 | 进度 | 消息 | 持续时间 |
|------|------|------|------|----------|
| 创建 | `created` / `Pending...` | 0% | "Initializing..." | < 1s |
| 启动 | `in_progress` / `In Progress` | 5% | "Starting index operation..." | 1-2s |
| 扫描 | `in_progress` | 20% | "Scanning for changed files..." | 2-5s |
| 处理 | `in_progress` | 90% | "Processed X files, Y chunks" | 5-15s |
| 完成 | `completed` / `Completed` | 100% | "Index operation completed" | < 1s |

**UI 反馈验证**:
- ✅ Toast 提示: "incremental job triggered successfully"
- ✅ 进度条动画流畅，无闪烁
- ✅ 状态徽章颜色正确（蓝色 → 黄色 → 绿色）
- ✅ Files/Chunks 计数正确更新
- ✅ Duration 在完成后显示（如 "15s"）

**验收标准**:
- [ ] 按钮点击响应 < 500ms
- [ ] 状态从 `created` → `in_progress` → `completed` 完整流转
- [ ] 进度从 0% → 100% 连续更新
- [ ] 无控制台错误
- [ ] WebSocket 事件正确接收（查看 Console 日志）

---

### 场景 2: 创建 Rebuild Job

**操作步骤**:
1. 点击 **Rebuild** 按钮
2. 观察与 Incremental 的差异
3. 验证全量索引行为

**预期结果**:

| 阶段 | 状态 | 进度 | 消息 | 特征 |
|------|------|------|------|------|
| 创建 | `created` | 0% | "Initializing..." | 与 Incremental 相同 |
| 启动 | `in_progress` | 5% | "Starting index operation..." | 与 Incremental 相同 |
| 重建 | `in_progress` | 20% | "Rebuilding entire index..." | **差异点** |
| 处理 | `in_progress` | 90% | "Processed X files, Y chunks" | Files 数量更多 |
| 完成 | `completed` | 100% | "Index operation completed" | 耗时更长 |

**差异验证**:
- ✅ Type 徽章显示为紫色 "Rebuild"
- ✅ Files Processed 数量 ≥ Incremental
- ✅ Duration 通常 > Incremental
- ✅ Message 显示 "Rebuilding entire index..."

**验收标准**:
- [ ] Type 标签正确显示 "Rebuild" (紫色徽章)
- [ ] 处理的文件数量 > 0
- [ ] 完整流程无异常
- [ ] 耗时合理（通常 10-60 秒，视项目大小）

---

### 场景 3: 创建 Repair Job

**操作步骤**:
1. 点击 **Repair** 按钮（次要按钮样式）
2. 验证索引修复逻辑
3. 观察错误处理行为

**预期结果**:

| 阶段 | 状态 | 进度 | 消息 |
|------|------|------|------|
| 创建 | `created` | 0% | "Initializing..." |
| 启动 | `in_progress` | 5% | "Starting index operation..." |
| 检查 | `in_progress` | 20% | "Checking index integrity..." |
| 修复 | `in_progress` | 90% | "Index repair completed" |
| 完成 | `completed` | 100% | "Index operation completed" |

**特殊验证**:
- ✅ Type 徽章为橙色 "Repair"
- ✅ Message 显示 "Checking index integrity..."
- ✅ Errors 列显示发现的问题数量
- ✅ 修复逻辑正确执行（检查后端日志）

**验收标准**:
- [ ] Type 标签正确显示 "Repair" (橙色徽章)
- [ ] 完整性检查正常执行
- [ ] 如有错误，Errors 列正确显示
- [ ] 修复后状态为 `completed`

---

### 场景 4: 创建 Vacuum Job

**操作步骤**:
1. 点击 **Vacuum** 按钮（次要按钮样式）
2. 验证清理和优化逻辑
3. 观察已删除文件的清理

**预期结果**:

| 阶段 | 状态 | 进度 | 消息 |
|------|------|------|------|
| 创建 | `created` | 0% | "Initializing..." |
| 启动 | `in_progress` | 5% | "Starting index operation..." |
| 清理 | `in_progress` | 20% | "Cleaning up index..." |
| 优化 | `in_progress` | 90% | "Cleaned X files, Y chunks" |
| 完成 | `completed` | 100% | "Index operation completed" |

**特殊验证**:
- ✅ Type 徽章为绿色 "Vacuum"
- ✅ Message 显示 "Cleaning up index..."
- ✅ Files/Chunks Processed 显示清理的数量
- ✅ 数据库文件大小可能减小

**验收标准**:
- [ ] Type 标签正确显示 "Vacuum" (绿色徽章)
- [ ] 清理逻辑正常执行
- [ ] 完成后无孤立 chunks
- [ ] 状态流转正常

---

### 场景 5: Refresh 列表（重要：验证不创建新 Job）

**操作步骤**:
1. 记录当前 Jobs 列表的 Job 数量 (记为 `N`)
2. 点击 **Refresh** 按钮（刷新图标）
3. 等待列表刷新完成
4. 验证 Job 数量仍为 `N`

**预期结果**:
- ✅ 列表重新加载
- ✅ 显示最新的 Job 状态
- ✅ **Job 数量不变**（不会触发新 Job）
- ✅ 进度和状态更新到最新值
- ✅ 无 Toast 提示（除非出错）

**关键验证**:
```
刷新前 Jobs 数量: N
点击 Refresh
刷新后 Jobs 数量: N  ✅ PASS
刷新后 Jobs 数量: N+1  ❌ FAIL (创建了新 Job)
```

**验收标准**:
- [ ] 点击 Refresh 按钮后，Job 数量不增加
- [ ] 现有 Jobs 的状态/进度正确更新
- [ ] 刷新延迟 < 1 秒
- [ ] 无控制台错误

---

### 场景 6: 并发 Jobs（压力测试）

**操作步骤**:
1. 快速连续点击（间隔 < 1 秒）:
   - Incremental 按钮
   - Rebuild 按钮
   - Repair 按钮
   - Vacuum 按钮
2. 观察多个 Jobs 同时运行的状态
3. 验证状态更新不冲突

**预期结果**:

| Job Type | 状态 | 进度 | 验证点 |
|----------|------|------|--------|
| Incremental | `in_progress` | 变化中 | 独立进度条 |
| Rebuild | `in_progress` | 变化中 | 独立进度条 |
| Repair | `in_progress` | 变化中 | 独立进度条 |
| Vacuum | `in_progress` | 变化中 | 独立进度条 |

**并发验证**:
- ✅ 4 个 Jobs 同时出现在列表中
- ✅ 每个 Job 的进度独立更新
- ✅ 状态不会互相覆盖
- ✅ WebSocket 事件正确分发到对应 Job
- ✅ 轮询机制正常工作（每 2 秒刷新）

**压力验证**:
- ✅ 无 UI 卡顿或冻结
- ✅ 内存使用正常（< 200MB 增长）
- ✅ 所有 Jobs 最终都能完成
- ✅ 无 JavaScript 错误

**验收标准**:
- [ ] 支持至少 4 个并发 Jobs
- [ ] 每个 Job 的状态独立更新
- [ ] 无状态冲突或覆盖
- [ ] UI 响应流畅（无明显延迟）
- [ ] 所有 Jobs 最终状态为 `completed`

---

### 场景 7: Job 详情查看（Drawer）

**操作步骤**:
1. 点击任意 Job 行（整行可点击）
2. 观察右侧 Drawer 滑出动画
3. 验证详情显示完整性
4. 点击关闭按钮或遮罩层关闭 Drawer

**预期详情内容**:

**Overview 区块**:
- Job ID: 完整的 ULID（如 `01HXYZ...`）
- Type: 彩色徽章（Incremental/Rebuild/Repair/Vacuum）
- Status: 状态徽章（Pending.../In Progress/Completed/Failed）
- Progress: 进度条 + 消息文本

**Statistics 区块**:
- Files Processed: 数字格式化（如 "1,250"）
- Chunks Processed: 数字格式化
- Errors: 红色高亮（如果 > 0）
- Duration: 格式化时间（如 "15s", "2m 30s", "1h 5m"）

**Timeline 区块**:
- Created: 相对时间（如 "Just now", "5m ago", "2h ago"）
- Updated: 相对时间

**Related 区块**:
- "View Events" 链接（导航到 Events 视图）
- "View Logs" 链接（导航到 Logs 视图）

**交互验证**:
- ✅ Drawer 滑入动画流畅（300ms 过渡）
- ✅ 点击遮罩层（半透明背景）可关闭
- ✅ 点击右上角 ✕ 按钮可关闭
- ✅ 关闭后 Drawer 滑出消失
- ✅ 可以连续点击不同 Job 行切换详情

**实时更新验证**:
1. 打开一个 `in_progress` Job 的 Drawer
2. 保持 Drawer 打开
3. 观察进度和状态是否实时更新

**验收标准**:
- [ ] 点击任意 Job 行能打开 Drawer
- [ ] Drawer 动画流畅无卡顿
- [ ] 所有信息字段正确显示
- [ ] 进度条和消息实时更新（如果 Job 进行中）
- [ ] 关闭 Drawer 的两种方式都有效
- [ ] Related 链接可点击（导航正确）

---

## 3. 验收标准总结

### 3.1 功能完整性

| 功能模块 | 验收标准 | 优先级 |
|----------|----------|--------|
| **Job 创建** | 4 种 Job 类型都能成功创建 | P0 |
| **状态流转** | created → in_progress → completed 完整流程 | P0 |
| **进度更新** | 0% → 100% 连续且准确 | P0 |
| **列表刷新** | Refresh 按钮不创建新 Job | P0 |
| **并发处理** | 支持 4+ 个 Job 同时运行 | P1 |
| **详情查看** | Drawer 显示完整信息 | P1 |
| **实时更新** | WebSocket 事件正确处理 | P1 |

### 3.2 性能要求

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| **按钮响应延迟** | < 500ms | 点击到 Toast 显示 |
| **状态更新延迟** | < 3s | 后端状态变化到前端显示 |
| **列表刷新延迟** | < 1s | 点击 Refresh 到数据更新 |
| **轮询间隔** | 2s | 检查 Network 请求频率 |
| **Drawer 动画** | 300ms | 观察滑入/滑出过渡 |
| **内存增长** | < 50MB/分钟 | 浏览器 Task Manager |

### 3.3 UI/UX 要求

| 项目 | 标准 | 验证方法 |
|------|------|----------|
| **进度条流畅度** | 无闪烁、无跳变 | 视觉观察 |
| **状态徽章颜色** | 符合设计规范 | 对比 CSS 定义 |
| **Toast 提示** | 清晰、无重复 | 操作后观察 |
| **错误处理** | 友好的错误提示 | 模拟失败场景 |
| **空状态** | "No index jobs found" 提示 | 清空数据后验证 |
| **分页功能** | 每页 10 条，分页按钮可用 | 创建 20+ Jobs 验证 |

### 3.4 稳定性要求

| 场景 | 验收标准 | 测试方法 |
|------|----------|----------|
| **无 Job 运行** | 不应持续轮询 | 检查 Network 请求 |
| **长时间运行** | 30 分钟无错误 | 压力测试 |
| **快速点击** | 防抖机制，无重复 Job | 快速点击按钮 |
| **WebSocket 断开** | 自动重连，提示用户 | 断网后恢复 |
| **Tab 切换** | 切回后状态同步 | 切换浏览器标签页 |

---

## 4. 常见问题排查

### 问题 1: Job 卡在 "Pending..." 状态

**症状**:
- Job 状态始终为 `created` / "Pending..."
- 进度为 0%
- 持续时间 > 10 秒

**排查步骤**:

1. **检查后端日志**:
   ```bash
   # 查找 KB Index Job 相关日志
   grep "KB Index Job" /path/to/server.log
   ```

   **期望看到**:
   ```
   [KB Index Job] Thread started: task_id=01HXYZ..., job_type=incremental
   [KB Index Job] Initial task state: status=created
   [KB Index Job] Updating task to in_progress...
   ```

2. **检查 TaskManager.update_task() 方法**:
   ```bash
   # 验证方法是否存在
   python -c "from agentos.core.task import TaskManager; tm = TaskManager(); print(hasattr(tm, 'update_task'))"
   # 应输出: True
   ```

3. **检查线程是否启动**:
   - 后端日志中搜索 `Thread started`
   - 如果没有，检查 `threading.Thread` 启动逻辑

4. **检查 WebSocket 连接**:
   - 打开浏览器 DevTools → Network → WS 标签
   - 查找 `/ws/events` 连接
   - Status 应为 `101 Switching Protocols`

**解决方案**:
- ✅ 确保 `TaskManager.update_task()` 方法存在
- ✅ 确认后台线程正确启动
- ✅ 验证 WebSocket 连接正常

---

### 问题 2: WebSocket 连接失败

**症状**:
- Console 显示: "WebSocket error"
- Network 标签中 WebSocket 连接失败
- Job 状态不实时更新

**排查步骤**:

1. **检查 WebSocket URL**:
   ```javascript
   // 打开 Console 执行
   const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
   const wsUrl = `${protocol}//${window.location.host}/ws/events`;
   console.log(wsUrl);
   // 应输出: ws://localhost:8000/ws/events
   ```

2. **测试 WebSocket 端点**:
   ```python
   # 测试脚本
   import asyncio
   import websockets

   async def test():
       uri = "ws://localhost:8000/ws/events"
       async with websockets.connect(uri) as ws:
           print("Connected!")
           msg = await ws.recv()
           print(f"Received: {msg}")

   asyncio.run(test())
   ```

3. **检查防火墙/代理**:
   - 确认 8000 端口开放
   - 检查是否有代理阻止 WebSocket

4. **查看服务器日志**:
   ```
   INFO:     ('127.0.0.1', xxxxx) - "WebSocket /ws/events" [accepted]
   ```

**解决方案**:
- ✅ 确认 WebSocket 端口开放
- ✅ 检查 CORS 配置
- ✅ 验证 `/ws/events` 路由注册
- ✅ 如果失败，回退到轮询模式（每 2 秒）

---

### 问题 3: 进度不更新或更新缓慢

**症状**:
- 进度卡在某个百分比不动
- 刷新列表后才更新
- 更新延迟 > 5 秒

**排查步骤**:

1. **检查轮询间隔**:
   ```javascript
   // 在 KnowledgeJobsView.js 搜索
   this.refreshInterval = setInterval(() => {
       // ...
   }, 2000);  // 应为 2000ms (2秒)
   ```

2. **验证 WebSocket 事件接收**:
   ```javascript
   // 打开 Console，查找日志
   "KnowledgeJobsView: WebSocket message received: {type: 'task.progress', ...}"
   ```

3. **检查 Event Bus 发送**:
   ```python
   # 在 knowledge.py 搜索
   event_bus.emit(
       Event.task_progress(
           task_id=task_id,
           progress=20,
           message="Scanning for changed files...",
       )
   )
   ```

4. **检查 Job 是否在列表中**:
   ```javascript
   // Console 执行
   const job = window.state.currentViewInstance.jobs.find(j => j.job_id === 'YOUR_JOB_ID');
   console.log(job);
   // 应返回 Job 对象
   ```

**解决方案**:
- ✅ 确认轮询间隔为 2 秒
- ✅ 验证 WebSocket 事件正确发送和接收
- ✅ 检查 `updateJobFromEvent()` 方法逻辑
- ✅ 确保 Job 在 `this.jobs` 数组中

---

### 问题 4: 点击 Refresh 创建了新 Job

**症状**:
- 点击 Refresh 按钮
- Jobs 数量增加
- 出现新的 "incremental" Job

**原因分析**:
- 按钮 ID 或事件绑定错误
- Refresh 按钮误绑定到 Trigger 逻辑

**排查步骤**:

1. **检查按钮 ID**:
   ```javascript
   // 在 KnowledgeJobsView.js 中搜索
   <button class="btn-refresh" id="jobs-refresh">
   ```

2. **检查事件绑定**:
   ```javascript
   this.container.querySelector('#jobs-refresh').addEventListener('click', () => {
       this.loadJobs();  // 应该调用 loadJobs()，而非 triggerJob()
   });
   ```

3. **验证 loadJobs() 方法**:
   ```javascript
   async loadJobs() {
       // 应该只执行 GET 请求，不触发 POST
       const response = await fetch('/api/knowledge/jobs?limit=100');
       // ...
   }
   ```

**解决方案**:
- ✅ 确认 Refresh 按钮 ID 为 `jobs-refresh`
- ✅ 确认事件监听器调用 `this.loadJobs()`
- ✅ 确认 `loadJobs()` 方法只执行 GET 请求

---

### 问题 5: 并发 Jobs 状态混乱

**症状**:
- 创建多个 Jobs 后，状态互相覆盖
- 进度显示错误
- Job A 的进度显示在 Job B 上

**原因分析**:
- WebSocket 事件分发错误
- Job ID 匹配逻辑问题

**排查步骤**:

1. **检查 Job ID 匹配**:
   ```javascript
   handleWebSocketMessage(event) {
       const taskId = data.entity ? data.entity.id : null;
       const job = this.jobs.find(j => j.job_id === taskId);
       // 应该精确匹配 Job ID
   }
   ```

2. **验证 Jobs 数组**:
   ```javascript
   // Console 执行
   window.state.currentViewInstance.jobs.forEach(j => {
       console.log(j.job_id, j.type, j.status, j.progress);
   });
   ```

3. **检查后端 Task ID 生成**:
   ```python
   # 在 knowledge.py 中
   task = task_manager.create_task(
       title=f"KB Index: {request.type}",
       # ...
   )
   task_id = task.task_id  # 应该是唯一的 ULID
   ```

**解决方案**:
- ✅ 确保每个 Job 有唯一的 `job_id`
- ✅ WebSocket 事件通过 `task_id` 精确匹配
- ✅ 更新 Jobs 数组时使用 `findIndex()` 定位

---

## 5. 验收报告模板

### 测试报告表头

```
============================================================
  Knowledge Jobs 页面 - 端到端测试验收报告
============================================================
测试日期: 2026-01-28
测试人员: [姓名]
环境信息:
  - 服务器: http://localhost:8000
  - 浏览器: Chrome 120.0.6099.109
  - 操作系统: macOS 14.2.1
  - 后端版本: AgentOS v0.3.2
  - 前端版本: Phase 3 完成
============================================================
```

### 场景测试结果表

| # | 场景 | 状态 | 耗时 | 备注 |
|---|------|------|------|------|
| 1 | 创建 Incremental Job | ⬜ Pass / ❌ Fail | ___s | |
| 2 | 创建 Rebuild Job | ⬜ Pass / ❌ Fail | ___s | |
| 3 | 创建 Repair Job | ⬜ Pass / ❌ Fail | ___s | |
| 4 | 创建 Vacuum Job | ⬜ Pass / ❌ Fail | ___s | |
| 5 | Refresh 列表 | ⬜ Pass / ❌ Fail | ___s | Jobs 数量: 前 ___ / 后 ___ |
| 6 | 并发 Jobs | ⬜ Pass / ❌ Fail | ___s | 并发数: ___ |
| 7 | Job 详情查看 | ⬜ Pass / ❌ Fail | ___s | |

### 详细测试记录

#### 场景 1: 创建 Incremental Job

**执行时间**: [HH:MM:SS]

**操作记录**:
1. [ ] 点击 Incremental 按钮
2. [ ] 观察 Toast 提示
3. [ ] 观察列表刷新
4. [ ] 监控状态流转

**状态流转记录**:
```
[时间戳] created (0%) - Initializing...
[时间戳] in_progress (5%) - Starting index operation...
[时间戳] in_progress (20%) - Scanning for changed files...
[时间戳] in_progress (90%) - Processed X files, Y chunks
[时间戳] completed (100%) - Index operation completed
```

**验收检查**:
- [ ] 按钮响应 < 500ms
- [ ] 状态完整流转
- [ ] 进度连续更新
- [ ] 无控制台错误
- [ ] WebSocket 事件接收

**结果**: ⬜ PASS / ❌ FAIL

**失败原因** (如果失败):
_______________________________________________________

---

#### 场景 2: 创建 Rebuild Job

**执行时间**: [HH:MM:SS]

**差异验证**:
- [ ] Type 徽章: 紫色 "Rebuild"
- [ ] Message: "Rebuilding entire index..."
- [ ] Files Processed: ___ (应 ≥ Incremental)
- [ ] Duration: ___s (应 > Incremental)

**结果**: ⬜ PASS / ❌ FAIL

---

#### 场景 3: 创建 Repair Job

**执行时间**: [HH:MM:SS]

**特殊验证**:
- [ ] Type 徽章: 橙色 "Repair"
- [ ] Message: "Checking index integrity..."
- [ ] Errors: ___ (如果有问题)

**结果**: ⬜ PASS / ❌ FAIL

---

#### 场景 4: 创建 Vacuum Job

**执行时间**: [HH:MM:SS]

**特殊验证**:
- [ ] Type 徽章: 绿色 "Vacuum"
- [ ] Message: "Cleaning up index..."
- [ ] Files/Chunks Cleaned: ___

**结果**: ⬜ PASS / ❌ FAIL

---

#### 场景 5: Refresh 列表

**执行时间**: [HH:MM:SS]

**关键验证**:
- 刷新前 Jobs 数量: ___
- 刷新后 Jobs 数量: ___
- [ ] 数量不变 (PASS) / ❌ 数量增加 (FAIL)

**结果**: ⬜ PASS / ❌ FAIL

---

#### 场景 6: 并发 Jobs

**执行时间**: [HH:MM:SS]

**并发测试**:
- 创建的 Jobs 数量: ___
- 同时运行的 Jobs: ___
- [ ] 所有 Jobs 独立更新
- [ ] 无状态冲突
- [ ] UI 无卡顿

**性能观察**:
- 内存使用: 开始 ___MB / 结束 ___MB
- CPU 使用: 峰值 ___%

**结果**: ⬜ PASS / ❌ FAIL

---

#### 场景 7: Job 详情查看

**执行时间**: [HH:MM:SS]

**Drawer 验证**:
- [ ] 点击 Job 行打开 Drawer
- [ ] 所有字段正确显示
- [ ] 实时更新 (如果 Job 进行中)
- [ ] 点击遮罩层关闭
- [ ] 点击 ✕ 按钮关闭

**结果**: ⬜ PASS / ❌ FAIL

---

### 发现的 Bug 列表

| Bug ID | 严重性 | 场景 | 描述 | 复现步骤 | 状态 |
|--------|--------|------|------|----------|------|
| BUG-001 | 🔴 高 / 🟡 中 / 🔵 低 | 场景 X | ... | 1. ... 2. ... | 🔍 新建 / 🔄 修复中 / ✅ 已修复 |
| | | | | | |
| | | | | | |

### 性能测试结果

| 指标 | 目标值 | 实测值 | 状态 |
|------|--------|--------|------|
| 按钮响应延迟 | < 500ms | ___ms | ⬜ / ❌ |
| 状态更新延迟 | < 3s | ___s | ⬜ / ❌ |
| 列表刷新延迟 | < 1s | ___s | ⬜ / ❌ |
| 轮询间隔 | 2s | ___s | ⬜ / ❌ |
| Drawer 动画 | 300ms | ___ms | ⬜ / ❌ |
| 内存增长 | < 50MB/分钟 | ___MB/分钟 | ⬜ / ❌ |

### 总体评分

**功能完整性**: ___ / 7 场景通过
**性能达标率**: ___ / 6 指标达标
**UI/UX 质量**: ___ / 10 分
**稳定性**: ___ / 10 分

**总体评分**: ___ / 100 分

**评分标准**:
- 90-100: 优秀，可以发布
- 80-89: 良好，minor 修复后可发布
- 70-79: 一般，需要修复主要问题
- < 70: 不合格，需要重大返工

---

### 验收结论

**验收结果**: ⬜ 通过 / ❌ 不通过 / ⏸ 有条件通过

**理由**:
_______________________________________________________
_______________________________________________________

**后续行动**:
- [ ] 修复 Bug-001
- [ ] 优化性能指标 X
- [ ] 补充测试覆盖场景 Y
- [ ] 更新文档

**签字**:
- 测试人员: ________________  日期: ________
- 审核人员: ________________  日期: ________

============================================================
报告结束
============================================================

---

## 6. 快速检查清单 (Quick Checklist)

### 30 秒快速验证

```
□ 服务器启动成功 (http://localhost:8000)
□ 访问 Knowledge → Jobs 页面
□ 点击 Incremental 按钮 → 出现 Toast 提示
□ 列表中出现新 Job，状态从 Pending → In Progress → Completed
□ 点击 Refresh 按钮 → Jobs 数量不变
□ 点击任意 Job 行 → 右侧 Drawer 打开
```

### 2 分钟核心功能验证

```
□ Incremental Job 创建成功并完成
□ Rebuild Job 创建成功并完成
□ Repair Job 创建成功并完成
□ Vacuum Job 创建成功并完成
□ Refresh 不创建新 Job
□ 并发 2 个 Jobs 同时运行无问题
□ Drawer 显示完整信息
□ WebSocket 连接正常（DevTools Console 无错误）
```

### 5 分钟完整验证

```
□ 完成 30 秒快速验证
□ 完成 2 分钟核心功能验证
□ 创建 4 个不同类型的 Jobs 并发运行
□ 验证进度条流畅更新
□ 验证状态徽章颜色正确
□ 验证 Files/Chunks 计数准确
□ 验证 Duration 格式化正确
□ 验证 Drawer 实时更新
□ 检查 Network 轮询间隔 = 2s
□ 检查 Console 无 JavaScript 错误
```

---

## 7. 附录

### A. 技术架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Frontend)                    │
├─────────────────────────────────────────────────────────┤
│  KnowledgeJobsView.js                                   │
│    ├─ Button Click Event Handlers                       │
│    ├─ DataTable Component (Jobs List)                   │
│    ├─ WebSocket Event Listener                          │
│    ├─ Auto Refresh Interval (2s)                        │
│    └─ Drawer Component (Job Details)                    │
└──────────────┬──────────────────────────┬────────────────┘
               │                          │
        HTTP POST/GET               WebSocket
               │                          │
┌──────────────▼──────────────────────────▼────────────────┐
│                FastAPI Server (Backend)                  │
├─────────────────────────────────────────────────────────┤
│  /api/knowledge/jobs (knowledge.py)                     │
│    ├─ POST /jobs → trigger_index_job()                  │
│    │   └─ TaskManager.create_task()                     │
│    │   └─ threading.Thread(_run_index_job)              │
│    ├─ GET /jobs → list_index_jobs()                     │
│    └─ GET /jobs/{id} → get_index_job()                  │
│                                                           │
│  /ws/events (ws_events.py)                              │
│    └─ WebSocket Connection                               │
│        └─ Event Bus → task.progress events               │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│            Background Index Thread                       │
├─────────────────────────────────────────────────────────┤
│  _run_index_job()                                       │
│    ├─ TaskManager.update_task() ← 修复后添加            │
│    ├─ Event Bus.emit(task.progress)                     │
│    ├─ ProjectKBService.refresh()                        │
│    └─ Event Bus.emit(task.completed)                    │
└─────────────────────────────────────────────────────────┘
```

### B. 状态机图

```
     [Button Click]
           │
           ▼
      ┌─────────┐
      │ created │ ← POST /api/knowledge/jobs
      │ (0%)    │
      └────┬────┘
           │ TaskManager.update_task()
           │ Event Bus: task.started
           ▼
   ┌──────────────┐
   │ in_progress  │ ← Thread started
   │ (5%)         │
   └──────┬───────┘
          │ Event Bus: task.progress (20%)
          ▼
   ┌──────────────┐
   │ in_progress  │ ← Scanning/Processing
   │ (20-90%)     │
   └──────┬───────┘
          │ Event Bus: task.progress (90%)
          ▼
   ┌──────────────┐
   │ in_progress  │ ← Finalizing
   │ (90%)        │
   └──────┬───────┘
          │ Event Bus: task.completed
          ▼
      ┌─────────┐
      │completed│
      │ (100%)  │
      └─────────┘
```

### C. 关键文件清单

**后端文件**:
```
/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/knowledge.py
  - trigger_index_job()    (Line 486-562)
  - _run_index_job()       (Line 627-738)
  - list_index_jobs()      (Line 416-482)
  - get_index_job()        (Line 566-624)
```

**前端文件**:
```
/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/KnowledgeJobsView.js
  - triggerJob()           (Line 305-330)
  - loadJobs()             (Line 288-303)
  - handleWebSocketMessage() (Line 214-238)
  - updateJobFromEvent()   (Line 240-286)
  - startAutoRefresh()     (Line 540-549)
```

**核心依赖**:
```
/Users/pangge/PycharmProjects/AgentOS/agentos/core/task.py
  - TaskManager.update_task() ← 关键修复
```

### D. 相关文档

- Phase 4 实现指南: `/Users/pangge/PycharmProjects/AgentOS/docs/implementation/PHASE4_README.md`
- API 文档: `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/api/knowledge.py` (Docstrings)
- 前端组件文档: 见各 View 文件头部注释

---

## 8. 测试日志示例

### 成功的测试日志

```
[2026-01-28 10:30:15] 测试开始
[2026-01-28 10:30:16] ✅ 服务器启动成功: http://localhost:8000
[2026-01-28 10:30:18] ✅ 访问 Jobs 页面成功
[2026-01-28 10:30:20] ✅ 点击 Incremental 按钮
[2026-01-28 10:30:20] ✅ Toast 提示: "incremental job triggered successfully"
[2026-01-28 10:30:21] ✅ Job 01HXYZ123 创建: status=created, progress=0%
[2026-01-28 10:30:23] ✅ 状态更新: status=in_progress, progress=5%
[2026-01-28 10:30:25] ✅ 状态更新: status=in_progress, progress=20%
[2026-01-28 10:30:32] ✅ 状态更新: status=in_progress, progress=90%
[2026-01-28 10:30:33] ✅ 状态更新: status=completed, progress=100%
[2026-01-28 10:30:33] ✅ Duration: 13s
[2026-01-28 10:30:33] ✅ Files: 15, Chunks: 245, Errors: 0
[2026-01-28 10:30:35] ✅ 场景 1 验收: PASS
```

### 失败的测试日志

```
[2026-01-28 10:35:15] 测试开始
[2026-01-28 10:35:16] ✅ 服务器启动成功
[2026-01-28 10:35:18] ✅ 访问 Jobs 页面成功
[2026-01-28 10:35:20] ✅ 点击 Incremental 按钮
[2026-01-28 10:35:20] ✅ Toast 提示正常
[2026-01-28 10:35:21] ✅ Job 01HXYZ456 创建: status=created
[2026-01-28 10:35:31] ❌ 状态未更新: 仍为 created (超过 10 秒)
[2026-01-28 10:35:31] ❌ 后端日志检查: 未找到 "Thread started"
[2026-01-28 10:35:31] ❌ 原因: 后台线程未启动
[2026-01-28 10:35:31] ❌ 场景 1 验收: FAIL
[2026-01-28 10:35:31] 🔧 需要检查 threading.Thread 启动逻辑
```

---

## 总结

本测试指南覆盖了 Knowledge Jobs 页面的所有核心功能和边缘场景。通过系统化的测试流程，确保该功能模块的质量、性能和用户体验达到生产级标准。

**关键验收点回顾**:
1. ✅ 4 种 Job 类型全部可用
2. ✅ 状态流转完整准确
3. ✅ 实时更新机制有效
4. ✅ 并发场景稳定
5. ✅ Refresh 不误触创建
6. ✅ Drawer 交互流畅

**下一步行动**:
- 执行完整测试并填写验收报告
- 修复发现的 Bug
- 优化性能瓶颈
- 准备生产环境部署

---

**文档维护**:
- 最后更新: 2026-01-28
- 维护人: AgentOS Team
- 版本: v1.0

如有问题或建议，请联系开发团队。
