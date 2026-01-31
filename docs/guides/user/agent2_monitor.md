# Agent2 - WebUI 健康监控器

Agent2 是一个自动化监控和修复工具，负责持续监控 AgentOS WebUI 的健康状态并在发现问题时自动修复。

## 功能特性

### 1. 持续健康监控

- **监控频率**: 每 5 秒检查一次
- **监控项**:
  - 健康检查 API (`/api/health`)
  - 进程存活状态
  - 端口监听状态 (8080)
  - API 响应时间

### 2. 自动故障诊断

Agent2 会自动诊断以下问题:

- 健康检查 API 失败
- WebUI 进程不存在
- 端口未监听
- 响应时间异常（超过 3 秒）

### 3. 自动修复机制

当检测到问题时，Agent2 会:

1. 记录问题详情
2. 创建重启信号通知 Agent1
3. 等待 Agent1 处理重启
4. 重置失败计数器
5. 继续监控

### 4. 状态追踪

所有监控和修复操作都会记录到:

- **状态文件**: `~/.agentos/multi_agent/agent2_status.json`
- **日志文件**: `~/.agentos/multi_agent/agent2.log`

## 快速开始

### 启动 Agent2

```bash
bash scripts/start_agent2.sh
```

输出示例:
```
激活虚拟环境
启动 Agent2 监控器...
日志文件: /Users/xxx/.agentos/multi_agent/agent2.log
PID 文件: /Users/xxx/.agentos/multi_agent/agent2.pid
Agent2 启动成功 (PID: 12345)

查看日志: tail -f /Users/xxx/.agentos/multi_agent/agent2.log
停止服务: scripts/stop_agent2.sh
查看状态: cat /Users/xxx/.agentos/multi_agent/agent2_status.json
```

### 查看状态

```bash
bash scripts/status_agent2.sh
```

输出示例:
```
=== Agent2 监控器状态 ===

进程状态:
  状态: 运行中
  PID: 12345
  CPU: 0.1%
  内存: 0.5% (RSS: 50000 KB)
  运行时长: 00:05:30

监控状态:
  运行状态: monitoring
  健康状态: ok
  最后检查: 2026-01-27T10:30:45.123456+00:00
  连续失败: 0
  修复次数: 2

最近修复记录 (最多显示 5 条):
  - [2026-01-27T10:25:12+00:00] WebUI 进程不存在 -> 创建重启信号 (signal_created)
  - [2026-01-27T10:28:30+00:00] 健康检查 API 失败 -> 创建重启信号 (signal_created)
```

### 停止 Agent2

```bash
bash scripts/stop_agent2.sh
```

### 测试功能

```bash
bash scripts/test_agent2.sh
```

此脚本会:
1. 检查 Agent2 运行状态
2. 验证状态文件
3. 观察监控周期
4. 可选：模拟故障恢复测试
5. 检查日志输出

## 文件结构

```
~/.agentos/multi_agent/
├── agent2.pid              # Agent2 进程 ID
├── agent2.log              # 监控日志
├── agent2_status.json      # 状态文件
└── restart_signal          # 重启信号文件 (临时)
```

## 状态文件格式

`agent2_status.json` 包含以下信息:

```json
{
  "status": "monitoring",          // 运行状态: monitoring|fixing|error|stopped
  "last_check": "2026-01-27T10:30:45.123456+00:00",
  "health_status": "ok",           // 健康状态: ok|warn|down|unknown
  "consecutive_failures": 0,       // 连续失败次数
  "fixes": [
    {
      "timestamp": "2026-01-27T10:25:12+00:00",
      "issue": "WebUI 进程不存在",
      "action": "创建重启信号",
      "result": "signal_created"   // success|failed|signal_created|warning_logged
    }
  ]
}
```

## 重启信号格式

当 Agent2 检测到需要重启 WebUI 时，会创建 `restart_signal` 文件:

```json
{
  "timestamp": "2026-01-27T10:25:12+00:00",
  "reason": "process_not_alive",
  "requested_by": "agent2"
}
```

Agent1 会监控此文件并执行重启操作。

## 监控逻辑

### 健康判断

Agent2 认为 WebUI 健康需要满足:
- ✓ 进程存在
- ✓ 端口 8080 正在监听
- ✓ 健康检查 API 返回 200
- ✓ API 返回的 status 字段为 "ok"

### 故障处理

1. **连续失败判断**:
   - 单次失败 → 标记为 "warn"，继续监控
   - 连续 2 次失败 → 触发修复流程

2. **修复策略**:
   - 进程不存在 → 创建重启信号
   - 端口未监听 → 创建重启信号
   - 健康检查失败 → 创建重启信号
   - 响应时间过长 → 记录警告（不重启）

3. **修复后处理**:
   - 等待 10 秒让 Agent1 处理
   - 重置失败计数器
   - 继续正常监控

## 日志示例

