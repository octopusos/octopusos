# Agent2 最佳实践指南

## 部署最佳实践

### 开发环境

#### 推荐配置

```bash
# 监控间隔: 2-3 秒（快速反馈）
# 失败阈值: 2 次（标准）
# 超时时间: 5 秒

# 启动顺序
agentos webui start        # 1. 启动 WebUI
bash scripts/start_agent2.sh   # 2. 启动监控

# 查看实时日志
tail -f ~/.agentos/multi_agent/agent2.log
```

#### 调试技巧

```bash
# 1. 手动运行 Agent2（查看详细输出）
cd /Users/pangge/PycharmProjects/AgentOS
source .venv/bin/activate
python agentos/webui/agent2_monitor.py

# 2. 启用 DEBUG 日志
# 编辑 agent2_monitor.py，将 logging.INFO 改为 logging.DEBUG

# 3. 手动测试健康检查
curl -v http://127.0.0.1:8080/api/health

# 4. 查看进程信息
cat ~/.agentos/webui.pid | xargs ps -fp

# 5. 检查端口监听
lsof -i :8080
```

### 测试环境

#### 推荐配置

```bash
# 监控间隔: 5 秒（标准）
# 失败阈值: 2 次
# 超时时间: 5 秒

# 使用统一管理脚本
bash scripts/manage_multi_agent.sh start all

# 定期检查状态
watch -n 10 'bash scripts/status_agent2.sh'
```

#### 故障模拟测试

```bash
# 测试 1: 模拟进程崩溃
# 找到 WebUI PID
WEBUI_PID=$(cat ~/.agentos/webui.pid)

# 杀死进程
kill $WEBUI_PID

# 观察 Agent2 响应（应在 10-15 秒内创建重启信号）
watch -n 1 'ls -l ~/.agentos/multi_agent/restart_signal'

# 测试 2: 模拟进程挂起
# 暂停进程
kill -STOP $WEBUI_PID

# 等待 Agent2 检测（15-20 秒）
tail -f ~/.agentos/multi_agent/agent2.log

# 恢复进程
kill -CONT $WEBUI_PID

# 测试 3: 运行完整测试套件
bash scripts/test_agent2.sh
```

### 生产环境

#### 推荐配置

```bash
# 监控间隔: 10-15 秒（降低资源占用）
# 失败阈值: 3 次（避免误报）
# 超时时间: 10 秒（适应网络波动）

# 使用 systemd 管理（Linux）
sudo systemctl enable agentos-agent2
sudo systemctl start agentos-agent2

# 或使用 launchd（macOS）
# 见下文 macOS 配置
```

#### systemd 配置（Linux）

创建 `/etc/systemd/system/agentos-agent2.service`:

```ini
[Unit]
Description=AgentOS Agent2 Health Monitor
Documentation=file:///Users/pangge/PycharmProjects/AgentOS/docs/agent2_monitor.md
After=network.target agentos-webui.service
Wants=agentos-webui.service

[Service]
Type=forking
User=youruser
Group=yourgroup
WorkingDirectory=/path/to/AgentOS
Environment="PATH=/path/to/AgentOS/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/AgentOS/scripts/start_agent2.sh
ExecStop=/path/to/AgentOS/scripts/stop_agent2.sh
ExecReload=/bin/kill -HUP $MAINPID
PIDFile=/home/youruser/.agentos/multi_agent/agent2.pid

# 重启策略
Restart=on-failure
RestartSec=10s
StartLimitInterval=5min
StartLimitBurst=3

# 资源限制
MemoryLimit=100M
CPUQuota=10%

# 安全加固
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

操作命令：
```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable agentos-agent2

# 启动/停止/重启
sudo systemctl start agentos-agent2
sudo systemctl stop agentos-agent2
sudo systemctl restart agentos-agent2

# 查看状态
sudo systemctl status agentos-agent2

# 查看日志
sudo journalctl -u agentos-agent2 -f
```

#### launchd 配置（macOS）

创建 `~/Library/LaunchAgents/com.agentos.agent2.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.agentos.agent2</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/pangge/PycharmProjects/AgentOS/.venv/bin/python</string>
        <string>/Users/pangge/PycharmProjects/AgentOS/agentos/webui/agent2_monitor.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/pangge/PycharmProjects/AgentOS</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/pangge/.agentos/multi_agent/agent2.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/pangge/.agentos/multi_agent/agent2_error.log</string>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

操作命令：
```bash
# 加载服务
launchctl load ~/Library/LaunchAgents/com.agentos.agent2.plist

# 卸载服务
launchctl unload ~/Library/LaunchAgents/com.agentos.agent2.plist

# 启动/停止
launchctl start com.agentos.agent2
launchctl stop com.agentos.agent2

# 查看状态
launchctl list | grep agent2
```

## 监控和告警

### 日志监控

#### 使用 logrotate（Linux）

创建 `/etc/logrotate.d/agentos-agent2`:

