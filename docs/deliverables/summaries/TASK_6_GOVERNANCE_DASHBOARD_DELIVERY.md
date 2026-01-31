# Task #6: Governance Dashboard WebUI 主视图 - 交付文档

**交付时间**: 2026-01-29
**负责人**: Claude (Sonnet 4.5)
**Sprint**: v0.3.2 - WebUI 100% Coverage

---

## 📦 交付内容

### 1. 新建文件

#### JavaScript View
- **文件**: `agentos/webui/static/js/views/GovernanceDashboardView.js`
- **大小**: 15KB
- **功能**:
  - C-level Governance Dashboard 主视图
  - 实时治理健康度指标
  - 趋势分析 (7d/30d/90d)
  - Top Risks 可视化
  - 健康指标展示
  - 自动刷新功能

#### CSS 样式文件
- **文件**: `agentos/webui/static/css/governance-dashboard.css`
- **大小**: 7.6KB
- **功能**:
  - Dashboard 布局样式
  - 响应式设计 (大屏/笔电/iPad/手机)
  - Metrics/Trends/Risks/Health 区域样式
  - 空态和错误状态样式

#### 测试文件
- **文件**: `test_governance_dashboard.html`
- **功能**: 独立测试 Dashboard，使用 mock 数据

### 2. 修改文件

#### index.html
**修改位置**: `agentos/webui/templates/index.html`

**变更内容**:
1. **导航菜单** (Line 165-179):
   - 添加 "Dashboard" 菜单项（Governance 分组第一个）
   - 使用 chart-bar 图标
   - 路由: `data-view="governance-dashboard"`

2. **CSS 引入** (Line 29):
   ```html
   <link rel="stylesheet" href="/static/css/governance-dashboard.css?v=1">
   ```

3. **组件 JS 引入** (Lines 367-371):
   ```html
   <!-- Governance Dashboard Components (Task #7) -->
   <script src="/static/js/components/RiskBadge.js?v=1"></script>
   <script src="/static/js/components/TrendSparkline.js?v=1"></script>
   <script src="/static/js/components/MetricCard.js?v=1"></script>
   <script src="/static/js/components/HealthIndicator.js?v=1"></script>
   ```

4. **View JS 引入** (Line 403):
   ```html
   <script src="/static/js/views/GovernanceDashboardView.js?v=1"></script>
   ```

#### main.js
**修改位置**: `agentos/webui/static/js/main.js`

**变更内容**:
1. **路由添加** (Lines 174-176):
   ```javascript
   case 'governance-dashboard':
       renderGovernanceDashboardView(container);
       break;
   ```

2. **渲染函数添加** (Lines 4439-4448):
   ```javascript
   function renderGovernanceDashboardView(container) {
       if (state.currentViewInstance && state.currentViewInstance.destroy) {
           state.currentViewInstance.destroy();
       }
       state.currentViewInstance = new GovernanceDashboardView();
       state.currentViewInstance.render(container);
   }
   ```

#### components.css
**修改位置**: `agentos/webui/static/css/components.css`

**变更内容**:
- 追加 Dashboard 可视化组件样式 (~250 lines)
- RiskBadge 组件样式
- MetricCard 组件样式
- TrendSparkline 组件样式
- HealthIndicator 组件样式

---

## ✅ 验收标准完成情况

### 核心功能
- ✅ Dashboard 页面可通过导航访问
- ✅ 显示 4 个核心指标
  - ✅ Risk Level (使用 RiskBadge 组件)
  - ✅ Open Findings (使用 MetricCard 组件)
  - ✅ Blocked Rate (使用 MetricCard 组件)
  - ✅ Guardian Coverage (使用 HealthIndicator 组件)
- ✅ 显示 3 个趋势图
  - ✅ Findings Trend (含 Sparkline)
  - ✅ Blocked Decisions Trend (含 Sparkline)
  - ✅ Guardian Coverage Trend (含 Sparkline)
- ✅ 显示 Top Risks 列表（最多 5 个）
- ✅ 显示 Health 指标（5 个子指标）

### 交互功能
- ✅ 时间范围选择器 (7d/30d/90d)
- ✅ 手动刷新按钮
- ✅ 自动刷新功能 (5 分钟间隔)
- ✅ 空态优雅处理
- ✅ 错误状态优雅处理

### 设计要求
- ✅ 响应式设计
  - ✅ 大屏 (1400px+): 完整网格布局
  - ✅ 笔电 (1024px): 2 列 Metrics
  - ✅ iPad (768px): 单列 Metrics
  - ✅ 手机 (480px): 优化间距和字体
- ✅ 使用 Task #7 的可视化组件
- ✅ 样式一致性（与现有 WebUI 保持一致）

---

## 🎨 UX 原则实现

Dashboard 回答的 5 个核心问题：

1. **安全吗？**
   ✅ Risk Level Badge 一眼可见（CRITICAL/HIGH/MEDIUM/LOW）

2. **趋势如何？**
   ✅ 3 个趋势卡片，带 Sparkline 和方向指示器

3. **最严重的是什么？**
   ✅ Top Risks 区域，按严重程度排序，突出显示

4. **治理系统在工作吗？**
   ✅ Health Indicators 展示系统健康度（覆盖率、延迟、审计率）

5. **有人负责吗？**
   ✅ Active Guardians 指标 + Last Scan 时间戳

---

## 🔌 API 集成

### 依赖的 API 端点
- **GET** `/api/governance/dashboard?timeframe={7d|30d|90d}`

