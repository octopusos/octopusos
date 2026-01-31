# AgentOS WebUI 实现清单

> **版本**: 0.3.2 (v0.3.2 Closeout 完成)
> **生成日期**: 2026-01-27
> **对照文档**: `docs/功能清单.md` (第二十二章 WebUI 系统)
> **目的**: 追踪功能点从后端 API → 前端 UI 的实现状态

---

## 📋 状态图例

### 后端状态
- ✅ **API 完成** - 后端 API 已实现并可用
- ⏳ **API 待实现** - 后端 API 尚未实现

### 前端状态
- ✅ **UI 完成** - 前端界面已实现，用户可见可用
- 🔧 **UI 部分实现** - 前端界面部分实现，基础功能可用但待完善
- ⏳ **UI 待实现** - 前端界面未实现，但 API 已就绪
- ❌ **UI 缺失** - 前端界面未实现，且无计划实现（API 可能已存在）

---

## 一、核心框架 (M0: 骨架与健康)

### 1.1 FastAPI 主应用

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| FastAPI 应用初始化 | ✅ | - | `app.py` |
| 静态文件服务 | ✅ | ✅ | `/static` 挂载，CSS/JS 加载正常 |
| Jinja2 模板渲染 | ✅ | ✅ | `index.html`, `health.html` |
| 路由注册 | ✅ | - | 16 个 API 路由器已注册 |

**完成度**: 后端 100% | 前端 100%

---

### 1.2 Health API

**后端 API**: `GET /api/health` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 系统健康检查 | ✅ | ✅ | 健康检查页面 `/health-check` |
| 组件状态监控 | ✅ | ✅ | 显示 DB, 模型, 内存, KB 状态 |
| 进程指标收集 | ✅ | ✅ | 显示 PID, 内存占用, CPU 时间 |
| 实时轮询 | ✅ | ✅ | 5 秒自动刷新 |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- 主界面：顶部状态指示器（实时）
- 专用页面：`/health-check` 完整健康报告

---

## 二、Chat 接入 (M1)

### 2.1 WebSocket 聊天

**后端 WebSocket**: `/ws/chat/{session_id}` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 实时 WebSocket 连接 | ✅ | ✅ | WebSocket 连接正常 |
| 流式消息输出 | ✅ | ✅ | 支持 SSE 流式响应 |
| 连接管理器 | ✅ | ✅ | 断线重连机制 |
| 消息类型支持 | ✅ | ✅ | `text`, `tool_use`, `tool_result` |
| 错误处理 | ✅ | ✅ | 错误消息显示 |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- 主视图：Chat 界面（左侧导航 → Chat）
- 消息列表：滚动容器，自动滚动到底部
- 输入框：底部固定，支持回车发送

---

### 2.2 会话管理

**后端 API**:
- `GET /api/sessions` ✅
- `POST /api/sessions` ✅
- `GET /api/sessions/{session_id}` ✅
- `DELETE /api/sessions/{session_id}` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 会话 CRUD 操作 | ✅ | 🔧 | 后端完整，前端仅支持列表 + 切换 |
| 消息历史记录 | ✅ | ✅ | 消息持久化（SQLite） |
| 默认 main 会话 | ✅ | ✅ | 启动时自动创建 |
| 会话切换 | ✅ | ✅ | 顶部下拉选择器 |
| 会话创建 | ✅ | ⏳ | API 已就绪，前端未实现 UI |
| 会话删除 | ✅ | ⏳ | API 已就绪，前端未实现 UI |
| 会话重命名 | ✅ | ⏳ | API 已就绪，前端未实现 UI |

**完成度**: 后端 100% | 前端 60%

**UI 位置**:
- ✅ 会话切换：顶部下拉选择器
- ⏳ 会话管理：需要 Sessions 视图（创建/删除/重命名）

**待实现 UI**:
1. Sessions 视图（左侧导航新增）
2. 会话列表（卡片式布局）
3. 新建会话按钮
4. 会话操作菜单（重命名、删除）

---

## 三、Observability (M2)

### 3.1 任务查询 API

