# Agent2 - WebUI 健康监控器完整说明

## 概述

Agent2 是 AgentOS 的健康监控组件，负责持续监控 WebUI 的运行状态并在发现问题时自动触发修复。

## 核心功能

- **持续监控**: 每 5 秒检查 WebUI 健康状态
- **自动诊断**: 识别进程、端口、API 等多维度问题
- **智能修复**: 检测到故障后自动创建重启信号
- **状态追踪**: 记录所有监控和修复操作
- **协同工作**: 与 Agent1 配合实现完整的自动恢复

## 文件清单

### 核心代码

| 文件 | 说明 |
|------|------|
| `/Users/pangge/PycharmProjects/AgentOS/agentos/webui/agent2_monitor.py` | Agent2 主程序 |

### 管理脚本

| 文件 | 说明 |
|------|------|
| `/Users/pangge/PycharmProjects/AgentOS/scripts/start_agent2.sh` | 启动 Agent2 |
| `/Users/pangge/PycharmProjects/AgentOS/scripts/stop_agent2.sh` | 停止 Agent2 |
| `/Users/pangge/PycharmProjects/AgentOS/scripts/status_agent2.sh` | 查看 Agent2 状态 |
| `/Users/pangge/PycharmProjects/AgentOS/scripts/test_agent2.sh` | 测试 Agent2 功能 |
| `/Users/pangge/PycharmProjects/AgentOS/scripts/manage_multi_agent.sh` | 多 Agent 统一管理 |

### 文档

| 文件 | 说明 |
|------|------|
| `/Users/pangge/PycharmProjects/AgentOS/docs/agent2_monitor.md` | 完整技术文档 |
| `/Users/pangge/PycharmProjects/AgentOS/docs/agent2_quickstart.md` | 快速启动指南 |
| `/Users/pangge/PycharmProjects/AgentOS/docs/AGENT2_README.md` | 本文件 |

### 运行时文件

| 文件 | 说明 |
|------|------|
| `~/.agentos/multi_agent/agent2.pid` | Agent2 进程 ID |
| `~/.agentos/multi_agent/agent2.log` | 监控日志 |
| `~/.agentos/multi_agent/agent2_status.json` | 状态文件 |
| `~/.agentos/multi_agent/restart_signal` | 重启信号（临时） |

## 快速开始

### 1. 安装依赖

```bash
cd /Users/pangge/PycharmProjects/AgentOS
source .venv/bin/activate
pip install -e .
```

### 2. 启动服务

```bash
# 方式 1: 单独启动 Agent2
bash scripts/start_agent2.sh

# 方式 2: 使用统一管理脚本
bash scripts/manage_multi_agent.sh start agent2

# 方式 3: 启动所有 Agent
bash scripts/manage_multi_agent.sh start all
```

### 3. 查看状态

```bash
# 方式 1: 查看 Agent2 状态
bash scripts/status_agent2.sh

# 方式 2: 使用统一管理脚本
bash scripts/manage_multi_agent.sh status agent2

# 方式 3: 查看所有 Agent
bash scripts/manage_multi_agent.sh status all
```

### 4. 查看日志

```bash
# 实时日志
tail -f ~/.agentos/multi_agent/agent2.log

# 最近 50 行
tail -n 50 ~/.agentos/multi_agent/agent2.log

# 查看错误
grep ERROR ~/.agentos/multi_agent/agent2.log
```

### 5. 停止服务

```bash
# 方式 1: 单独停止 Agent2
bash scripts/stop_agent2.sh

# 方式 2: 使用统一管理脚本
bash scripts/manage_multi_agent.sh stop agent2
```

## 使用场景

### 场景 1: 开发环境

在开发环境中，Agent2 可以帮助你：
- 自动检测 WebUI 崩溃
- 快速发现性能问题
- 记录所有异常情况

启动顺序：
```bash
# 1. 启动 WebUI
agentos webui start

# 2. 启动 Agent2
bash scripts/start_agent2.sh

# 3. 开始开发
# Agent2 会在后台持续监控
```

### 场景 2: 测试环境

在测试环境中，Agent2 可以：
- 验证 WebUI 稳定性
- 模拟故障恢复
- 收集性能数据

运行测试：
```bash
# 启动完整测试
bash scripts/test_agent2.sh

# 查看测试结果
cat ~/.agentos/multi_agent/agent2_status.json | jq
```

### 场景 3: 生产环境（配合 Agent1）

在生产环境中，Agent2 + Agent1 提供完整的自动恢复：

```bash
# 1. 启动 WebUI
agentos webui start

# 2. 启动所有 Agent
bash scripts/manage_multi_agent.sh start all

# 3. 监控运行状态
watch -n 5 'bash scripts/manage_multi_agent.sh status all'
```

