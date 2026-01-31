# Agent2 快速启动指南

本指南将帮助你快速启动并验证 Agent2 监控器。

## 前置要求

1. AgentOS 已安装并初始化
2. WebUI 正在运行（或准备启动）
3. Python 虚拟环境已激活

## 5 分钟快速开始

### 1. 安装依赖

如果还未安装依赖：

```bash
# 进入项目目录
cd /Users/pangge/PycharmProjects/AgentOS

# 激活虚拟环境
source .venv/bin/activate

# 安装/更新依赖
pip install -e .
```

### 2. 启动 WebUI（如果未运行）

```bash
agentos webui start
```

### 3. 启动 Agent2 监控器

```bash
bash scripts/start_agent2.sh
```

预期输出：
```
激活虚拟环境
启动 Agent2 监控器...
日志文件: /Users/pangge/.agentos/multi_agent/agent2.log
PID 文件: /Users/pangge/.agentos/multi_agent/agent2.pid
Agent2 启动成功 (PID: 12345)
```

### 4. 验证运行状态

```bash
bash scripts/status_agent2.sh
```

预期看到：
- 进程状态: **运行中**
- 健康状态: **ok**
- 最后检查时间已更新

### 5. 观察实时日志

```bash
tail -f ~/.agentos/multi_agent/agent2.log
```

按 `Ctrl+C` 退出日志查看。

## 验证自动修复功能

### 测试场景 1: 健康监控

等待几个监控周期，观察日志：

```bash
tail -n 20 ~/.agentos/multi_agent/agent2.log
```

应该看到类似输出：
```
2026-01-27 10:30:05 - Agent2 - INFO - 开始健康检查...
2026-01-27 10:30:05 - Agent2 - INFO - 健康检查通过 (响应时间: 0.05s)
2026-01-27 10:30:10 - Agent2 - INFO - 开始健康检查...
2026-01-27 10:30:10 - Agent2 - INFO - 健康检查通过 (响应时间: 0.04s)
```

### 测试场景 2: 自动故障恢复（可选）

运行完整测试脚本：

```bash
bash scripts/test_agent2.sh
```

该脚本会：
1. 检查 Agent2 状态
2. 观察监控周期
3. 可选：模拟 WebUI 故障，观察自动恢复

## 常用命令

| 操作 | 命令 |
|-----|------|
| 启动 Agent2 | `bash scripts/start_agent2.sh` |
| 停止 Agent2 | `bash scripts/stop_agent2.sh` |
| 查看状态 | `bash scripts/status_agent2.sh` |
| 查看日志 | `tail -f ~/.agentos/multi_agent/agent2.log` |
| 运行测试 | `bash scripts/test_agent2.sh` |
| 查看状态文件 | `cat ~/.agentos/multi_agent/agent2_status.json \| jq` |

## 目录结构

启动后会创建以下文件：

```
~/.agentos/multi_agent/
├── agent2.pid              # 进程 ID
├── agent2.log              # 监控日志
├── agent2_status.json      # 状态文件
└── restart_signal          # 重启信号（临时文件）
```

## 配置文件位置

| 文件 | 位置 |
|-----|------|
| 监控脚本 | `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/agent2_monitor.py` |
| 启动脚本 | `/Users/pangge/PycharmProjects/AgentOS/scripts/start_agent2.sh` |
| 停止脚本 | `/Users/pangge/PycharmProjects/AgentOS/scripts/stop_agent2.sh` |
| 状态脚本 | `/Users/pangge/PycharmProjects/AgentOS/scripts/status_agent2.sh` |
| 测试脚本 | `/Users/pangge/PycharmProjects/AgentOS/scripts/test_agent2.sh` |
| 文档 | `/Users/pangge/PycharmProjects/AgentOS/docs/agent2_monitor.md` |

## 监控指标

Agent2 监控以下指标：

### 1. 进程健康
- 检查 `~/.agentos/webui.pid` 中的进程是否存活
- 验证进程名称包含 "python"

### 2. 网络健康
- 检查端口 8080 是否监听
- 验证可以建立 TCP 连接

### 3. API 健康
- 请求 `http://127.0.0.1:8080/api/health`
- 验证返回状态码 200
- 验证 JSON 响应中 `status` 字段为 "ok"

### 4. 响应性能
- 测量 API 响应时间
- 响应时间超过 3 秒会记录警告