**后端 API**:
- `GET /api/tasks` ✅
- `GET /api/tasks/{task_id}` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 任务列表查询 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 任务详情查询 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 过滤和分页 | ✅ | ⏳ | 后端支持 limit/offset |
| 状态筛选 | ✅ | ⏳ | 后端支持 status 参数 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Tasks 视图（左侧导航新增）

**待实现 UI**:
1. Tasks 视图布局
2. 任务列表表格（ID, 状态, 创建时间, 更新时间）
3. 状态筛选器（pending, running, completed, failed）
4. 点击行展开详情
5. 分页控件

---

### 3.2 事件流 API

**后端 API**:
- `GET /api/events` ✅
- `GET /api/events/stream` ✅ (SSE)

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 事件查询 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 时间范围过滤 | ✅ | ⏳ | 支持 since/until 参数 |
| 内存事件存储 | ✅ | - | 最近 1000 条事件 |
| SSE 实时推送 | ✅ | ⏳ | 前端未实现 SSE 订阅 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Events 视图（左侧导航新增）

**待实现 UI**:
1. Events 视图布局
2. 事件时间线（时间戳 + 事件类型 + 内容）
3. 实时 SSE 订阅（自动追加新事件）
4. 时间范围选择器
5. 事件类型筛选器

---

### 3.3 日志查询 API

**后端 API**:
- `GET /api/logs` ✅
- `GET /api/logs/stream` ✅ (SSE)

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 结构化日志查询 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 多维度过滤 | ✅ | ⏳ | 支持 level/source/since 参数 |
| 日志级别筛选 | ✅ | ⏳ | DEBUG/INFO/WARNING/ERROR |
| SSE 实时推送 | ✅ | ⏳ | 前端未实现 SSE 订阅 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Logs 视图（左侧导航新增）

**待实现 UI**:
1. Logs 视图布局
2. 日志列表（时间戳 + 级别 + 来源 + 消息）
3. 日志级别筛选器（颜色编码）
4. 实时 SSE 订阅
5. 搜索框（消息内容搜索）
6. 自动滚动开关

---

## 四、Skills/Memory 接入 (M3)

### 4.1 Skills API

**后端 API**:
- `GET /api/skills` ✅
- `GET /api/skills/{skill_name}` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| Skills 列表查询 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| Skill 详情查询 | ✅ | ⏳ | 包含 schema 和 metadata |
| Schema 展示 | ✅ | ⏳ | JSON Schema 格式 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Skills 视图（左侧导航新增）

**待实现 UI**:
1. Skills 视图布局
2. Skill 卡片列表（名称 + 描述 + 状态）
3. 点击展开 Schema
4. Schema 可视化（JSON 树形展示）

---

### 4.2 Memory API

**后端 API**:
- `GET /api/memory/search` ✅
- `POST /api/memory/items` ✅
- `GET /api/memory/namespaces` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 内存搜索 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 内存写入 | ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 命名空间管理 | ✅ | ⏳ | 支持多命名空间隔离 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Memory 视图（左侧导航新增）

**待实现 UI**:
1. Memory 视图布局
2. 命名空间选择器
3. 搜索框 + 搜索结果列表
4. 新增记忆按钮
5. 记忆详情卡片（时间戳 + 内容 + metadata）

---

### 4.3 配置 API

**后端 API**:
- `GET /api/config` ✅
- `GET /api/config/env` ✅
- `GET /api/config/version` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 配置查看（只读）| ✅ | ⏳ | API 已就绪，前端未实现视图 |
| 环境变量展示 | ✅ | ⏳ | 敏感信息已脱敏 |
| 版本信息 | ✅ | ⏳ | Git SHA + 版本号 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Settings 视图（左侧导航新增）

**待实现 UI**:
1. Settings 视图布局
2. 配置项分类展示（系统配置、模型配置、路径配置）
3. 环境变量表格
4. 版本信息面板

---

## 五、Provider 管理 (Sprint B Task #4-6)

### 5.1 Provider 状态 API