工作流程：
```
WebUI 崩溃
    ↓
Agent2 检测到异常
    ↓
Agent2 创建重启信号
    ↓
Agent1 检测到信号
    ↓
Agent1 重启 WebUI
    ↓
Agent1 清理信号
    ↓
Agent2 确认恢复，重置计数
    ↓
继续正常监控
```

## 监控指标详解

### 1. 进程健康 (Process Health)

检查内容：
- PID 文件是否存在
- 进程是否存活
- 进程类型是否正确

失败条件：
- PID 文件不存在
- 进程已退出
- 进程不是 Python 进程

### 2. 网络健康 (Network Health)

检查内容：
- 端口 8080 是否监听
- TCP 连接状态

失败条件：
- 端口未监听
- 无法建立连接

### 3. API 健康 (API Health)

检查内容：
- GET `/api/health` 请求
- HTTP 状态码
- 响应 JSON 格式
- status 字段值

失败条件：
- 连接超时（5 秒）
- 状态码非 200
- 响应格式错误
- status 不为 "ok"

### 4. 性能指标 (Performance)

监控内容：
- API 响应时间
- CPU 使用率（通过健康 API）
- 内存使用量（通过健康 API）

警告条件：
- 响应时间 > 3 秒
- CPU > 80%（计划中）
- 内存 > 512MB（计划中）

## 配置调优

### 调整监控频率

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 第 27 行
self.check_interval = 5  # 改为你想要的秒数
```

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| 开发 | 2-3 秒 | 快速反馈 |
| 测试 | 5 秒 | 平衡性能和响应 |
| 生产 | 10-15 秒 | 减少资源占用 |

### 调整故障阈值

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 第 198 行
if self.status["consecutive_failures"] >= 2:
```

| 场景 | 推荐值 | 说明 |
|------|--------|------|
| 敏感 | 1 | 立即响应故障 |
| 标准 | 2 | 避免误报 |
| 宽松 | 3 | 容忍短暂抖动 |

### 调整超时时间

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 第 28 行
self.timeout = 5  # 请求超时秒数
```

| 网络环境 | 推荐值 |
|----------|--------|
| 本地 | 5 秒 |
| 局域网 | 10 秒 |
| 远程 | 15 秒 |

### 修改日志级别

编辑 `agentos/webui/agent2_monitor.py`:

```python
# 第 19 行
logging.basicConfig(
    level=logging.INFO,  # 改为 DEBUG, WARNING, ERROR
    # ...
)
```

## 状态文件说明

### agent2_status.json 格式

```json
{
  "status": "monitoring",           // 当前状态
  "last_check": "2026-01-27T...",  // 最后检查时间
  "health_status": "ok",           // 健康状态
  "consecutive_failures": 0,        // 连续失败次数
  "fixes": [                       // 修复历史
    {
      "timestamp": "2026-01-27T...",
      "issue": "问题描述",
      "action": "修复动作",
      "result": "结果"
    }
  ]
}
```

#### status 字段值

| 值 | 含义 |
|----|------|
| `initializing` | 正在初始化 |
| `monitoring` | 正常监控中 |
| `fixing` | 正在修复问题 |
| `error` | 发生错误 |
| `stopped` | 已停止 |

#### health_status 字段值

| 值 | 含义 |
|----|------|
| `ok` | 健康 |
| `warn` | 警告（单次失败） |
| `down` | 故障（连续失败） |
| `unknown` | 未知（初始化或错误） |

#### fix result 字段值

| 值 | 含义 |
|----|------|
| `signal_created` | 已创建重启信号 |
| `warning_logged` | 已记录警告 |
| `success` | 修复成功 |
| `failed` | 修复失败 |

### restart_signal 格式

```json
{
  "timestamp": "2026-01-27T10:30:45+00:00",
  "reason": "health_check_failed",
  "requested_by": "agent2"
}
```

#### reason 字段值

| 值 | 含义 |
|----|------|
| `process_not_alive` | 进程不存在 |
| `port_not_listening` | 端口未监听 |
| `health_check_failed` | 健康检查失败 |

## 常见问题

### Q1: Agent2 启动后立即退出？

**检查步骤：**
```bash
# 1. 查看日志
cat ~/.agentos/multi_agent/agent2.log

# 2. 手动运行
cd /Users/pangge/PycharmProjects/AgentOS
source .venv/bin/activate
python agentos/webui/agent2_monitor.py

# 3. 检查依赖
pip list | grep -E "requests|psutil"
```

**常见原因：**
- Python 依赖缺失 → `pip install -e .`
- 权限问题 → `chmod 755 ~/.agentos`
- Python 版本不兼容 → 需要 Python 3.13+

### Q2: Agent2 一直报告 "down" 状态？

**检查步骤：**
```bash
# 1. 手动测试健康检查
curl http://127.0.0.1:8080/api/health

# 2. 检查 WebUI 是否真的在运行
ps aux | grep uvicorn

# 3. 检查端口
lsof -i :8080