## 故障处理流程

```
检测到故障
    ↓
连续失败 < 2 次？
    ↓ 是
标记为 "warn"，继续监控
    ↓ 否
开始诊断
    ↓
识别问题类型
    ↓
创建 restart_signal 文件
    ↓
等待 Agent1 处理
    ↓
重置失败计数
    ↓
继续监控
```

## 与 Agent1 协同

Agent2 和 Agent1 必须同时运行才能实现完整的自动恢复：

- **Agent2**: 检测问题 → 创建重启信号
- **Agent1**: 监控信号 → 执行重启 → 清理信号

启动顺序：
1. 启动 WebUI
2. 启动 Agent1（进程管理器）
3. 启动 Agent2（健康监控器）

## 故障排查

### 问题 1: Agent2 无法启动

**症状**: 运行 `start_agent2.sh` 后进程立即退出

**检查**:
```bash
# 查看日志
cat ~/.agentos/multi_agent/agent2.log

# 手动运行查看错误
source .venv/bin/activate
python agentos/webui/agent2_monitor.py
```

**常见原因**:
- Python 依赖缺失 → 运行 `pip install -e .`
- 目录权限问题 → 检查 `~/.agentos` 权限

### 问题 2: Agent2 持续报告故障

**症状**: 状态文件显示 `health_status: "down"`

**检查**:
```bash
# 1. 验证 WebUI 是否真的在运行
curl http://127.0.0.1:8080/api/health

# 2. 查看详细日志
tail -n 50 ~/.agentos/multi_agent/agent2.log

# 3. 检查 WebUI 进程
cat ~/.agentos/webui.pid | xargs ps -p
```

**常见原因**:
- WebUI 确实未运行 → 启动 WebUI
- 端口被占用 → 检查端口占用情况
- 网络配置问题 → 验证本地回环

### 问题 3: 自动修复不工作

**症状**: Agent2 检测到故障但 WebUI 未重启

**检查**:
```bash
# 1. 确认 Agent1 是否运行
# (需要有 Agent1 的状态检查脚本)

# 2. 检查是否创建了重启信号
ls -la ~/.agentos/multi_agent/restart_signal

# 3. 查看重启信号内容
cat ~/.agentos/multi_agent/restart_signal | jq
```

**常见原因**:
- Agent1 未运行 → 启动 Agent1
- 重启信号文件权限问题
- Agent1 配置错误

## 性能调优

### 调整监控频率

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 默认 5 秒
self.check_interval = 5

# 更频繁（适合测试）
self.check_interval = 2

# 更宽松（适合生产）
self.check_interval = 10
```

重启 Agent2 生效。

### 调整故障阈值

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 默认连续 2 次失败触发修复
if self.status["consecutive_failures"] >= 2:

# 更敏感
if self.status["consecutive_failures"] >= 1:

# 更宽容
if self.status["consecutive_failures"] >= 3:
```

### 调整超时时间

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 默认 5 秒
self.timeout = 5

# 更宽松
self.timeout = 10
```

## 生产环境部署

### 使用 systemd 管理（Linux）

创建 `/etc/systemd/system/agentos-agent2.service`:

```ini
[Unit]
Description=AgentOS Agent2 Health Monitor
After=network.target agentos-webui.service

[Service]
Type=forking
User=youruser
WorkingDirectory=/path/to/AgentOS
ExecStart=/path/to/AgentOS/scripts/start_agent2.sh
ExecStop=/path/to/AgentOS/scripts/stop_agent2.sh
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable agentos-agent2
sudo systemctl start agentos-agent2
```

### 日志轮转

创建 `/etc/logrotate.d/agentos-agent2`:

```
/home/youruser/.agentos/multi_agent/agent2.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 youruser youruser
}
```

## 下一步

- [查看完整文档](./agent2_monitor.md)
- [了解 Agent1 进程管理器](./agent1_manager.md)
- [多 Agent 协同架构](./multi_agent_architecture.md)

## 获取帮助

如遇到问题：
1. 查看日志: `tail -f ~/.agentos/multi_agent/agent2.log`
2. 查看状态: `bash scripts/status_agent2.sh`
3. 运行测试: `bash scripts/test_agent2.sh`
4. 查阅完整文档: `docs/agent2_monitor.md`
