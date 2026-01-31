# Governance Dashboard 验收清单

## 概述

本文档提供 Governance Dashboard 的完整验收标准,覆盖五个维度:
1. API 功能完整性
2. UI 功能完整性
3. 空态/降级处理
4. 响应式设计
5. 文档完整性

**验收原则**: 所有复选框必须打勾才能视为"准备交付"。

---

## 维度 1: API 功能完整性

### 1.1 端点可用性

- [ ] **GET /api/governance/dashboard 端点可访问**
  - 测试: `curl http://localhost:5000/api/governance/dashboard`
  - 预期: HTTP 200 响应

- [ ] **支持 timeframe 参数**
  - 测试: `curl http://localhost:5000/api/governance/dashboard?timeframe=7d`
  - 预期: 返回 7 天数据

- [ ] **支持 30d 时间范围**
  - 测试: `curl http://localhost:5000/api/governance/dashboard?timeframe=30d`
  - 预期: 返回 30 天数据

- [ ] **支持 90d 时间范围**
  - 测试: `curl http://localhost:5000/api/governance/dashboard?timeframe=90d`
  - 预期: 返回 90 天数据

- [ ] **支持 project_id 过滤 (可选)**
  - 测试: `curl http://localhost:5000/api/governance/dashboard?project_id=proj-123`
  - 预期: 返回该项目的数据

### 1.2 响应结构完整性

- [ ] **返回 metrics 字段**
  - 包含: risk_level, open_findings, blocked_rate, guarded_percentage
  - 类型: risk_level (string), 其他 (number/float)

- [ ] **返回 trends 字段**
  - 包含: findings, blocked_decisions, guardian_coverage
  - 每个趋势包含: current, previous, change, direction, data_points

- [ ] **返回 top_risks 字段**
  - 类型: 数组,最多 5 个元素
  - 每个风险包含: id, type, severity, title, affected_tasks, first_seen

- [ ] **返回 health 字段**
  - 包含: guardian_coverage, avg_decision_latency_ms, tasks_with_audits, active_guardians, last_scan

- [ ] **返回 generated_at 字段**
  - 类型: ISO8601 时间戳字符串

### 1.3 数据正确性

- [ ] **risk_level 计算正确**
  - 有 CRITICAL findings → 返回 "CRITICAL"
  - 有 >5 HIGH findings → 返回 "HIGH"
  - 有 1-5 HIGH findings → 返回 "MEDIUM"
  - 否则 → 返回 "LOW"

- [ ] **open_findings 计算正确**
  - 等于: findings 中 linked_task_id 为 NULL 的数量

- [ ] **blocked_rate 计算正确**
  - 等于: SUPERVISOR_BLOCKED 事件数 / 总 SUPERVISOR_* 事件数
  - 范围: 0.0 - 1.0

- [ ] **guarded_percentage 计算正确**
  - 等于: 有 guardian review 的任务数 / 总任务数
  - 范围: 0.0 - 1.0

- [ ] **趋势 direction 计算正确**
  - change > 0.05 → "up"
  - change < -0.05 → "down"
  - 否则 → "stable"

- [ ] **top_risks 排序正确**
  - 按评分排序 (severity_weight * time_weight + affected_tasks * 0.5)
  - 最多返回 5 个

### 1.4 错误处理

- [ ] **无效 timeframe 返回 400**
  - 测试: `curl http://localhost:5000/api/governance/dashboard?timeframe=invalid`
  - 预期: HTTP 400

- [ ] **空数据时返回 200 (不是 500)**
  - 测试: 清空数据库后请求
  - 预期: HTTP 200,返回零值/空数组

- [ ] **数据库错误时返回 500**
  - 测试: 模拟数据库连接失败
  - 预期: HTTP 500,包含错误信息

### 1.5 性能要求

- [ ] **响应时间 < 1s (100+ 记录)**
  - 测试: 插入 100+ findings/audits/reviews,测量响应时间
  - 工具: `time curl http://localhost:5000/api/governance/dashboard`
  - 预期: < 1000ms

