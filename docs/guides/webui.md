# AgentOS WebUI - Control Surface

> **版本**: v0.3.0
> **状态**: M0-M3 完成

AgentOS WebUI 是一个基于 Web 的控制面板，提供可观察性和控制能力。

---

## 📋 功能概览

### 已实现功能 (v0.3.0)

#### M0: 骨架与健康
- ✅ FastAPI 服务器
- ✅ 静态页面布局
- ✅ Health API (`/api/health`)
- ✅ 实时健康状态监控

#### M1: Chat 接入
- ✅ WebSocket 聊天接口
- ✅ 流式消息输出
- ✅ 会话管理
- ✅ 消息历史记录

#### M2: Observability
- ✅ 系统概览 (Overview)
- ✅ 会话列表 (Sessions)
- ✅ 日志查询 (Logs)
- ✅ 实例信息 (Instances)

#### M3: Skills/Memory 接入
- ✅ Skills 列表
- ✅ Memory 搜索
- ✅ 配置查看

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 WebUI 依赖
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "websockets>=12.0" "psutil>=5.9.0"

# 或者重新安装 agentos
pip install -e .
```

### 2. 启动 WebUI

```bash
# 默认启动 (http://127.0.0.1:8080)
agentos web

# 自定义端口
agentos web --port 8888

# 绑定到所有网络接口
agentos web --host 0.0.0.0 --port 8080

# 开发模式 (自动重载)
agentos web --reload

# 调试模式
agentos web --log-level debug
```

### 3. 访问 WebUI

打开浏览器访问: **http://127.0.0.1:8080**

---

## 🎨 界面架构

### 左侧导航栏

```
📱 Chat
  └─ Chat          # 快速干预入口

🎛️ Control
  ├─ Overview      # 运行概览
  ├─ Sessions      # 会话列表
  └─ Logs          # 日志查询

🤖 Agent
  ├─ Skills        # 已加载 Skills
  └─ Memory        # 内存搜索

⚙️ Settings
  └─ Config        # 配置查看
```

### 顶部栏

- **Session Selector**: 切换当前会话
- **Health Badge**: 实时健康状态 (🟢 OK / 🟡 WARN / 🔴 DOWN)
- **Refresh Button**: 刷新当前视图

### 主内容区

根据左侧导航选择，显示不同的视图内容。

---

## 🔌 API 端点

### HTTP APIs

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 系统健康状态 |
| `/api/sessions` | GET | 列出所有会话 |
| `/api/sessions` | POST | 创建新会话 |
| `/api/sessions/{id}` | GET | 获取会话详情 |
| `/api/sessions/{id}/messages` | GET | 获取会话消息 |
| `/api/tasks` | GET | 列出任务 (支持过滤) |
| `/api/tasks/{id}` | GET | 获取任务详情 |
| `/api/events` | GET | 查询事件流 |
| `/api/skills` | GET | 列出 Skills |
| `/api/skills/{name}` | GET | 获取 Skill 详情 |
| `/api/memory/search` | GET | 搜索内存 |
| `/api/memory/upsert` | POST | 更新/插入内存 |
| `/api/memory/{id}` | GET | 获取内存详情 |
| `/api/config` | GET | 查看配置 (只读) |
| `/api/logs` | GET | 查询日志 |

### WebSocket APIs

| 端点 | 协议 | 描述 |
|------|------|------|
| `/ws/chat/{session_id}` | WebSocket | 实时聊天接口 |

---

## 💬 WebSocket 协议

### 客户端 → 服务器

```json
{
  "type": "user_message",
  "content": "你好，AgentOS",
  "metadata": {}
}
```

### 服务器 → 客户端

#### 助手消息 (流式)

```json
{
  "type": "assistant_message",
  "content": "你好",
  "chunk": true,
  "is_last": false,
  "metadata": {}
}
```

#### 工具调用

```json
{
  "type": "tool_call",
  "content": "正在调用工具...",
  "metadata": {
    "tool_name": "search",
    "args": {}
  }
}
```

#### 事件

```json
{
  "type": "event",
  "content": "message_completed",
  "metadata": {
    "message_id": "msg_123"
  }
}
```

#### 错误

```json
{
  "type": "error",
  "content": "错误信息"
}
```

---

## 🏗️ 架构设计

### 技术栈

**后端**:
- FastAPI - HTTP API 框架
- Uvicorn - ASGI 服务器
- WebSocket - 实时通信

**前端**:
- HTMX - 轻量级交互
- Tailwind CSS - 样式框架
- Vanilla JavaScript - 核心逻辑

**集成**:
- AgentOS Core - 任务管理、执行引擎
- MemoryOS - 内存管理系统

### 目录结构

```
agentos/webui/
├── __init__.py           # 模块初始化
├── app.py                # FastAPI 主应用
├── api/                  # API 路由
│   ├── __init__.py
│   ├── health.py         # 健康检查
│   ├── sessions.py       # 会话管理
│   ├── tasks.py          # 任务查询
│   ├── events.py         # 事件流
│   ├── skills.py         # Skills API
│   ├── memory.py         # Memory API
│   ├── config.py         # 配置 API
│   └── logs.py           # 日志 API
├── websocket/            # WebSocket 处理
│   ├── __init__.py
│   └── chat.py           # 聊天 WebSocket
├── static/               # 静态资源
│   ├── css/
│   │   └── main.css      # 自定义样式
│   └── js/
│       └── main.js       # 核心 JavaScript
└── templates/            # Jinja2 模板
    ├── index.html        # 主页
    └── health.html       # 健康检查页