```
2026-01-27 10:30:00 - Agent2 - INFO - Agent2 监控器启动
2026-01-27 10:30:00 - Agent2 - INFO - 监控目标: http://127.0.0.1:8080
2026-01-27 10:30:00 - Agent2 - INFO - 检查间隔: 5秒
2026-01-27 10:30:05 - Agent2 - INFO - 开始健康检查...
2026-01-27 10:30:05 - Agent2 - INFO - 健康检查通过 (响应时间: 0.05s)
2026-01-27 10:30:10 - Agent2 - INFO - 开始健康检查...
2026-01-27 10:30:10 - Agent2 - ERROR - 无法连接到 WebUI
2026-01-27 10:30:10 - Agent2 - WARNING - 检测到异常 (连续失败: 1)
2026-01-27 10:30:15 - Agent2 - INFO - 开始健康检查...
2026-01-27 10:30:15 - Agent2 - ERROR - 无法连接到 WebUI
2026-01-27 10:30:15 - Agent2 - WARNING - 检测到异常 (连续失败: 2)
2026-01-27 10:30:15 - Agent2 - ERROR - 开始尝试修复...
2026-01-27 10:30:15 - Agent2 - INFO - 已创建重启信号: health_check_failed
2026-01-27 10:30:15 - Agent2 - INFO - 修复操作: 创建重启信号, 结果: signal_created
2026-01-27 10:30:15 - Agent2 - INFO - 等待 Agent1 处理重启信号...
```

## 与 Agent1 协同工作

Agent2 和 Agent1 通过文件系统通信:

1. **Agent2 职责**:
   - 监控 WebUI 健康状态
   - 诊断问题
   - 创建重启信号

2. **Agent1 职责**:
   - 监控重启信号
   - 执行 WebUI 重启
   - 清理重启信号文件

3. **通信流程**:
```
Agent2 检测到故障
    ↓
创建 restart_signal 文件
    ↓
等待 10 秒
    ↓
Agent1 检测到信号
    ↓
Agent1 执行重启
    ↓
Agent1 删除信号文件
    ↓
Agent2 重置计数器，继续监控
```

## 常见问题

### Q: Agent2 启动失败?

检查:
1. Python 环境是否正确
2. 依赖是否安装 (`requests`, `psutil`)
3. 查看日志: `~/.agentos/multi_agent/agent2.log`

### Q: Agent2 一直报告故障但不修复?

可能原因:
- 连续失败次数未达到阈值 (需要 2 次)
- Agent1 未运行，无法处理重启信号

### Q: 如何调整监控频率?

编辑 `agentos/webui/agent2_monitor.py`:
```python
self.check_interval = 5  # 改为其他值，单位：秒
```

### Q: 如何调整失败阈值?

编辑修复逻辑中的判断:
```python
if self.status["consecutive_failures"] >= 2:  # 改为其他值
```

### Q: 如何查看实时日志?

```bash
tail -f ~/.agentos/multi_agent/agent2.log
```

### Q: 如何清理历史记录?

```bash
# 停止 Agent2
bash scripts/stop_agent2.sh

# 删除状态和日志文件
rm ~/.agentos/multi_agent/agent2_status.json
rm ~/.agentos/multi_agent/agent2.log

# 重新启动
bash scripts/start_agent2.sh
```

## 性能影响

Agent2 的资源占用非常低:

- **CPU**: < 0.1% (空闲时)
- **内存**: < 50 MB
- **网络**: 每 5 秒一次 HTTP 请求到本地
- **磁盘**: 日志文件会逐渐增长，建议定期清理

## 最佳实践

1. **始终同时运行 Agent1 和 Agent2**
   - Agent2 负责检测
   - Agent1 负责修复

2. **定期检查日志**
   ```bash
   bash scripts/status_agent2.sh
   ```

3. **生产环境建议**
   - 使用 systemd 或 supervisor 管理 Agent2
   - 配置日志轮转
   - 设置告警通知

4. **开发环境建议**
   - 启动 WebUI 后立即启动 Agent2
   - 使用测试脚本验证功能

## 进阶配置

### 自定义健康检查

修改 `_check_health_api` 方法添加更多检查项:

```python
def _check_health_api(self):
    # ... 现有代码 ...

    # 添加自定义检查
    if data.get('components', {}).get('database') != 'ok':
        logger.warning("数据库组件异常")
        return False, data, response_time

    return True, data, response_time
```

### 添加告警通知

在 `_fix_issue` 方法中添加通知逻辑:

```python
def _fix_issue(self, diagnosis):
    # ... 现有修复代码 ...

    # 发送告警
    self._send_alert(fix_record)

    return fix_record

def _send_alert(self, fix_record):
    # 实现邮件/Slack/钉钉等通知
    pass
```

## 相关文档

- [Agent1 进程管理器文档](./agent1_manager.md)
- [多 Agent 协同架构](./multi_agent_architecture.md)
- [WebUI 健康检查 API](../agentos/webui/api/health.py)

## 版本历史

- v1.0 (2026-01-27): 初始版本
  - 基础健康监控
  - 自动故障修复
  - 与 Agent1 协同工作