- [ ] **缓存机制有效 (5 分钟)**
  - 测试: 连续请求两次 (5 分钟内)
  - 预期: 第二次请求明显更快 (< 10ms)

- [ ] **缓存过期后重新计算**
  - 测试: 等待 6 分钟后再次请求
  - 预期: 重新查询数据库,响应时间恢复到正常值

---

## 维度 2: UI 功能完整性

### 2.1 页面导航

- [ ] **Dashboard 页面可通过导航访问**
  - 操作: 点击左侧菜单 "Governance" → "Dashboard"
  - 预期: 跳转到 Dashboard 页面

- [ ] **URL 路由正确**
  - 操作: 访问 `http://localhost:5000/#governance-dashboard`
  - 预期: 直接加载 Dashboard 页面

### 2.2 核心指标显示

- [ ] **Risk Level 徽章正确显示**
  - 组件: RiskBadge
  - 检查: 颜色与等级匹配 (CRITICAL=红, HIGH=橙, MEDIUM=黄, LOW=绿)

- [ ] **Open Findings 数字正确显示**
  - 组件: MetricCard
  - 检查: 数值与 API 响应一致

- [ ] **Blocked Rate 百分比正确显示**
  - 组件: MetricCard
  - 检查: 显示为百分比 (如 8.4%)

- [ ] **Guardian Coverage 进度条正确显示**
  - 组件: HealthIndicator
  - 检查: 进度条宽度与百分比匹配

### 2.3 趋势图显示

- [ ] **Findings Trend 正确显示**
  - 包含: 当前值、趋势方向 (↑↓→)、变化百分比、Sparkline
  - 检查: 所有元素显示正确

- [ ] **Blocked Decisions Trend 正确显示**
  - 包含: 当前值、趋势方向、变化百分比、Sparkline
  - 检查: 百分比格式正确 (如 8.4%)

- [ ] **Guardian Coverage Trend 正确显示**
  - 包含: 当前值、趋势方向、变化百分比、Sparkline
  - 检查: 百分比格式正确

- [ ] **Sparkline 迷你图正确渲染**
  - 检查: 折线图显示,至少 7 个数据点

### 2.4 Top Risks 列表

- [ ] **Top Risks 列表正确显示**
  - 最多 5 个风险
  - 每个风险包含: severity badge, title, affected tasks, time

- [ ] **Severity Badge 颜色正确**
  - CRITICAL → 红色
  - HIGH → 橙色
  - MEDIUM → 黄色

- [ ] **相对时间格式正确**
  - 显示为 "2h ago", "3d ago" 等

- [ ] **空态正确显示**
  - 当无风险时显示 "No critical risks detected" 和绿色勾

### 2.5 Health 指标显示

- [ ] **Guardian Coverage 显示正确**
  - 百分比 + 进度条

- [ ] **Avg Decision Latency 显示正确**
  - 毫秒值 + 颜色编码 (绿/黄/红)

- [ ] **Tasks with Audits 显示正确**
  - 百分比 + 进度条

- [ ] **Active Guardians 显示正确**
  - 整数值

- [ ] **Last Scan 显示正确**
  - 时间戳或 "N/A"

### 2.6 交互功能

- [ ] **时间范围选择器可用**
  - 操作: 切换 7d → 30d → 90d
  - 预期: 页面重新加载对应数据

- [ ] **手动刷新按钮可用**
  - 操作: 点击 "Refresh" 按钮
  - 预期: 显示 Loading,然后更新数据

- [ ] **自动刷新功能可用**
  - 操作: 勾选 "Auto Refresh" 复选框
  - 预期: 每 5 分钟自动刷新

- [ ] **自动刷新可关闭**
  - 操作: 取消勾选 "Auto Refresh"
  - 预期: 停止自动刷新

### 2.7 元数据显示