**后端 API**:
- `GET /api/providers` ✅
- `GET /api/providers/status` ✅
- `GET /api/providers/{provider_id}/models` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| Provider 列表 | ✅ | ✅ | 本地 + 云端 Provider 元数据 |
| Provider 状态查询 | ✅ | ✅ | 健康检查 + 延迟监控 |
| 模型列表 | ✅ | ✅ | 支持 Ollama/OpenAI/Anthropic |
| 状态缓存（StatusStore）| ✅ | ✅ | 5 秒 TTL，减少重复探测 |
| 状态码标准化 | ✅ | ✅ | ReasonCode + hint（v0.3.2） |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- ✅ 主界面：顶部 Provider 状态栏（实时监控）
- ✅ Settings → Providers：Provider 管理面板

**UI 功能**:
1. ✅ 状态点指示（绿/黄/红/灰）
2. ✅ 红点脉冲动画（ERROR 状态）
3. ✅ Tooltip 显示 reason_code + hint
4. ✅ Last updated 时间戳
5. ✅ 延迟显示（ms）

---

### 5.2 本地 Provider 检测 (Task #4)

**后端 API**:
- `GET /api/providers/local/detect` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| CLI 检测 | ✅ | ✅ | 检测 `ollama`, `llama-server` 命令 |
| 服务可达性检测 | ✅ | ✅ | HTTP 健康检查 |
| 模型列表检测 | ✅ | ✅ | 显示可用模型数量 |
| 安装提示 | ✅ | ✅ | 未安装时显示安装链接 |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- ✅ Settings → Providers → Local 标签页

---

### 5.3 Ollama 运行时管理 (Task #5)

**后端 API**:
- `POST /api/providers/ollama/start` ✅
- `POST /api/providers/ollama/stop` ✅
- `POST /api/providers/ollama/restart` ✅
- `GET /api/providers/ollama/runtime` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 启动 Ollama 服务 | ✅ | ✅ | `ollama serve` 后台运行 |
| 停止 Ollama 服务 | ✅ | ✅ | SIGTERM + SIGKILL 清理 |
| 重启 Ollama 服务 | ✅ | ✅ | 先停止再启动 |
| 运行时状态查询 | ✅ | ✅ | PID + 启动时间 + 命令 |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- ✅ Settings → Providers → Local → Ollama 卡片
- ✅ Start/Stop/Restart 按钮
- ✅ 运行状态指示器

---

### 5.4 Cloud Provider 配置 (Task #6)

**后端 API**:
- `POST /api/providers/cloud/config` ✅
- `POST /api/providers/cloud/test` ✅
- `DELETE /api/providers/cloud/config/{provider_id}` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| API Key 配置 | ✅ | ✅ | 保存到 `~/.agentos/secrets/providers.json` |
| Base URL 配置 | ✅ | ✅ | 支持自定义端点 |
| 连接测试 | ✅ | ✅ | 实时验证 API Key |
| 配置删除 | ✅ | ✅ | 清除已保存凭证 |
| 文件权限（chmod 600）| ✅ | ✅ | 安全存储凭证 |
| API Key 脱敏 | ✅ | ✅ | 响应中自动 mask |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- ✅ Settings → Providers → Cloud 标签页
- ✅ OpenAI / Anthropic 配置卡片
- ✅ API Key 输入框（type=password）
- ✅ Test Connection 按钮
- ✅ Clear Config 按钮

---

## 六、Self-check 系统 (Sprint B Task #7)

### 6.1 Self-check API

**后端 API**:
- `POST /api/selfcheck` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 运行时检查 | ✅ | ✅ | 版本、路径、权限 |
| Provider 检查 | ✅ | ✅ | 本地 + 云端状态（使用缓存）|
| Context 检查 | ✅ | ✅ | 内存存储、RAG、会话绑定 |
| 可选网络探测 | ✅ | ✅ | `include_network` 参数控制 |
| 可操作 actions | ✅ | ✅ | 一键修复按钮 |

**完成度**: 后端 100% | 前端 100%