# 4. 查看 WebUI 日志
agentos webui logs
```

**常见原因：**
- WebUI 确实未运行 → `agentos webui start`
- 端口被其他程序占用 → 查找并关闭
- 防火墙阻止本地访问 → 检查防火墙规则

### Q3: 修复信号创建了但 WebUI 没重启？

**检查步骤：**
```bash
# 1. 检查重启信号
cat ~/.agentos/multi_agent/restart_signal

# 2. 检查 Agent1 是否运行
ps aux | grep agent1

# 3. 查看 Agent1 日志
cat ~/.agentos/multi_agent/agent1.log
```

**常见原因：**
- Agent1 未运行 → 启动 Agent1
- Agent1 配置错误
- 权限不足无法重启

### Q4: 日志文件过大？

**解决方案：**
```bash
# 临时清理（需要先停止 Agent2）
bash scripts/stop_agent2.sh
> ~/.agentos/multi_agent/agent2.log
bash scripts/start_agent2.sh

# 配置日志轮转（Linux）
# 创建 /etc/logrotate.d/agentos-agent2
cat << EOF | sudo tee /etc/logrotate.d/agentos-agent2
/home/$USER/.agentos/multi_agent/agent2.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```

### Q5: 如何禁用自动修复只保留监控？

**修改代码：**

编辑 `agentos/webui/agent2_monitor.py`，注释掉修复逻辑：

```python
# 第 195-206 行
# 如果连续失败次数超过阈值，尝试修复
# if self.status["consecutive_failures"] >= 2:
#     logger.error("开始尝试修复...")
#     self._update_status("fixing", health_status)
#
#     fix_record = self._fix_issue(diagnosis)
#     logger.info(f"修复操作: {fix_record['action']}, 结果: {fix_record['result']}")
#
#     self._update_status("monitoring", health_status, fix_record)

# 改为只记录
if self.status["consecutive_failures"] >= 2:
    logger.error(f"检测到持续故障，但未启用自动修复")
```

## 性能影响

### 资源占用

| 指标 | 典型值 | 峰值 |
|------|--------|------|
| CPU | < 0.1% | < 0.5% |
| 内存 | ~30 MB | ~50 MB |
| 网络 | ~1 KB/5s | ~5 KB/5s |
| 磁盘 IO | 最小 | 写日志时 |

### 对 WebUI 的影响

- 每 5 秒一次 HTTP 请求
- 响应时间 < 50ms（本地）
- 不影响正常业务请求

## 扩展开发

### 添加自定义检查

在 `_diagnose` 方法中添加：

```python
def _diagnose(self):
    diagnosis = {
        # ... 现有检查 ...
        "custom_check": self._check_custom(),
    }
    return diagnosis

def _check_custom(self):
    """自定义检查"""
    # 实现你的检查逻辑
    return True
```

### 添加告警通知

在 `_fix_issue` 方法中添加：

```python
def _fix_issue(self, diagnosis):
    fix_record = {
        # ... 现有代码 ...
    }

    # 发送告警
    self._send_alert(fix_record)

    return fix_record

def _send_alert(self, fix_record):
    """发送告警通知"""
    # 实现邮件/Slack/钉钉等通知
    pass
```

### 集成监控平台

导出 Prometheus 指标：

```python
from prometheus_client import Counter, Gauge, start_http_server

# 定义指标
health_check_total = Counter('agent2_health_check_total', 'Total health checks')
health_check_failures = Counter('agent2_health_check_failures', 'Failed health checks')
response_time = Gauge('agent2_response_time_seconds', 'Health check response time')

# 在 __init__ 中启动 metrics server
start_http_server(9090)

# 在监控逻辑中更新指标
health_check_total.inc()
if not healthy:
    health_check_failures.inc()
response_time.set(response_time_value)
```

## 相关资源

- [完整技术文档](./agent2_monitor.md)
- [快速启动指南](./agent2_quickstart.md)
- [Agent1 文档](./agent1_manager.md)（待创建）
- [多 Agent 架构](./multi_agent_architecture.md)（待创建）

## 版本信息

- **当前版本**: 1.0
- **创建日期**: 2026-01-27
- **Python 要求**: >= 3.13
- **依赖项**: requests, psutil, fastapi, uvicorn

## 维护计划

### 即将实现的功能

- [ ] Prometheus 指标导出
- [ ] 邮件/Slack 告警
- [ ] 更多自定义检查项
- [ ] 性能趋势分析
- [ ] Web UI 监控面板

### 已知限制

- 仅支持单实例 WebUI
- 依赖本地文件系统通信
- 无法监控远程 WebUI

## 贡献

如需改进 Agent2，请：
1. 修改 `agentos/webui/agent2_monitor.py`
2. 更新相关文档
3. 运行测试验证：`bash scripts/test_agent2.sh`
4. 提交更改

## 许可证

MIT License - 与 AgentOS 主项目相同

---

**最后更新**: 2026-01-27
**维护者**: AgentOS Team
