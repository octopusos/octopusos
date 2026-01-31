# Task #15 演示指南

## 🎯 目标
演示 Mode Monitor 在 AgentOS WebUI 中的集成效果。

---

## 🚀 启动步骤

### 1. 启动 WebUI 服务
```bash
cd /Users/pangge/PycharmProjects/AgentOS
python -m agentos.webui.app
```

**预期输出**:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:5000
```

---

## 🖥️ 浏览器操作

### 2. 打开浏览器
访问: `http://localhost:5000`

### 3. 找到 Mode Monitor
1. 查看左侧导航栏
2. 找到 **Observability** 部分
3. 点击 **Mode Monitor** 导航项（盾牌图标）

---

## 📸 预期界面

### 统计卡片
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Total Alerts   │ │  Recent Errors  │ │    Warnings     │
│        0        │ │        0        │ │        0        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 告警列表
```
Recent Alerts
┌────────────────────────────────────────────────────┐
│ No alerts                                          │
└────────────────────────────────────────────────────┘

[Refresh]
```

---

## 🧪 功能演示

### 测试 1: 刷新功能
1. 点击 **Refresh** 按钮
2. 观察数据刷新

### 测试 2: 自动刷新
1. 等待 10 秒
2. 观察数据自动更新

### 测试 3: API 测试
在新终端中运行:
```bash
# 获取统计
curl http://localhost:5000/api/mode/stats

# 获取告警
curl http://localhost:5000/api/mode/alerts

# 测试过滤
curl "http://localhost:5000/api/mode/alerts?severity=error&limit=10"
```

---

## 🔍 开发者工具检查

### 打开浏览器开发者工具 (F12)

#### 1. Console 标签
检查是否有错误:
```javascript
// 应该看到成功消息
✓ Mode Monitor View rendered successfully
```

#### 2. Network 标签
检查 API 请求:
- `GET /api/mode/alerts` - 状态: 200 OK
- `GET /api/mode/stats` - 状态: 200 OK
- `GET /static/css/mode-monitor.css` - 状态: 200 OK
- `GET /static/js/views/ModeMonitorView.js` - 状态: 200 OK

#### 3. Elements 标签
检查 DOM 结构:
```html
<div class="mode-monitor">
  <h2>🛡️ Mode System Monitor</h2>
  <div class="stats-grid">...</div>
  <div class="alerts-section">...</div>
</div>
```

---

## 📊 生成测试告警

### 方法 1: 使用 Python API
```python
from agentos.core.mode.mode_alerts import get_alert_aggregator

aggregator = get_alert_aggregator()
aggregator.alert_mode_violation(
    mode_id="design",
    operation="apply_diff",
    message="Test violation",
    severity="error"
)
```

### 方法 2: 触发实际违规
运行 mode policy 测试:
```bash
python3 -m pytest tests/unit/mode/test_mode_policy.py -v
```

### 刷新浏览器查看告警
点击 **Refresh** 按钮，应该看到告警出现在列表中。

---

## 🎨 样式验证

### 检查 CSS 样式
1. 统计卡片应该有悬停效果
2. 告警项应该有左侧彩色边框
3. 严重程度徽章应该有不同颜色:
   - **Error**: 红色 (#e74c3c)
   - **Warning**: 橙色 (#f39c12)
   - **Info**: 蓝色 (#3498db)
   - **Critical**: 深红色 (#c0392b)

---

## ✅ 验收检查清单

### 界面显示
- [ ] Mode Monitor 导航项可见
- [ ] 点击导航项后页面正确加载
- [ ] 三个统计卡片显示正确
- [ ] 告警列表显示正确
- [ ] Refresh 按钮可点击

### 功能测试
- [ ] 手动刷新功能正常
- [ ] 自动刷新功能正常（10秒）
- [ ] API 端点返回正确数据
- [ ] 过滤功能正常（severity, limit）
- [ ] 清空功能正常

### 用户体验
- [ ] 页面加载速度快
- [ ] 无控制台错误
- [ ] 无网络错误
- [ ] 样式显示正确
- [ ] 响应式设计（手机/平板）

### 错误处理
- [ ] 模块加载失败时显示错误提示
- [ ] API 失败时显示错误消息
- [ ] 错误消息对用户友好

---

## 🐛 故障排除

### 问题 1: 导航项不显示
**解决**: 清除浏览器缓存，强制刷新 (Ctrl+Shift+R)

### 问题 2: 点击后页面空白
**检查**:
1. 开发者工具 Console 是否有错误
2. Network 标签是否显示 404 错误
3. 确认 ModeMonitorView.js 文件存在

### 问题 3: API 返回 404
**检查**:
1. 确认 app.py 已重启
2. 确认路由已正确注册
3. 运行 `test_mode_monitor_runtime.py` 验证

### 问题 4: 样式不正确
**检查**:
1. mode-monitor.css 是否加载成功
2. 浏览器是否缓存了旧版本
3. 检查 CSS 文件路径是否正确

---

## 📝 演示脚本

### 适用于演示或培训

**开场**:
"大家好，今天我将演示 Mode Monitor 在 AgentOS WebUI 中的集成效果。"

**步骤 1** - 启动:
"首先，我们启动 WebUI 服务..."
```bash
python -m agentos.webui.app
```

**步骤 2** - 导航:
"打开浏览器，在 Observability 部分可以看到新的 Mode Monitor 导航项..."

**步骤 3** - 界面:
"点击后，我们可以看到三个统计卡片和告警列表..."

**步骤 4** - 功能:
"让我演示一下刷新功能..." [点击 Refresh]

**步骤 5** - API:
"我们也可以通过 API 直接访问数据..." [运行 curl 命令]

**结束**:
"Mode Monitor 已成功集成，提供了实时的监控能力。"

---

## 📚 相关资源

- **完整报告**: `TASK15_MODE_MONITOR_INTEGRATION_REPORT.md`
- **快速参考**: `TASK15_QUICK_REFERENCE.md`
- **API 文档**: `agentos/webui/api/mode_monitoring.py`
- **前端代码**: `agentos/webui/static/js/views/ModeMonitorView.js`

---

## 🎉 演示成功标志

如果以下所有项都正常，演示成功:

1. ✅ WebUI 成功启动
2. ✅ Mode Monitor 导航项可见
3. ✅ 页面正确显示
4. ✅ 统计卡片显示数据
5. ✅ Refresh 按钮工作
6. ✅ API 返回正确数据
7. ✅ 无控制台错误
8. ✅ 样式显示美观

**恭喜！Mode Monitor 集成完成！** 🎊