```
/home/youruser/.agentos/multi_agent/agent2.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 youruser yourgroup
    postrotate
        # 通知 Agent2 重新打开日志文件
        kill -HUP $(cat /home/youruser/.agentos/multi_agent/agent2.pid) 2>/dev/null || true
    endscript
}
```

测试配置：
```bash
sudo logrotate -d /etc/logrotate.d/agentos-agent2
```

#### 使用 newsyslog（macOS）

添加到 `/etc/newsyslog.conf`:

```
/Users/pangge/.agentos/multi_agent/agent2.log pangge:staff 644 7 * @T00 JC
```

### 告警集成

#### 邮件告警

在 `agent2_monitor.py` 中添加：

```python
import smtplib
from email.mime.text import MIMEText

def _send_email_alert(self, issue, action):
    """发送邮件告警"""
    msg = MIMEText(f"""
    Agent2 检测到问题:

    问题: {issue}
    修复动作: {action}
    时间: {datetime.now().isoformat()}

    查看详情: cat ~/.agentos/multi_agent/agent2_status.json
    """)

    msg['Subject'] = f'[Agent2 Alert] {issue}'
    msg['From'] = 'agent2@agentos.local'
    msg['To'] = 'admin@example.com'

    try:
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg)
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")

# 在 _fix_issue 中调用
def _fix_issue(self, diagnosis):
    # ... 现有代码 ...
    self._send_email_alert(fix_record['issue'], fix_record['action'])
    return fix_record
```

#### Slack 告警

```python
import requests

def _send_slack_alert(self, issue, action):
    """发送 Slack 告警"""
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    payload = {
        "text": "Agent2 Alert",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "Issue", "value": issue, "short": False},
                {"title": "Action", "value": action, "short": False},
                {"title": "Time", "value": datetime.now().isoformat(), "short": True}
            ]
        }]
    }

    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"发送 Slack 消息失败: {e}")
```

#### PagerDuty 告警

```python
import requests

def _send_pagerduty_alert(self, issue, action):
    """发送 PagerDuty 告警"""
    api_key = "YOUR_PAGERDUTY_API_KEY"
    service_key = "YOUR_SERVICE_KEY"

    payload = {
        "routing_key": service_key,
        "event_action": "trigger",
        "payload": {
            "summary": f"Agent2: {issue}",
            "severity": "error",
            "source": "agent2",
            "custom_details": {
                "issue": issue,
                "action": action,
                "timestamp": datetime.now().isoformat()
            }
        }
    }

    try:
        requests.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
    except Exception as e:
        logger.error(f"发送 PagerDuty 告警失败: {e}")
```

## 性能调优

### 场景 1: 高负载环境

```python
# 降低检查频率
self.check_interval = 15  # 从 5 秒改为 15 秒

# 增加超时时间
self.timeout = 10  # 从 5 秒改为 10 秒

# 提高失败阈值
if self.status["consecutive_failures"] >= 3:  # 从 2 改为 3
```

### 场景 2: 低延迟要求

```python
# 提高检查频率
self.check_interval = 2  # 从 5 秒改为 2 秒

# 降低失败阈值
if self.status["consecutive_failures"] >= 1:  # 从 2 改为 1

# 减少超时时间
self.timeout = 3  # 从 5 秒改为 3 秒
```

### 场景 3: 网络不稳定

```python
# 增加超时时间
self.timeout = 15  # 从 5 秒改为 15 秒

# 提高失败阈值
if self.status["consecutive_failures"] >= 5:  # 从 2 改为 5

# 添加重试逻辑
def _check_health_api_with_retry(self):
    for attempt in range(self.max_retry):
        success, data, time = self._check_health_api()
        if success:
            return True, data, time
        sleep(1)
    return False, None, None
```

## 故障排查流程

### 第 1 步: 确认 Agent2 状态

```bash
# 检查进程
bash scripts/status_agent2.sh

# 如果未运行，启动它
bash scripts/start_agent2.sh
```

### 第 2 步: 检查日志

```bash
# 查看最近的错误
tail -n 100 ~/.agentos/multi_agent/agent2.log | grep ERROR

# 查看最近的警告
tail -n 100 ~/.agentos/multi_agent/agent2.log | grep WARNING

# 查看最近的修复操作
grep "修复操作" ~/.agentos/multi_agent/agent2.log
```

### 第 3 步: 检查状态文件

```bash
# 查看当前状态
cat ~/.agentos/multi_agent/agent2_status.json | jq '.'

# 查看失败次数
cat ~/.agentos/multi_agent/agent2_status.json | jq '.consecutive_failures'

# 查看修复历史
cat ~/.agentos/multi_agent/agent2_status.json | jq '.fixes[-5:]'
```

### 第 4 步: 手动验证 WebUI

```bash
# 检查进程
cat ~/.agentos/webui.pid | xargs ps -fp

# 检查端口
lsof -i :8080

# 测试健康检查
curl -v http://127.0.0.1:8080/api/health
```

### 第 5 步: 重启服务