**UI 位置**:
- ✅ Settings → Self-check 标签页
- ✅ Run Check 按钮
- ✅ 检查项列表（分组：runtime, providers, context）
- ✅ 状态图标（✓ PASS, ⚠ WARN, ✗ FAIL）
- ✅ FAIL 项红点脉冲动画（v0.3.2）
- ✅ Hint 提示（💡）
- ✅ 可操作按钮（如 Start Ollama）

**UI 功能**:
1. ✅ 汇总统计（OK/WARN/FAIL 数量）
2. ✅ 筛选器（All/Pass/Warn/Fail）
3. ✅ 空状态引导（v0.3.2）
4. ✅ 实时 Actions（POST API 调用）

---

## 七、Context 管理 (Sprint B Task #8)

### 7.1 Context API

**后端 API**:
- `GET /api/context/status` ✅
- `POST /api/context/attach` ✅
- `POST /api/context/detach` ✅
- `POST /api/context/refresh` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| Context 状态查询 | ✅ | ⏳ | State/Tokens/RAG/Memory |
| Memory 附加 | ✅ | ⏳ | 绑定内存命名空间 |
| RAG 附加 | ✅ | ⏳ | 绑定 RAG 索引 |
| Context 分离 | ✅ | ⏳ | 解绑所有 context |
| Context 刷新 | ✅ | ⏳ | 重建 RAG/同步内存 |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要 Context 视图（左侧导航新增）

**待实现 UI**:
1. Context 视图布局
2. 当前会话 Context 状态卡片
   - State 指示器（EMPTY/ATTACHED/BUILDING/STALE/ERROR）
   - Token 统计（prompt/completion/context window）
   - RAG 状态（enabled/index/last_refresh）
   - Memory 状态（enabled/namespace/last_write）
3. Attach Context 表单
   - Memory 开关 + namespace 输入
   - RAG 开关 + index 输入
4. Refresh 按钮
5. Detach 按钮

---

## 八、Runtime 管理 (v0.3.2 Closeout)

### 8.1 Runtime API

**后端 API**:
- `POST /api/runtime/fix-permissions` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 权限修复 | ✅ | ⏳ | 修复 secrets 文件权限（600）|

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ⏳ 可集成到 Self-check 的 runtime.permissions 检查项
- ⏳ 或添加到 Settings → System 面板

**待实现 UI**:
1. 权限状态指示器
2. Fix Permissions 按钮
3. 修复结果提示

---

## 九、Support 支持 (v0.3.2 Closeout)

### 9.1 Diagnostic Bundle API

**后端 API**:
- `GET /api/support/diagnostic-bundle` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| 诊断数据收集 | ✅ | ⏳ | 系统信息 + Provider 状态 + Self-check |
| 数据脱敏 | ✅ | - | API Key 自动 mask |

**完成度**: 后端 100% | 前端 0%

**UI 位置**:
- ❌ 需要添加到 Settings 或 Help 菜单

**待实现 UI**:
1. "Download Diagnostic Bundle" 按钮
2. 下载 JSON 文件
3. 可选：预览诊断数据（可折叠 JSON 树）

---

## 十、Secrets 管理 (Sprint B Task #6)

### 10.1 Secrets API

**后端 API**:
- `POST /api/secrets` ✅
- `GET /api/secrets/{provider_id}` ✅
- `DELETE /api/secrets/{provider_id}` ✅
- `POST /api/secrets/test` ✅

| 功能点 | 后端 | 前端 | 说明 |
|--------|------|------|------|
| Secret 保存 | ✅ | ✅ | 集成到 Cloud Provider 配置 |
| Secret 查询 | ✅ | ✅ | 用于回显（masked）|
| Secret 删除 | ✅ | ✅ | 清除凭证 |
| Secret 测试 | ✅ | ✅ | 验证凭证有效性 |

**完成度**: 后端 100% | 前端 100% (集成在 Providers 中)

**说明**: Secrets API 已通过 Cloud Provider 配置 UI 完全覆盖，无需单独视图。

---

## 前端视图完成度总览