```

### 数据流

```
用户浏览器
    ↓ HTTP/WebSocket
FastAPI App
    ↓ API 调用
AgentOS Core APIs
    ├─ TaskManager
    ├─ ChatEngine
    ├─ MemoryService
    └─ SkillRegistry
```

---

## 🔧 开发指南

### 本地开发

```bash
# 启动开发服务器 (自动重载)
agentos web --reload --log-level debug

# 访问健康检查页
curl http://localhost:8080/api/health

# 测试 WebSocket (使用 wscat)
npm install -g wscat
wscat -c ws://localhost:8080/ws/chat/main
```

### 添加新 API

1. 在 `agentos/webui/api/` 创建新模块
2. 定义 APIRouter 和端点
3. 在 `app.py` 中注册路由

示例:

```python
# agentos/webui/api/myapi.py
from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def my_endpoint():
    return {"message": "Hello"}

# agentos/webui/app.py
from agentos.webui.api import myapi
app.include_router(myapi.router, prefix="/api/myapi", tags=["myapi"])
```

### 添加新视图

1. 在 `static/js/main.js` 添加 `render*View()` 函数
2. 在 `loadView()` 的 switch 中添加 case
3. 在左侧导航添加菜单项

---

## 🎯 Roadmap

### v0.3.0 ✅ (当前版本)
- ✅ M0: 骨架与健康
- ✅ M1: Chat 接入
- ✅ M2: Observability
- ✅ M3: Skills/Memory 接入

### v0.4.0 (计划中)
- 🔄 任务执行控制 (暂停/恢复/取消)
- 🔄 实时事件流推送
- 🔄 Open Plan 可视化
- 🔄 审查门控 UI
- 🔄 多用户支持

### v0.5.0 (计划中)
- 🔄 Cron Jobs 管理
- 🔄 执行图可视化
- 🔄 性能监控面板
- 🔄 导出/导入配置

---

## 🐛 已知问题

1. **内存存储**: 当前使用内存存储会话和消息，重启后丢失
   - **计划**: 集成到 SQLite 数据库

2. **聊天集成**: 当前使用 Echo 占位，未集成真实 Chat Engine
   - **计划**: 集成 `agentos.core.chat`

3. **认证授权**: 无身份验证
   - **计划**: 添加可选的基础认证

---

## 📚 相关文档

- [v0.3.0 规划文档](../todos/v0.3.0.md)
- [功能清单](../功能清单.md)
- [AgentOS 架构文档](../architecture.md)

---

## 💡 提示

### 安全建议

- 默认绑定 `127.0.0.1`，仅本机访问
- 如需网络访问，使用 `--host 0.0.0.0`，但请确保网络安全
- 生产环境建议使用 Nginx 反向代理 + HTTPS

### 性能优化

- 使用 `uvicorn[standard]` 获得更好的性能 (已包含)
- 生产环境建议使用 gunicorn + uvicorn workers
- 考虑使用 Redis 替代内存存储

### 故障排查

**问题**: WebSocket 连接失败
- 检查防火墙设置
- 确认端口未被占用
- 查看浏览器控制台错误

**问题**: 健康检查显示 DOWN
- 检查数据库连接
- 查看后端日志: `agentos web --log-level debug`

---

**更新时间**: 2026-01-27
**维护者**: AgentOS Team