```bash
# 重启 Agent2
bash scripts/manage_multi_agent.sh restart agent2

# 或重启所有服务
bash scripts/manage_multi_agent.sh restart all
```

## 安全最佳实践

### 1. 文件权限

```bash
# 确保配置文件权限正确
chmod 755 ~/.agentos
chmod 755 ~/.agentos/multi_agent
chmod 644 ~/.agentos/multi_agent/agent2_status.json
chmod 644 ~/.agentos/multi_agent/agent2.log
chmod 644 ~/.agentos/multi_agent/agent2.pid
```

### 2. 日志安全

```python
# 避免记录敏感信息
# 不要记录:
# - API 密钥
# - 密码
# - 令牌
# - 个人信息

# 正确的做法
logger.info("健康检查失败")  # ✓
# 错误的做法
# logger.info(f"使用密钥 {api_key} 的健康检查失败")  # ✗
```

### 3. 网络安全

```python
# 仅监听本地地址
self.webui_url = "http://127.0.0.1:8080"  # ✓
# 不要使用
# self.webui_url = "http://0.0.0.0:8080"  # ✗
```

## 维护清单

### 日常维护（每天）

```bash
# 1. 检查 Agent2 状态
bash scripts/status_agent2.sh

# 2. 查看是否有错误
grep ERROR ~/.agentos/multi_agent/agent2.log | tail -n 10

# 3. 检查修复次数
cat ~/.agentos/multi_agent/agent2_status.json | jq '.fixes | length'
```

### 周度维护（每周）

```bash
# 1. 查看日志大小
du -h ~/.agentos/multi_agent/agent2.log

# 2. 分析失败模式
grep "修复操作" ~/.agentos/multi_agent/agent2.log | \
    awk -F'修复操作: ' '{print $2}' | \
    cut -d',' -f1 | \
    sort | uniq -c | sort -rn

# 3. 检查性能指标
# 提取响应时间
grep "响应时间" ~/.agentos/multi_agent/agent2.log | \
    awk -F'响应时间: ' '{print $2}' | \
    awk '{print $1}' | \
    awk '{sum+=$1; count++} END {print "平均:", sum/count "s"}'
```

### 月度维护（每月）

```bash
# 1. 清理旧日志
# 如果没有配置 logrotate
> ~/.agentos/multi_agent/agent2.log

# 2. 重置状态文件
# 备份后清理修复历史
cp ~/.agentos/multi_agent/agent2_status.json \
   ~/.agentos/multi_agent/agent2_status.json.backup
cat ~/.agentos/multi_agent/agent2_status.json | \
    jq '.fixes = []' > /tmp/agent2_status.json.tmp
mv /tmp/agent2_status.json.tmp ~/.agentos/multi_agent/agent2_status.json

# 3. 检查系统资源
ps aux | grep agent2_monitor.py
```

## 集成测试示例

### 编写自动化测试

```python
#!/usr/bin/env python3
"""Agent2 集成测试"""

import json
import time
import requests
import subprocess
from pathlib import Path

def test_agent2_monitoring():
    """测试 Agent2 监控功能"""
    status_file = Path.home() / '.agentos' / 'multi_agent' / 'agent2_status.json'

    # 等待几个监控周期
    time.sleep(15)

    # 读取状态
    with open(status_file) as f:
        status = json.load(f)

    # 验证
    assert status['status'] == 'monitoring'
    assert status['last_check'] is not None
    print("✓ 监控功能正常")

def test_agent2_health_check():
    """测试健康检查"""
    # 直接测试 WebUI
    response = requests.get('http://127.0.0.1:8080/api/health', timeout=5)
    assert response.status_code == 200

    data = response.json()
    assert data['status'] == 'ok'
    print("✓ 健康检查正常")

def test_agent2_failure_detection():
    """测试故障检测"""
    # 1. 停止 WebUI
    subprocess.run(['agentos', 'webui', 'stop'])

    # 2. 等待 Agent2 检测
    time.sleep(15)

    # 3. 检查重启信号
    signal_file = Path.home() / '.agentos' / 'multi_agent' / 'restart_signal'
    assert signal_file.exists(), "应该创建重启信号"

    # 4. 重启 WebUI
    subprocess.run(['agentos', 'webui', 'start'])

    print("✓ 故障检测正常")

if __name__ == '__main__':
    test_agent2_health_check()
    test_agent2_monitoring()
    # test_agent2_failure_detection()  # 需要谨慎运行
    print("\n所有测试通过!")
```

运行测试：
```bash
python test_agent2_integration.py
```

## 总结

遵循这些最佳实践可以确保 Agent2：
- ✓ 稳定可靠地运行
- ✓ 及时检测和修复问题
- ✓ 最小化资源占用
- ✓ 易于维护和调试

关键要点：
1. **根据环境调整配置**（开发 vs 生产）
2. **配置日志轮转**防止磁盘占满
3. **设置告警通知**及时发现问题
4. **定期维护检查**保持系统健康
5. **编写自动化测试**验证功能正常
