# Task #15 快速参考指南

## 📍 修改的文件

### 1. agentos/webui/app.py
```python
# Line 43 - 添加导入
from agentos.webui.api import ..., mode_monitoring

# Line 264 - 注册路由
app.include_router(mode_monitoring.router, prefix="/api/mode", tags=["mode"])
```

### 2. agentos/webui/templates/index.html
```html
<!-- Line 51 - CSS 链接 -->
<link rel="stylesheet" href="/static/css/mode-monitor.css?v=1">

<!-- Line 138-144 - 导航项 -->
<a href="#" class="nav-item" data-view="mode-monitor">
    <svg>...</svg>
    <span>Mode Monitor</span>
</a>

<!-- Line 509-512 - JS 模块 -->
<script type="module">
    import ModeMonitorView from "/static/js/views/ModeMonitorView.js";
    window.ModeMonitorView = ModeMonitorView;
</script>
```

### 3. agentos/webui/static/js/main.js
```javascript
// Line 278-280 - 路由 case
case 'mode-monitor':
    renderModeMonitorView(container);
    break;

// Line 5612-5655 - 渲染函数
async function renderModeMonitorView(container) { ... }
```

---

## 🚀 启动和使用

### 启动 WebUI
```bash
python -m agentos.webui.app
```

### 访问 Mode Monitor
1. 打开: `http://localhost:5000`
2. 点击导航: **Observability > Mode Monitor**

---

## 🧪 验证

### 运行集成测试
```bash
python3 test_mode_monitor_integration.py
```

### 运行运行时测试
```bash
python3 test_mode_monitor_runtime.py
```

### 手动验证 API
```bash
# 获取统计
curl http://localhost:5000/api/mode/stats

# 获取告警
curl http://localhost:5000/api/mode/alerts

# 清空告警
curl -X POST http://localhost:5000/api/mode/alerts/clear
```

---

## 📊 API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/mode/stats` | GET | 获取告警统计 |
| `/api/mode/alerts` | GET | 获取告警列表 |
| `/api/mode/alerts?severity=error` | GET | 过滤告警 |
| `/api/mode/alerts?limit=20` | GET | 限制返回数量 |
| `/api/mode/alerts/clear` | POST | 清空告警缓冲区 |

---

## ✅ 验收清单

- [x] app.py 导入 mode_monitoring
- [x] app.py 注册 API 路由
- [x] index.html 链接 CSS
- [x] index.html 添加导航项
- [x] index.html 导入 JS 模块
- [x] main.js 添加路由 case
- [x] main.js 实现渲染函数
- [x] 所有测试通过
- [x] API 端点可访问
- [x] WebUI 正常启动

---

## 📁 相关文件

- **完整报告**: `TASK15_MODE_MONITOR_INTEGRATION_REPORT.md`
- **API 实现**: `agentos/webui/api/mode_monitoring.py`
- **前端视图**: `agentos/webui/static/js/views/ModeMonitorView.js`
- **CSS 样式**: `agentos/webui/static/css/mode-monitor.css`
- **集成测试**: `test_mode_monitor_integration.py`
- **运行时测试**: `test_mode_monitor_runtime.py`

---

## 🎯 任务状态

**Task #15**: ✅ **已完成**
**完成时间**: 2026-01-30

**下一步**: Task #16 - Phase 4.1: 创建 100% 完成度验证脚本