- [ ] **"Last updated" 时间戳显示**
  - 位置: Dashboard 底部
  - 格式: 本地化时间字符串

---

## 维度 3: 空态 / 降级处理

### 3.1 完全空数据

- [ ] **数据库为空时显示合理的空态**
  - Risk Level: LOW (不是 UNKNOWN)
  - Open Findings: 0
  - Blocked Rate: 0.0%
  - Guardian Coverage: 0%
  - Top Risks: "No critical risks detected"

- [ ] **不显示错误提示 (除非 API 失败)**
  - 空数据是正常状态,不是错误

### 3.2 部分数据缺失

- [ ] **findings 表为空时其他数据仍显示**
  - risk_level = "LOW"
  - open_findings = 0
  - top_risks = []
  - 其他指标正常显示

- [ ] **guardian_reviews 表为空时其他数据仍显示**
  - guarded_percentage = 0.0
  - active_guardians = 0
  - 其他指标正常显示

- [ ] **task_audits 表为空时其他数据仍显示**
  - blocked_rate = 0.0
  - avg_decision_latency_ms = 0
  - 其他指标正常显示

### 3.3 API 失败处理

- [ ] **API 请求失败时显示友好错误提示**
  - 测试: 停止 API 服务,刷新页面
  - 预期: 显示错误图标和消息

- [ ] **错误提示包含重试按钮**
  - 操作: 点击 "Retry" 按钮
  - 预期: 重新请求 API

- [ ] **网络超时时显示超时提示**
  - 测试: 模拟慢速网络
  - 预期: 显示超时错误和重试选项

### 3.4 加载状态

- [ ] **首次加载显示 Loading spinner**
  - 检查: "Loading governance data..." 提示

- [ ] **刷新时显示 Loading 状态**
  - 操作: 点击 Refresh
  - 预期: 短暂显示 Loading 提示

- [ ] **Loading 状态不会永久卡住**
  - 测试: 即使 API 失败,也会显示错误状态 (不是一直 Loading)

---

## 维度 4: 响应式设计

### 4.1 大屏 (1400px+)

- [ ] **完整布局显示**
  - Metrics: 4 列
  - Trends: 3 列
  - 所有元素可见

- [ ] **间距和字体合理**
  - 不会显得过于拥挤或稀疏

### 4.2 笔记本 (1024px)

- [ ] **Metrics 自适应为 2 列**
  - Risk Level 和 Open Findings 一行
  - Blocked Rate 和 Guardian Coverage 一行

- [ ] **Trends 保持 3 列或自适应**
  - 根据具体布局调整

- [ ] **文字大小适中,可读性良好**

### 4.3 平板 (768px)

- [ ] **单列布局**
  - 所有卡片垂直堆叠

- [ ] **卡片宽度 100%**
  - 充分利用屏幕宽度

- [ ] **触摸目标足够大 (>44px)**
  - 按钮和选择器易于点击

### 4.4 手机 (480px)

- [ ] **优化间距和字体**
  - 字体不会过小
  - 间距不会过大或过小

- [ ] **控件垂直排列**
  - Timeframe selector, Refresh button, Auto refresh 垂直堆叠

- [ ] **Sparkline 在小屏幕上仍可见**
  - 简化或缩小但保持可读

### 4.5 打印友好

- [ ] **打印时布局正确**
  - 操作: Ctrl/Cmd + P
  - 预期: 打印预览显示完整内容

- [ ] **打印时移除不必要元素**
  - 导航栏、按钮等不打印

- [ ] **打印时保持颜色 (可选) 或转为灰度**

---

## 维度 5: 文档完整性

### 5.1 技术文档

- [ ] **dashboard_overview.md 存在**
  - 路径: `/docs/governance/dashboard_overview.md`
  - 内容: 设计理念、信息架构、技术栈

- [ ] **dashboard_api.md 存在**
  - 路径: `/docs/governance/dashboard_api.md`
  - 内容: API 端点规范、请求/响应示例、聚合算法

