# Task #13: ModeMonitorView 快速参考

## 📁 文件位置
```
/Users/pangge/PycharmProjects/AgentOS/agentos/webui/static/js/views/ModeMonitorView.js
```

## 🔧 核心 API

### 类实例化
```javascript
import ModeMonitorView from './views/ModeMonitorView.js';
const view = new ModeMonitorView();
```

### 主要方法

| 方法 | 说明 | 返回值 |
|-----|------|--------|
| `async render(container)` | 渲染视图到容器 | `Promise<void>` |
| `async loadAlerts()` | 从 API 加载数据 | `Promise<void>` |
| `updateStats()` | 更新统计卡片 | `void` |
| `renderAlerts()` | 渲染告警列表 | `void` |
| `startAutoRefresh()` | 启动10秒自动刷新 | `void` |
| `stopAutoRefresh()` | 停止自动刷新 | `void` |
| `destroy()` | 清理资源 | `void` |

## 🌐 API 端点

**GET** `/api/mode/alerts`

响应格式:
```json
{
    "alerts": [
        {
            "severity": "error",
            "mode_id": "WRITE",
            "timestamp": "2026-01-30T12:34:56.789Z",
            "operation": "file_write",
            "message": "Blocked dangerous operation"
        }
    ],
    "stats": {
        "total_alerts": 10,
        "severity_breakdown": {
            "error": 2,
            "warning": 5,
            "info": 3
        }
    }
}
```

## 🎨 CSS 类名

### 容器
- `.mode-monitor` - 主容器
- `.stats-grid` - 统计卡片网格
- `.alerts-section` - 告警区域

### 统计卡片
- `.stat-card` - 统计卡片
- `.stat-value` - 统计值
- `.stat-value.error` - 错误统计（红色）
- `.stat-value.warning` - 警告统计（黄色）

### 告警卡片
- `.alert-item` - 告警卡片
- `.alert-item.error` - 错误告警
- `.alert-item.warning` - 警告告警
- `.alert-item.info` - 信息告警
- `.alert-header` - 告警头部
- `.alert-body` - 告警内容
- `.severity-badge` - 严重性徽章
- `.mode-badge` - 模式徽章
- `.timestamp` - 时间戳
- `.no-alerts` - 无告警提示

### 按钮
- `.btn-primary` - 主按钮

## 📋 HTML 结构

```html
<div class="mode-monitor">
    <h2>🛡️ Mode System Monitor</h2>

    <div class="stats-grid">
        <div class="stat-card">
            <h3>Total Alerts</h3>
            <div class="stat-value" id="total-alerts">0</div>
        </div>
        <!-- ... 更多卡片 ... -->
    </div>

    <div class="alerts-section">
        <h3>Recent Alerts</h3>
        <div id="alerts-list">
            <div class="alert-item error">
                <div class="alert-header">
                    <span class="severity-badge error">error</span>
                    <span class="mode-badge">WRITE</span>
                    <span class="timestamp">1/30/2026, 12:34:56 PM</span>
                </div>
                <div class="alert-body">
                    <strong>file_write</strong>: Message here
                </div>
            </div>
        </div>
    </div>

    <button id="refresh-btn" class="btn-primary">Refresh</button>
</div>
```

## 🔒 安全特性

1. **XSS 防护**: 所有用户输入通过 `escapeHtml()` 转义
2. **空值安全**: 使用可选链 `?.` 和默认值 `|| 0`
3. **DOM 检查**: 所有 DOM 操作前检查元素存在性
4. **错误处理**: try-catch 包裹所有异步操作

## ⚙️ 配置选项

### 刷新间隔
修改 `startAutoRefresh()` 中的间隔：
```javascript
this.refreshInterval = setInterval(() => {
    this.loadAlerts();
}, 10000); // 改为其他毫秒值
```

## 🧪 测试

运行测试页面：
```bash
open test_mode_monitor_view.html
```

测试覆盖：
- ✅ 类实例化
- ✅ 构造函数属性
- ✅ 所有方法存在性
- ✅ ES6 模块导出
- ✅ HTML 结构渲染

## 🔄 生命周期

```javascript
// 1. 创建实例
const view = new ModeMonitorView();

// 2. 渲染（自动执行以下步骤）
await view.render(container);
//   -> attachEventListeners()
//   -> loadAlerts()
//   -> startAutoRefresh()

// 3. 运行时（每10秒自动刷新）
//   -> loadAlerts()
//       -> updateStats()
//       -> renderAlerts()

// 4. 清理
view.destroy();
//   -> stopAutoRefresh()
```

## 📊 状态管理

```javascript
// 内部状态
{
    alerts: [],          // 告警数组
    stats: {},           // 统计数据
    refreshInterval: null // 定时器引用
}
```

## 🚨 错误处理

视图会自动处理以下错误：
- API 请求失败
- JSON 解析错误
- DOM 操作错误
- 时间戳格式化错误

错误会：
1. 记录到控制台 (`console.error`)
2. 显示用户友好的错误消息

## 🎯 下一步

- Task #14: 创建监控页面样式
- Task #15: 集成监控到 WebUI

---

**完成日期**: 2026-01-30
