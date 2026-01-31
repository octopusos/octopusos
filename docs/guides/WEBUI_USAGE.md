# AgentOS WebUI 使用指南

> **完整的 WebUI 使用说明** - 从安装到高级配置

---

## 📚 目录

1. [简介](#简介)
2. [安装](#安装)
3. [自动启动](#自动启动)
4. [手动管理](#手动管理)
5. [配置管理](#配置管理)
6. [界面功能](#界面功能)
7. [命令参考](#命令参考)
8. [故障排查](#故障排查)
9. [高级用法](#高级用法)

---

## 简介

AgentOS WebUI 是一个基于 Web 的控制台，提供：

- 🎯 **Chat 界面** - 实时聊天和命令执行
- 📊 **Observability** - 任务、事件、日志查询
- 🤖 **Agent 管理** - Skills 和 Memory 查看
- ⚙️ **配置管理** - 系统配置查看

**关键特性**:
- ✅ **自动启动** - 运行任何命令自动启动 WebUI
- ✅ **后台运行** - 不阻塞主命令
- ✅ **实时通信** - WebSocket 流式消息
- ✅ **零配置** - 开箱即用

---

## 安装

### 1. 安装 AgentOS

```bash
# 克隆仓库
git clone https://github.com/yourorg/agentos.git
cd agentos

# 安装
pip install -e .
```

### 2. 验证安装

```bash
# 检查版本
agentos --version

# 检查 WebUI 命令
agentos webui --help
```

---

## 自动启动

### 工作原理

AgentOS **默认启用自动启动**。当你运行任何 CLI 命令时，WebUI 会自动在后台启动（如果尚未运行）。

### 使用方法

**只需运行任何命令**：

```bash
# 运行任何命令
agentos task list

# WebUI 已自动启动！
```

**访问 WebUI**：

```bash
open http://127.0.0.1:8080
```

### 验证状态

```bash
agentos webui status
```

输出：
```
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property ┃ Value                      ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Running  │ ✅ Yes                     │
│ PID      │ 12345                      │
│ URL      │ http://127.0.0.1:8080      │
│ Host     │ 127.0.0.1                  │
│ Port     │ 8080                       │
│ Log File │ ~/.agentos/webui.log       │
└──────────┴────────────────────────────┘
```

---

## 手动管理

除了自动启动，你也可以手动管理 WebUI。

### 后台启动

```bash
agentos webui start
```

### 停止服务

```bash
agentos webui stop
```

### 重启服务

```bash
agentos webui restart
```

### 前台运行（开发模式）

```bash
agentos web --reload --log-level debug
```

---

## 配置管理

### 查看配置

```bash
agentos webui config --show
```

输出：
```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Setting    ┃ Value        ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ Auto-start │ ✅ Enabled   │
│ Host       │ 127.0.0.1    │
│ Port       │ 8080         │
└────────────┴──────────────┘
```

### 启用/禁用自动启动

```bash
# 禁用
agentos webui config --no-auto-start

# 启用
agentos webui config --auto-start
```

### 修改主机和端口

```bash
# 修改端口
agentos webui config --port 8888

# 修改主机
agentos webui config --host 0.0.0.0

# 同时修改
agentos webui config --host 0.0.0.0 --port 8888
```

### 配置文件

配置存储在 `~/.agentos/settings.json`:

```json
{
  "webui_auto_start": true,
  "webui_host": "127.0.0.1",
  "webui_port": 8080,
  ...
}
```

---

## 界面功能

### 主界面布局

```
┌─────────────────────────────────────────────────────────┐
│  AgentOS v0.3.0              [Session: main] [🟢 OK] [↻] │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  📱 Chat │                                              │
│  Chat    │          主内容区域                          │
│          │         (根据左侧选择动态变化)                │
│  🎛️ Ctrl │                                              │
│  Overvw  │                                              │
│  Sessns  │                                              │
│  Logs    │                                              │
│          │                                              │
│  🤖 Agnt │                                              │
│  Skills  │                                              │
│  Memory  │                                              │
│          │                                              │
│  ⚙️ Sets │                                              │
│  Config  │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 左侧导航

#### Chat 区域
- **Chat** - 实时聊天界面

#### Control 区域
- **Overview** - 系统概览
- **Sessions** - 会话列表
- **Logs** - 日志查询

#### Agent 区域
- **Skills** - 已加载 Skills
- **Memory** - 内存搜索

#### Settings 区域
- **Config** - 配置查看

### 顶部控制栏

- **Session Selector** - 切换会话
- **Health Badge** - 实时健康状态
  - 🟢 OK - 正常
  - 🟡 WARN - 警告
  - 🔴 DOWN - 故障
- **Refresh Button** - 刷新当前视图

### 功能详解

#### 1. Chat 聊天

**使用方法**:
1. 在输入框输入消息
2. 按 `Enter` 发送（`Shift+Enter` 换行）
3. 观察流式响应

**功能**:
- 流式消息输出
- 消息历史记录
- 多会话支持

#### 2. Skills 管理

**查看 Skills**:
- Skills 列表
- 版本信息
- 执行状态
- Input/Output Schema

#### 3. Memory 搜索

**搜索内存**:
- 关键词搜索
- 命名空间过滤
- 来源追踪

#### 4. Logs 日志

**查询日志**:
- 日志级别过滤
- 时间范围筛选
- 任务/会话关联

---

## 命令参考

### agentos web

前台启动 WebUI（原方式）。

```bash
agentos web [OPTIONS]
```

**选项**:
- `--host TEXT` - 绑定主机 (默认: 127.0.0.1)
- `--port INT` - 绑定端口 (默认: 8080)
- `--reload` - 启用自动重载（开发模式）
- `--log-level LEVEL` - 日志级别 (debug/info/warning/error)

**示例**:
```bash
# 默认启动
agentos web

# 自定义端口
agentos web --port 8888

# 开发模式
agentos web --reload --log-level debug
```

### agentos webui start

后台启动 WebUI。

```bash
agentos webui start [OPTIONS]
```

**选项**:
- `--host TEXT` - 绑定主机
- `--port INT` - 绑定端口
- `--foreground` - 前台运行

**示例**:
```bash
# 使用配置启动
agentos webui start

# 自定义端口
agentos webui start --port 8888

# 前台运行
agentos webui start --foreground
```

### agentos webui stop

停止 WebUI。

```bash
agentos webui stop
```

### agentos webui restart

重启 WebUI。

```bash
agentos webui restart
```

### agentos webui status

查看 WebUI 状态。

```bash
agentos webui status
```

### agentos webui config

管理配置。

```bash
agentos webui config [OPTIONS]
```

**选项**:
- `--show` - 显示当前配置
- `--auto-start` - 启用自动启动
- `--no-auto-start` - 禁用自动启动
- `--host TEXT` - 设置主机
- `--port INT` - 设置端口

**示例**:
```bash
# 查看配置
agentos webui config --show

# 禁用自动启动
agentos webui config --no-auto-start

# 修改端口
agentos webui config --port 8888
```

---

## 故障排查

### 问题 1: WebUI 未自动启动

**症状**: 运行命令后 WebUI 没有启动。

**排查步骤**:

1. 检查配置:
```bash
agentos webui config --show
```

2. 确认 Auto-start: Enabled

3. 手动启动测试:
```bash
agentos webui start --foreground
```

4. 查看错误日志:
```bash
tail -f ~/.agentos/webui.log
```

### 问题 2: 端口被占用

**症状**: 启动失败，提示 "Address already in use"。

**解决方案**:

1. 检查端口占用:
```bash
lsof -i :8080
```

2. 修改端口:
```bash
agentos webui config --port 8888
agentos webui restart
```

### 问题 3: 无法访问 WebUI

**症状**: 浏览器无法打开 WebUI。

**排查步骤**:

1. 检查服务状态:
```bash
agentos webui status
```

2. 测试健康检查 API:
```bash
curl http://127.0.0.1:8080/api/health
```

3. 检查防火墙:
```bash
# macOS
sudo pfctl -s rules

# Linux
sudo iptables -L
```

4. 查看日志:
```bash
tail -n 100 ~/.agentos/webui.log
```

### 问题 4: 进程僵死

**症状**: WebUI 无响应，无法停止。

**解决方案**:

1. 查找 PID:
```bash
cat ~/.agentos/webui.pid
```

2. 强制杀死:
```bash
kill -9 <PID>
```

3. 清理 PID 文件:
```bash
rm ~/.agentos/webui.pid
```

4. 重新启动:
```bash
agentos webui start
```

---

## 高级用法

### 远程访问

**场景**: 需要从其他机器访问 WebUI。

**配置**:
```bash
# 监听所有接口
agentos webui config --host 0.0.0.0

# 重启
agentos webui restart

# 通过 IP 访问
open http://192.168.1.100:8080
```

⚠️ **安全警告**: 仅在受信任网络使用 `0.0.0.0`。

### 生产部署

**推荐配置**:

1. 使用反向代理（Nginx）:
```nginx
server {
    listen 80;
    server_name agentos.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

2. 启用 HTTPS

3. 配置防火墙

### 多实例运行

**场景**: 同一机器运行多个 AgentOS 实例。

**方法**:
```bash
# 禁用自动启动
agentos webui config --no-auto-start

# 手动启动多个实例
agentos webui start --port 8080
agentos webui start --port 8081
agentos webui start --port 8082
```

注意: 每个实例需要不同的端口。

### 开发调试

**方法 1: 前台运行**:
```bash
agentos web --reload --log-level debug
```

**方法 2: 查看日志**:
```bash
tail -f ~/.agentos/webui.log
```

**方法 3: 测试 API**:
```bash
# 测试健康检查
curl http://127.0.0.1:8080/api/health

# 测试 Sessions
curl http://127.0.0.1:8080/api/sessions

# 测试 Skills
curl http://127.0.0.1:8080/api/skills
```

---

## 相关资源

### 文档

- [WebUI 快速上手](./docs/guides/webui-quickstart.md) - 3 分钟快速体验
- [WebUI 完整指南](./docs/guides/webui.md) - 详细功能说明
- [自动启动配置](./docs/guides/webui-autostart.md) - 高级配置
- [API 文档](./docs/guides/api.md) - REST API 参考

### 测试工具

- `scripts/test_webui.py` - API 功能测试
- `scripts/test_auto_start.sh` - 自动启动测试

### 源代码

- `agentos/webui/` - WebUI 源代码
- `agentos/cli/webui_control.py` - 控制命令
- `agentos/webui/daemon.py` - 后台服务管理

---

## 总结

AgentOS WebUI 提供了强大的 Web 控制台功能：

- ✅ **自动启动** - 运行任何命令自动启动
- ✅ **后台运行** - 不阻塞主命令
- ✅ **完整管理** - 启动/停止/重启/配置
- ✅ **实时通信** - WebSocket 流式消息
- ✅ **丰富功能** - Chat/Tasks/Skills/Memory

立即开始使用：
```bash
agentos task list
open http://127.0.0.1:8080
```

---

**AgentOS Team** | v0.3.0 | 2026-01-27