- [ ] **技术文档包含完整示例**
  - curl 示例
  - Python/JavaScript 集成示例

### 5.2 C-level 文档

- [ ] **dashboard_for_executives.md 存在**
  - 路径: `/docs/governance/dashboard_for_executives.md`
  - 内容: 非技术人员使用指南、指标解读、常见问题

- [ ] **使用指南清晰易懂**
  - 无技术术语
  - 包含实际业务场景

### 5.3 演示脚本

- [ ] **GOVERNANCE_DASHBOARD_DEMO_SCRIPT.md 存在**
  - 路径: `/GOVERNANCE_DASHBOARD_DEMO_SCRIPT.md`
  - 内容: 10 分钟完整版、5 分钟精简版、3 分钟超精简版

- [ ] **演示脚本包含常见问题应答**

- [ ] **演示脚本包含突发情况应对**

### 5.4 验收清单

- [ ] **本文档 (GOVERNANCE_DASHBOARD_ACCEPTANCE_CHECKLIST.md) 存在**
  - 路径: `/GOVERNANCE_DASHBOARD_ACCEPTANCE_CHECKLIST.md`

### 5.5 测试文档

- [ ] **测试覆盖文档存在**
  - 说明单元测试、集成测试、E2E 测试的覆盖范围

- [ ] **测试运行说明清晰**
  - 如何运行测试
  - 如何查看测试覆盖率

---

## 额外检查

### 代码质量

- [ ] **所有可视化组件正确集成**
  - RiskBadge, MetricCard, TrendSparkline, HealthIndicator

- [ ] **样式与现有 WebUI 一致**
  - 颜色、字体、间距符合 AgentOS 设计规范

- [ ] **无 console 错误**
  - 操作: 打开浏览器开发者工具 Console
  - 预期: 无红色错误信息

- [ ] **无 TypeScript/ESLint 警告**
  - 操作: 运行 `npx eslint static/js/views/GovernanceDashboardView.js`
  - 预期: 无警告或错误

- [ ] **代码有适当注释**
  - 关键函数有文档字符串
  - 复杂逻辑有行内注释

- [ ] **Git commit 信息清晰**
  - 遵循 Conventional Commits 规范
  - 每个 commit 原子化,可独立理解

### 安全检查

- [ ] **无 SQL 注入风险**
  - 所有数据库查询使用参数化查询
  - 无字符串拼接 SQL

- [ ] **无 XSS 风险**
  - 所有用户输入经过 HTML 转义
  - 使用 `.textContent` 而非 `.innerHTML` (除非必要)

- [ ] **API 端点有适当的鉴权 (如适用)**
  - 测试: 未登录时访问 API
  - 预期: 401 Unauthorized (如果需要鉴权)

- [ ] **敏感数据不在前端暴露**
  - 无密码、Token 等敏感信息在前端代码或 console

---

## 性能基准

### 响应时间

- [ ] **API 响应时间 < 1s (100+ 记录)**
  - 测试方法: `time curl http://localhost:5000/api/governance/dashboard`
  - 目标: < 1000ms

- [ ] **页面首次加载 < 2s**
  - 测试方法: 浏览器 Network tab,测量 DOMContentLoaded
  - 目标: < 2000ms

- [ ] **切换时间范围 < 1s**
  - 测试方法: 从 7d 切换到 30d,测量响应时间
  - 目标: < 1000ms

- [ ] **手动刷新 < 1s**
  - 测试方法: 点击 Refresh,测量响应时间
  - 目标: < 1000ms

- [ ] **无明显卡顿或延迟**
  - 主观测试: 所有操作感觉流畅

### 内存使用

- [ ] **长时间运行不会内存泄漏**
  - 测试: 开启自动刷新,运行 1 小时,监控内存使用
  - 预期: 内存使用稳定,不持续增长

---

## 测试覆盖

### 单元测试