| 视图名称 | 后端 API | 前端 UI | 完成度 | 优先级 |
|---------|---------|---------|--------|--------|
| **Chat** | ✅ | ✅ | 100% | ✅ M1 |
| **Health** | ✅ | ✅ | 100% | ✅ M0 |
| **Settings → Providers** | ✅ | ✅ | 100% | ✅ Sprint B |
| **Settings → Self-check** | ✅ | ✅ | 100% | ✅ Sprint B |
| Sessions | ✅ | 🔧 | 60% | P1 |
| Tasks | ✅ | ⏳ | 0% | P2 |
| Events | ✅ | ⏳ | 0% | P2 |
| Logs | ✅ | ⏳ | 0% | P2 |
| Skills | ✅ | ⏳ | 0% | P3 |
| Memory | ✅ | ⏳ | 0% | P3 |
| Context | ✅ | ⏳ | 0% | P2 |
| Settings → Config | ✅ | ⏳ | 0% | P3 |
| Settings → Support | ✅ | ⏳ | 0% | P3 |

---

## 待实现 UI 清单（按优先级排序）

### P1 - 高优先级（影响核心用户体验）

#### 1. Sessions 视图完善 ✨ P1
**当前状态**: 🔧 部分实现（仅支持切换，不支持 CRUD）

**待实现功能**:
1. Sessions 视图布局（左侧导航新增）
2. 会话列表（卡片式，显示标题 + 最后消息时间 + 消息数量）
3. 新建会话按钮（弹窗输入标题）
4. 会话操作菜单（重命名、删除、归档）
5. 会话搜索（按标题搜索）

**API 就绪**:
- ✅ `GET /api/sessions`
- ✅ `POST /api/sessions`
- ✅ `DELETE /api/sessions/{session_id}`
- ✅ `PATCH /api/sessions/{session_id}` (重命名)

