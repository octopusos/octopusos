# Governance Dashboard 快速入门指南

## 🎯 概述

Governance Dashboard 是 AgentOS 的 C-level 治理监控中心，提供系统治理健康度的一页式视图。

**5 秒问答**:
- 安全吗？ → Risk Level Badge
- 趋势如何？ → 3 个趋势卡片
- 最严重的是什么？ → Top Risks 列表
- 治理系统在工作吗？ → Health Indicators
- 有人负责吗？ → Active Guardians + Last Scan

---

## 🚀 快速开始

### 1. 访问 Dashboard

```bash
# 启动 WebUI
cd agentos
python -m agentos.webui.app

# 浏览器访问
http://localhost:5000
```

在左侧导航菜单中点击: **Governance > Dashboard**

---

## 📊 Dashboard 布局

```
┌─────────────────────────────────────────────────────┐
│  Governance Dashboard                    [时间选择]  │
│                                         [刷新] [自动] │
├─────────────────────────────────────────────────────┤
│  Metrics 区域 (4 个核心指标)                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  │Risk  │ │Open  │ │Block │ │Guard │               │
│  │Level │ │Finds │ │Rate  │ │Cover │               │
│  └──────┘ └──────┘ └──────┘ └──────┘               │
├─────────────────────────────────────────────────────┤
│  Trends 区域 (3 个趋势图)                            │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐         │
│  │ Findings  │ │  Blocked  │ │ Coverage  │         │
│  │  ↑ +15%   │ │  ↓ -5%    │ │  ↑ +10%   │         │
│  │ ▁▂▃▄▅▆▇   │ │ ▇▆▅▄▃▂▁   │ │ ▁▂▃▄▅▆▇   │         │
│  └───────────┘ └───────────┘ └───────────┘         │
├─────────────────────────────────────────────────────┤
│  Top Risks 区域 (最多 5 个风险)                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ [CRITICAL] FORBIDDEN_OPERATION  2h ago      │   │
│  │ Attempted file deletion in protected dir    │   │
│  │ ⚠️ 3 tasks affected                          │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│  Health 区域 (5 个健康指标)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Guardian  │ │Latency   │ │Audit     │           │
│  │Coverage  │ │125ms ✓   │ │Coverage  │           │
│  │85% ████▌ │ │          │ │92% ████▍ │           │
│  └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────┘
```

---

## 🎛️ 控制面板

### 时间范围选择
```
[Last 7 Days  ▼]
 └─ Last 7 Days    (默认)
 └─ Last 30 Days
 └─ Last 90 Days
```

**用途**: 选择趋势分析的时间窗口

### 刷新按钮
```
[🔄 Refresh]
```

**用途**: 手动刷新 Dashboard 数据

### 自动刷新
```
☐ Auto Refresh (5min)
```

**用途**: 启用后每 5 分钟自动刷新一次

---

## 📈 Metrics 区域详解

### 1. Risk Level
```
┌─────────────┐
│  ⚠ HIGH     │  ← 当前风险等级
└─────────────┘
```

**颜色编码**:
- 🔴 CRITICAL: 红色脉冲动画
- 🟠 HIGH: 橙色
- 🟡 MEDIUM: 黄色
- 🟢 LOW: 绿色

### 2. Open Findings
```
┌─────────────┐
│Open Findings│
│     23      │  ← 当前未解决的发现数
└─────────────┘
```

### 3. Blocked Rate
```
┌─────────────┐
│Blocked Rate │
│    15.0%    │  ← 被阻止的决策比例
└─────────────┘
```

### 4. Guardian Coverage
```
┌──────────────┐
│Guardian Cover│
│    85%       │
│ ████████▌    │  ← 覆盖率进度条
└──────────────┘
```

**阈值**:
- < 50%: 🔴 Critical
- 50-70%: 🟡 Warning
- > 70%: 🟢 Healthy

---

## 📊 Trends 区域详解

### Trend Card 结构
```
┌─────────────────┐
│ Findings        │  ← 指标名称
│ 23      ↑ +15%  │  ← 当前值 + 变化方向和百分比
│ ▁▂▃▄▅▆▇         │  ← Sparkline 趋势图
└─────────────────┘
```

### 趋势方向
- ↑ **Up** (绿色): 指标上升
- ↓ **Down** (红色): 指标下降
- → **Stable** (灰色): 指标稳定

### 3 个趋势指标

1. **Findings Trend**: 发现数量变化
2. **Blocked Decisions**: 阻止决策比例变化
3. **Guardian Coverage**: 守护覆盖率变化

---

## 🚨 Top Risks 区域详解

### Risk Item 结构
```
┌────────────────────────────────────────────┐
│ [CRITICAL] FORBIDDEN_OPERATION  2h ago     │  ← 严重程度 | 类型 | 时间
│ Attempted file deletion in protected dir   │  ← 风险描述
│ ⚠️ 3 tasks affected                         │  ← 影响范围
└────────────────────────────────────────────┘
```

### 严重程度颜色
- 🔴 CRITICAL: 深红背景
- 🟠 HIGH: 橙黄背景
- 🟡 MEDIUM: 浅黄背景
- 🟢 LOW: 浅绿背景

### 空态显示
```
┌────────────────────────────────────────────┐
│              ✅                              │
│      No critical risks detected            │
└────────────────────────────────────────────┘
```

---

## 💚 Health 区域详解

