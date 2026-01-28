# AgentOS WebUI

> **v0.3.0 Control Surface** - Web-based observability and control interface for AgentOS

一个基于 FastAPI + HTMX + Tailwind CSS 的轻量级 Web 控制台。

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install "fastapi>=0.109.0" "uvicorn[standard]>=0.27.0" "websockets>=12.0" "psutil>=5.9.0"
```

### 2. 启动 WebUI

```bash
agentos web
```

### 3. 访问

打开浏览器: **http://127.0.0.1:8080**

---

## 📦 功能列表

### ✅ 已实现 (v0.3.0)

**M0: 骨架与健康**
- FastAPI 服务器
- Health API
- 实时健康监控

**M1: Chat 接入**
- WebSocket 聊天
- 流式消息输出
- 会话管理

**M2: Observability**
- 系统概览
- 任务查询
- 事件流
- 日志查询

**M3: Skills/Memory**
- Skills 列表
- Memory 搜索
- 配置查看

---

## 🏗️ 架构

```
agentos/webui/
├── app.py              # FastAPI 主应用
├── api/                # HTTP API 路由
│   ├── health.py       # 健康检查
│   ├── sessions.py     # 会话管理
│   ├── tasks.py        # 任务查询
│   ├── events.py       # 事件流
│   ├── skills.py       # Skills
│   ├── memory.py       # Memory
│   ├── config.py       # 配置
│   └── logs.py         # 日志
├── websocket/          # WebSocket 处理
│   └── chat.py         # 聊天 WebSocket
├── static/             # 静态资源
│   ├── css/main.css    # 样式
│   └── js/main.js      # JavaScript
└── templates/          # Jinja2 模板
    ├── index.html      # 主页
    └── health.html     # 健康检查
```

---

## 📖 API 文档

访问 **http://127.0.0.1:8080/docs** 查看完整的 API 文档 (FastAPI 自动生成)。

---

## 🔧 开发

```bash
# 开发模式 (自动重载)
agentos web --reload --log-level debug

# 自定义端口
agentos web --port 8888

# 绑定所有网络接口
agentos web --host 0.0.0.0
```

---

## 📚 详细文档

查看完整文档: [docs/guides/webui.md](../../docs/guides/webui.md)

---

## 🎯 Roadmap

- [x] M0: 骨架与健康
- [x] M1: Chat 接入
- [x] M2: Observability
- [x] M3: Skills/Memory 接入
- [ ] v0.4: 任务控制、实时推送
- [ ] v0.5: Cron Jobs、执行图可视化

---

**技术栈**: FastAPI · Uvicorn · WebSocket · HTMX · Tailwind CSS