### 数据结构契约
```typescript
interface DashboardResponse {
    generated_at: string;
    metrics: {
        risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
        open_findings: number;
        blocked_rate: number;
        guarded_percentage: number;
    };
    trends: {
        findings: TrendData;
        blocked_decisions: TrendData;
        guardian_coverage: TrendData;
    };
    top_risks: Array<RiskItem>;
    health: HealthMetrics;
}

interface TrendData {
    current: number;
    direction: 'up' | 'down' | 'stable';
    change: number;
    data_points: number[];
}
```

---

## 📊 组件使用说明

### 1. RiskBadge
```javascript
new RiskBadge({
    container: '#metric-risk-level',
    level: 'HIGH',
    size: 'large',
    showIcon: true,
});
```

### 2. MetricCard
```javascript
new MetricCard({
    container: '#metric-open-findings',
    title: 'Open Findings',
    value: 23,
    size: 'medium',
    icon: '🔍',
    trend: 'up',
    trendValue: 15,
    sparklineData: [18, 19, 20, 21, 22, 23, 25]
});
```

### 3. HealthIndicator
```javascript
new HealthIndicator({
    container: '#metric-guarded-percentage',
    mode: 'bar',
    percentage: 85,
    label: 'Guardian Coverage',
    thresholds: { critical: 50, warning: 70 }
});
```

---

## 🧪 测试指南

### 手动测试步骤

1. **启动 WebUI**:
   ```bash
   cd agentos
   python -m agentos.webui.app
   ```

2. **访问 Dashboard**:
   - 导航到 `http://localhost:5000`
   - 点击左侧菜单 "Governance" > "Dashboard"

3. **功能测试**:
   - ✅ 检查页面加载（显示 Loading 状态）
   - ✅ 验证 Metrics 区域显示 4 个指标
   - ✅ 验证 Trends 区域显示 3 个趋势卡片
   - ✅ 验证 Top Risks 区域显示风险列表
   - ✅ 验证 Health 区域显示健康指标

4. **交互测试**:
   - ✅ 切换时间范围 (7d/30d/90d)
   - ✅ 点击刷新按钮
   - ✅ 启用/禁用自动刷新

5. **响应式测试**:
   - ✅ 调整浏览器窗口大小
   - ✅ 在移动设备上测试

### 独立测试

打开 `test_governance_dashboard.html` 在浏览器中查看（使用 mock 数据）。

---

## 📝 代码质量

### 代码组织
- ✅ 单一职责原则：每个方法专注一个功能
- ✅ 清晰的命名约定
- ✅ 详细的 JSDoc 注释
- ✅ 错误处理完善

### 性能优化
- ✅ 使用 event delegation
- ✅ 防抖/节流（时间选择器）
- ✅ 按需销毁组件
- ✅ CSS 动画使用 transform

### 可维护性
- ✅ 模块化设计
- ✅ 配置与逻辑分离
- ✅ 易于扩展新的指标类型
- ✅ 遵循现有代码风格

---

## 🔗 依赖关系

### 前置任务
- ✅ Task #5: Dashboard 聚合 API (已完成)
- ✅ Task #7: 可视化组件库 (已完成)

### 被依赖任务
- Task #8: Dashboard 文档和验收 Checklist (待完成)
- Task #3: Guardian Reviews Tab (可选集成)

---

## 🚀 部署清单

### 文件清单
```
agentos/webui/static/js/views/GovernanceDashboardView.js  (新增)
agentos/webui/static/css/governance-dashboard.css        (新增)
agentos/webui/templates/index.html                       (修改)
agentos/webui/static/js/main.js                          (修改)
agentos/webui/static/css/components.css                  (修改)
```

### 版本号更新
- GovernanceDashboardView.js: v1
- governance-dashboard.css: v1
- 组件 JS: v1 (已在 Task #7 完成)

### 浏览器兼容性
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

---

## 📚 文档链接

### 相关文档
- [Task #5: Dashboard API 交付文档](./TASK_5_DASHBOARD_API_DELIVERY.md)
- [Task #7: 可视化组件库交付文档](./TASK_7_VISUALIZATION_COMPONENTS_DELIVERY.md)
- [Governance Dashboard Design Spec](./docs/governance/dashboard_design.md)

### API 文档
- Dashboard API: `/api/governance/dashboard`
- 参数: `?timeframe={7d|30d|90d}`

---

## ⚠️ 已知限制

1. **数据刷新**:
   - 自动刷新间隔固定为 5 分钟
   - 未来可考虑动态调整间隔

2. **错误处理**:
   - 网络错误显示通用错误消息
   - 未来可添加更详细的错误分类

3. **国际化**:
   - 当前仅支持英文
   - 未来可添加多语言支持

4. **可访问性**:
   - 基本键盘导航支持
   - 未来可增强屏幕阅读器支持

---

## 🎯 下一步工作

1. **Task #8**: 编写完整的 Dashboard 使用文档
2. **Task #3**: 集成 Guardian Reviews Tab（可选）
3. **性能优化**: 添加虚拟滚动（如果 Top Risks 数量很大）
4. **增强功能**:
   - 添加导出功能（PDF/CSV）
   - 添加钉选/收藏功能
   - 添加自定义 Dashboard 布局

---

## ✅ 交付确认

**状态**: ✅ **已完成**
**质量**: 🟢 **Production Ready**
**测试**: ✅ **手动测试通过**

所有验收标准已满足，代码已提交，可进入下一阶段。

---

**交付签字**:
- 开发: Claude (Sonnet 4.5) - 2026-01-29
- 审核: 待 Code Review
- 验收: 待 UAT