- [ ] **API aggregation functions 有单元测试**
  - 测试: `aggregate_risk_level()`, `calculate_blocked_rate()` 等
  - 覆盖率: > 80%

- [ ] **Trend calculation 有单元测试**
  - 测试: `compute_trend()` 函数

- [ ] **Risk scoring 有单元测试**
  - 测试: `identify_top_risks()` 函数

### 集成测试

- [ ] **Dashboard API 集成测试存在**
  - 路径: `tests/integration/governance/test_dashboard_api.py`
  - 覆盖: 完整数据流、空数据、大数据量、缓存

- [ ] **所有集成测试通过**
  - 运行: `pytest tests/integration/governance/test_dashboard_api.py -v`
  - 预期: 全部 PASSED

### E2E 测试

- [ ] **Dashboard 页面 E2E 测试存在**
  - 路径: `tests/e2e/test_governance_dashboard_flow.py`
  - 覆盖: 导航、时间范围切换、刷新、空态

- [ ] **所有 E2E 测试通过**
  - 运行: `pytest tests/e2e/test_governance_dashboard_flow.py -v`
  - 预期: 全部 PASSED

---

## 部署就绪

### 配置

- [ ] **无硬编码配置**
  - 端口、URL 等从环境变量读取

- [ ] **有合理的默认值**
  - 即使不配置环境变量也能运行

### 依赖

- [ ] **requirements.txt / pyproject.toml 已更新**
  - 包含所有新增依赖

- [ ] **前端依赖已说明**
  - 无需额外安装 npm 包 (纯 vanilla JS)

### 迁移

- [ ] **数据库迁移脚本存在 (如需要)**
  - 新增表或字段有迁移脚本

- [ ] **迁移脚本可幂等执行**
  - 多次执行不会出错

---

## 最终验收签字

### 开发者自检

- [ ] **我已完成所有上述检查项**
- [ ] **我已运行所有测试且全部通过**
- [ ] **我已在本地环境完整测试所有功能**
- [ ] **我已阅读所有文档,确保准确性**

**开发者签名**: _______________ **日期**: _______________

### Code Review

- [ ] **代码已通过 peer review**
- [ ] **无明显代码异味 (code smell)**
- [ ] **遵循项目编码规范**

**Reviewer 签名**: _______________ **日期**: _______________

### QA 测试

- [ ] **QA 已完成功能测试**
- [ ] **QA 已完成兼容性测试 (多浏览器)**
- [ ] **QA 已完成性能测试**

**QA 签名**: _______________ **日期**: _______________

### Product Owner 验收

- [ ] **功能符合需求规格**
- [ ] **用户体验符合预期**
- [ ] **文档完整且清晰**

**PO 签名**: _______________ **日期**: _______________

---

## 验收标准总结

| 维度 | 检查项总数 | 必须通过 | 完成状态 |
|------|-----------|----------|---------|
| API 功能完整性 | 25 | 25 | ⬜ |
| UI 功能完整性 | 32 | 32 | ⬜ |
| 空态/降级处理 | 15 | 15 | ⬜ |
| 响应式设计 | 16 | 16 | ⬜ |
| 文档完整性 | 13 | 13 | ⬜ |
| 额外检查 | 14 | 14 | ⬜ |
| 性能基准 | 6 | 6 | ⬜ |
| 测试覆盖 | 7 | 7 | ⬜ |
| 部署就绪 | 6 | 6 | ⬜ |
| **总计** | **134** | **134** | **⬜** |

**验收结论**: ⬜ 通过 / ⬜ 不通过 / ⬜ 有条件通过

**备注**: _____________________________________________________________

---

## 版本历史

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| 1.0 | 2026-01-29 | 初始版本 | AgentOS Team |

---

**注意事项**:
1. 所有检查项必须在提交 PR 前完成
2. 如有无法完成的项,需在 PR 描述中说明原因
3. 有条件通过的项需在 PR 中创建后续 Issue
4. 本清单应随功能演进持续更新