### 5 个健康指标

#### 1. Guardian Coverage
```
Guardian Coverage
      85%
████████▌         ← 进度条
```

#### 2. Avg Decision Latency
```
Avg Decision Latency
      125ms
      ●           ← 状态指示器
```

**颜色**:
- 🟢 < 500ms: Success
- 🟡 500-1500ms: Warning
- 🔴 > 1500ms: Danger

#### 3. Tasks with Audits
```
Tasks with Audits
      92%
█████████▏        ← 进度条
```

#### 4. Active Guardians
```
Active Guardians
       4
```

#### 5. Last Scan
```
Last Scan
2026-01-29 10:30:15
```

---

## 🔄 刷新策略

### 手动刷新
1. 点击 "🔄 Refresh" 按钮
2. 立即重新加载数据
3. 按钮显示旋转动画

### 自动刷新
1. 勾选 "☑ Auto Refresh (5min)"
2. 每 5 分钟自动刷新一次
3. 刷新期间不影响用户交互

### 数据更新流程
```
User Action
    ↓
Load Dashboard Data
    ↓
GET /api/governance/dashboard?timeframe=7d
    ↓
Render Components
    ↓
Display Dashboard
```

---

## 📱 响应式设计

### 大屏 (1400px+)
```
[Metric] [Metric] [Metric] [Metric]
[Trend ] [Trend ] [Trend ]
[Risks                    ]
[Health                   ]
```

### 笔电 (1024px)
```
[Metric] [Metric]
[Metric] [Metric]
[Trend ]
[Trend ]
[Trend ]
[Risks          ]
[Health         ]
```

### 平板 (768px)
```
[Metric]
[Metric]
[Metric]
[Metric]
[Trend ]
[Trend ]
[Trend ]
[Risks  ]
[Health ]
```

### 手机 (480px)
```
[Metric]
[Metric]
[Metric]
[Metric]
[Trend ]
[Trend ]
[Trend ]
[Risks  ]
[Health ]
```

---

## 🎨 视觉层级

### 信息优先级
1. **P0 - 关键警报**: Risk Level (脉冲动画)
2. **P1 - 核心指标**: Open Findings, Blocked Rate
3. **P2 - 趋势分析**: 3 个趋势卡片
4. **P3 - 风险详情**: Top Risks 列表
5. **P4 - 系统健康**: Health Indicators

### 视觉引导
- 🔴 红色 → 立即关注
- 🟠 橙色 → 需要注意
- 🟡 黄色 → 警告
- 🟢 绿色 → 正常
- ⚪ 灰色 → 中性信息

---

## ⌨️ 键盘快捷键

（未来实现）
- `R`: 刷新 Dashboard
- `1-3`: 切换时间范围
- `A`: 切换自动刷新
- `Esc`: 清除选择

---

## 🐛 故障排查

### 问题 1: Dashboard 加载失败
**症状**: 显示 "Failed to Load Dashboard"

**解决**:
1. 检查 API 服务是否运行
2. 打开浏览器 DevTools → Network 查看请求
3. 确认 `/api/governance/dashboard` 返回 200

### 问题 2: 数据显示不正确
**症状**: 指标为空或异常

**解决**:
1. 检查 API 响应数据格式
2. 查看浏览器 Console 是否有 JS 错误
3. 确认 Task #5 API 已正确实现

### 问题 3: 自动刷新不工作
**症状**: 勾选自动刷新后数据不更新

**解决**:
1. 打开浏览器 Console 查看错误
2. 检查是否有 JS 异常
3. 确认刷新间隔设置正确（5 分钟）

### 问题 4: 组件显示异常
**症状**: RiskBadge/MetricCard 样式错误

**解决**:
1. 确认 `components.css` 已加载
2. 确认 `governance-dashboard.css` 已加载
3. 清除浏览器缓存

---

## 📚 相关文档

- [Task #6 交付文档](./TASK_6_GOVERNANCE_DASHBOARD_DELIVERY.md)
- [Dashboard API 文档](./TASK_5_DASHBOARD_API_DELIVERY.md)
- [可视化组件库文档](./TASK_7_VISUALIZATION_COMPONENTS_DELIVERY.md)

---

## 💡 最佳实践

### 1. 监控频率
- **实时监控**: 勾选自动刷新
- **日常检查**: 每天早上查看一次
- **事件响应**: 发生告警时立即查看

### 2. 时间范围选择
- **短期分析**: 7 天（发现趋势变化）
- **中期分析**: 30 天（评估改进效果）
- **长期分析**: 90 天（季度报告）

### 3. 风险优先级处理
1. 优先处理 CRITICAL 风险
2. 关注 affected_tasks 多的风险
3. 跟踪风险 first_seen 时间

### 4. 健康度优化
- Guardian Coverage 保持 > 80%
- Decision Latency 保持 < 500ms
- Tasks with Audits 保持 > 90%

---

## 🎓 进阶使用

### 自定义监控
（未来实现）
- 自定义指标阈值
- 自定义时间范围
- 自定义风险过滤器

### 导出报告
（未来实现）
- 导出 PDF 报告
- 导出 CSV 数据
- 定期邮件推送

### 集成告警
（未来实现）
- Slack 通知
- 邮件告警
- Webhook 集成

---

**版本**: v0.3.2
**更新日期**: 2026-01-29
**状态**: ✅ Production Ready