**UI 设计建议**:
```
┌─────────────────────────────────────┐
│ Sessions                      [+]   │  ← 新建按钮
├─────────────────────────────────────┤
│ 🔍 Search sessions...               │
├─────────────────────────────────────┤
│ ┌─────────────────────────────┐    │
│ │ 📝 Main Session             │    │
│ │ 5 messages · 2 hours ago    │ [⋮] │ ← 操作菜单
│ └─────────────────────────────┘    │
│ ┌─────────────────────────────┐    │
│ │ 💬 Debug Session            │    │
│ │ 12 messages · 1 day ago     │ [⋮] │
│ └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

**预计工作量**: 2-3 天

---

### P2 - 中优先级（提升可观测性）

#### 2. Tasks 视图 ✨ P2
**当前状态**: ⏳ 待实现

**待实现功能**:
1. Tasks 视图布局
2. 任务列表表格（Task ID, Status, Session, Created, Updated）
3. 状态筛选器（All/Pending/Running/Completed/Failed）
4. 行点击展开详情（显示 lineage, metadata, 执行计划）
5. 分页控件（limit/offset）

**API 就绪**:
- ✅ `GET /api/tasks?limit=50&offset=0&status=running`
- ✅ `GET /api/tasks/{task_id}`

**UI 设计建议**:
```
┌────────────────────────────────────────────────────┐
│ Tasks                                              │
├────────────────────────────────────────────────────┤
│ [All] [Pending] [Running] [Completed] [Failed]    │ ← 筛选器
├────┬──────────┬─────────┬──────────┬─────────────┤
│ ID │ Status   │ Session │ Created  │ Updated     │
├────┼──────────┼─────────┼──────────┼─────────────┤
│ 1  │ 🟢 DONE  │ main    │ 2h ago   │ 1h ago      │
│ 2  │ 🟡 RUN   │ debug   │ 5m ago   │ 2m ago      │
│ 3  │ ⚪ NEW   │ main    │ 10m ago  │ 10m ago     │
└────┴──────────┴─────────┴──────────┴─────────────┘
```

**预计工作量**: 3-4 天

---

#### 3. Events 视图 ✨ P2
**当前状态**: ⏳ 待实现

**待实现功能**:
1. Events 视图布局
2. 事件时间线（时间戳 + 事件类型 + 详情）
3. SSE 实时订阅（`/api/events/stream`）
4. 事件类型筛选器（System/Task/Provider/Chat）
5. 时间范围选择器（Last 1h / Last 24h / Custom）
6. 自动滚动开关

**API 就绪**:
- ✅ `GET /api/events?since=2026-01-27T00:00:00Z`
- ✅ `GET /api/events/stream` (SSE)

**UI 设计建议**:
```
┌────────────────────────────────────────────────────┐
│ Events                            [Auto-scroll: ON] │
├────────────────────────────────────────────────────┤
│ [System] [Task] [Provider] [Chat]  [Last 1h ▾]    │
├────────────────────────────────────────────────────┤
│ ●──────────────────────────────────────────────────│
│ │ 10:30:45  [Task] Task #42 completed              │
│ │                                                   │
│ │ 10:29:12  [Provider] Ollama status: READY (45ms) │
│ │                                                   │
│ │ 10:28:03  [Chat] New message in session 'main'   │
│ └───────────────────────────────────────────────── │
```

**预计工作量**: 2-3 天

---

#### 4. Logs 视图 ✨ P2
**当前状态**: ⏳ 待实现

**待实现功能**:
1. Logs 视图布局
2. 日志列表（时间戳 + 级别 + 来源 + 消息）
3. 日志级别筛选器（DEBUG/INFO/WARNING/ERROR）
4. SSE 实时订阅（`/api/logs/stream`）
5. 来源筛选器（API/Core/WebUI/CLI）
6. 消息搜索框
7. 自动滚动开关

**API 就绪**:
- ✅ `GET /api/logs?level=ERROR&source=api`
- ✅ `GET /api/logs/stream` (SSE)

**UI 设计建议**:
```
┌────────────────────────────────────────────────────┐
│ Logs                              [Auto-scroll: ON] │
├────────────────────────────────────────────────────┤
│ [DEBUG] [INFO] [WARN] [ERROR]     [All sources ▾]  │
│ 🔍 Search logs...                                  │
├────────────────────────────────────────────────────┤
│ 10:30:45 ERROR [api] Failed to connect to provider │
│ 10:29:12 INFO  [core] Task #42 started             │
│ 10:28:03 DEBUG [webui] WebSocket connected         │
└────────────────────────────────────────────────────┘
```

**预计工作量**: 2-3 天

---

#### 5. Context 视图 ✨ P2
**当前状态**: ⏳ 待实现

**待实现功能**:
1. Context 视图布局
2. 当前 Context 状态卡片（State/Tokens/RAG/Memory）
3. Attach Context 表单
4. Refresh 按钮
5. Detach 按钮

**API 就绪**:
- ✅ `GET /api/context/status?session_id=main`
- ✅ `POST /api/context/attach`
- ✅ `POST /api/context/refresh`
- ✅ `POST /api/context/detach`

**UI 设计建议**:
```
┌────────────────────────────────────────────────────┐
│ Context - Session: main                            │
├────────────────────────────────────────────────────┤
│ State: 🟢 ATTACHED          [Refresh] [Detach]    │
├────────────────────────────────────────────────────┤
│ Token Usage:                                       │
│   Prompt:     1,250 / 200,000                     │
│   Completion:   350 / 200,000                     │
│   Window:     1,600 / 200,000 (0.8%)              │
├────────────────────────────────────────────────────┤
│ Memory:                                            │
│   ✅ Enabled                                       │
│   Namespace: main                                  │
│   Last Write: 5 minutes ago                        │
├────────────────────────────────────────────────────┤
│ RAG:                                               │
│   ⚪ Disabled                    [Enable]          │
└────────────────────────────────────────────────────┘
```

**预计工作量**: 2-3 天

---

### P3 - 低优先级（锦上添花）

#### 6. Skills 视图 ✨ P3
**预计工作量**: 1-2 天

#### 7. Memory 视图 ✨ P3
**预计工作量**: 2-3 天

#### 8. Settings → Config 视图 ✨ P3
**预计工作量**: 1 天

#### 9. Settings → Support 视图 ✨ P3
**待实现功能**:
- Download Diagnostic Bundle 按钮
- 诊断数据预览

**预计工作量**: 0.5 天

---

## 技术栈汇总

### 后端技术
- **框架**: FastAPI 0.100+
- **WebSocket**: FastAPI WebSocket + SSE
- **数据库**: SQLite 3 (SessionStore)
- **安全**: Response sanitization (v0.3.2)
- **缓存**: StatusStore (TTL-based, v0.3.2)

### 前端技术
- **模板**: Jinja2
- **样式**: Tailwind CSS
- **脚本**: Vanilla JavaScript (ES6+)
- **通信**: WebSocket + Fetch API + SSE (部分)

### 部署
- **命令**: `agentos webui` / `agentos webui start`
- **端口**: 默认 8000
- **模式**: 开发模式（`--reload`）+ 生产模式

---

## 总结统计

### 完成度分析（v0.3.2）

| 分类 | API 完成 | UI 完成 | 完成度 |
|------|----------|---------|--------|
| **核心功能（M0-M1）** | 100% | 100% | ✅ 完成 |
| **Sprint B (Task #4-7)** | 100% | 100% | ✅ 完成 |
| **v0.3.2 Closeout** | 100% | 20% | 🔧 部分完成 |
| **M2-M3 扩展功能** | 100% | 10% | ⏳ 大量待实现 |

### 按功能模块统计

| 模块 | API | UI | 说明 |
|------|-----|-----|------|
| Chat | ✅ 100% | ✅ 100% | 完整实现 |
| Sessions | ✅ 100% | 🔧 60% | CRUD 待完善 |
| Health | ✅ 100% | ✅ 100% | 完整实现 |
| Providers | ✅ 100% | ✅ 100% | 完整实现（Sprint B）|
| Self-check | ✅ 100% | ✅ 100% | 完整实现（Sprint B）|
| Tasks | ✅ 100% | ⏳ 0% | 待实现 |
| Events | ✅ 100% | ⏳ 0% | 待实现 |
| Logs | ✅ 100% | ⏳ 0% | 待实现 |
| Skills | ✅ 100% | ⏳ 0% | 待实现 |
| Memory | ✅ 100% | ⏳ 0% | 待实现 |
| Context | ✅ 100% | ⏳ 0% | 待实现 |
| Config | ✅ 100% | ⏳ 0% | 待实现 |
| Runtime | ✅ 100% | ⏳ 0% | 待实现 |
| Support | ✅ 100% | ⏳ 0% | 待实现 |

### 总体完成度

- **后端 API**: 100% (所有规划的 API 已实现)
- **前端 UI**: 42% (核心功能 + Sprint B 完成，扩展功能待实现)
- **整体完成度**: 71% (加权平均，核心功能权重更高)

### 剩余工作量估算

| 优先级 | 视图数量 | 预计工作量 | 说明 |
|--------|---------|-----------|------|
| P1 | 1 个 | 2-3 天 | Sessions 视图完善 |
| P2 | 4 个 | 10-13 天 | Tasks, Events, Logs, Context |
| P3 | 4 个 | 5-7 天 | Skills, Memory, Config, Support |
| **总计** | **9 个** | **17-23 天** | 约 3-4 周（单人工作量）|

---

## 下一步建议

### 短期目标（1-2 周）
1. ✅ **P1: Sessions 视图完善**
   - 实现会话 CRUD UI
   - 优化会话切换体验

2. ✅ **P2: Tasks 视图**
   - 实现任务列表和详情
   - 提升系统可观测性

### 中期目标（3-4 周）
3. ✅ **P2: Events + Logs 视图**
   - 实现实时事件流
   - 实现日志监控

4. ✅ **P2: Context 视图**
   - 实现 Context 管理 UI
   - 完成 Memory/RAG 绑定

### 长期目标（1-2 月）
5. ✅ **P3: Skills + Memory 视图**
   - 实现 Skills 管理
   - 实现 Memory 搜索和写入

6. ✅ **P3: 配置和支持**
   - 实现配置查看
   - 实现诊断数据下载

---

**文档生成时间**: 2026-01-27
**下次更新建议**: 每完成一个视图后更新状态
