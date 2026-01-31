# Governance Dashboard 总览

## 设计理念

Governance Dashboard 是一个**单页式治理健康度视图**,专为 C-level 管理层和审计人员设计。它提供系统治理状态的实时快照,让管理层能够在 30 秒内了解系统的安全态势、风险趋势和治理系统健康度。

### 核心设计原则

1. **信息密度优化**: 在单个页面内展示所有关键指标,无需跳转
2. **分层信息架构**: 从高层概览到详细指标,支持快速扫描和深入分析
3. **实时性保证**: 5 分钟缓存,确保数据新鲜度
4. **优雅降级**: 部分数据缺失时仍能提供有意义的视图
5. **零学习曲线**: 直观的视觉设计,无需培训即可理解

### 回答的 5 个核心问题

Dashboard 设计围绕管理层最关心的 5 个问题:

1. **系统现在安全吗?** → Risk Level Badge (CRITICAL/HIGH/MEDIUM/LOW)
2. **最近风险是在变好还是变坏?** → Trend Sparklines (7d/30d/90d)
3. **哪些问题最严重?** → Top Risks 列表 (Top 5 按严重程度排序)
4. **治理系统有没有在工作?** → Governance Health 指标 (覆盖率、延迟)
5. **有没有人/Agent 在负责?** → Active Guardians 数量

## 信息架构

Dashboard 分为 4 个主要区域,采用卡片式布局:

```
┌─────────────────────────────────────────────────────────────┐
│                  Governance Dashboard                       │
│  [7d ▼] [Refresh] [Auto Refresh ☑]                        │
├─────────────────────────────────────────────────────────────┤
│  Metrics Section (核心指标)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Risk     │ │  Open    │ │ Blocked  │ │ Guardian │      │
│  │ Level    │ │Findings  │ │  Rate    │ │ Coverage │      │
│  │  HIGH    │ │    12    │ │  8.4%    │ │   92%    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
├─────────────────────────────────────────────────────────────┤
│  Trends Section (趋势分析)                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                   │
│  │Findings  │ │ Blocked  │ │ Coverage │                   │
│  │   12 ↓   │ │  8.4% ↓  │ │   92% ↑  │                   │
│  │ ▁▂▃▂▁▂▂  │ │ ▄▃▃▂▂▁▁  │ │ ▂▂▃▃▄▄▄  │  (Sparklines)    │
│  └──────────┘ └──────────┘ └──────────┘                   │
├─────────────────────────────────────────────────────────────┤
│  Top Risks Section (高优先级风险)                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [CRITICAL] Blocked decisions increased 45% in 24h    │  │
│  │ 12 tasks affected • 2h ago                           │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ [HIGH] High-risk operation allowed w/o Guardian      │  │
│  │ 3 tasks affected • 4h ago                            │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Health Section (治理系统健康度)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Guardian │ │   Avg    │ │  Tasks   │ │  Active  │      │
│  │ Coverage │ │ Decision │ │   with   │ │Guardians │      │
│  │   92%    │ │Latency   │ │  Audits  │ │    5     │      │
│  │ ▓▓▓▓▓▓▓░ │ │ 1200ms   │ │   98%    │ │          │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  Last Scan: 2026-01-29 11:30:00                            │
└─────────────────────────────────────────────────────────────┘
```

### 1. Metrics Section (核心指标)

位置: Dashboard 顶部,最显眼位置

**组成:**
- **Risk Level**: 系统整体风险等级 (CRITICAL/HIGH/MEDIUM/LOW)
  - 大号徽章,颜色编码 (红/橙/黄/绿)
  - 自动计算:CRITICAL findings → CRITICAL, >5 HIGH findings → HIGH
- **Open Findings**: 未解决的发现数量
  - 数字指标,无关联 follow-up task 的 findings
- **Blocked Rate**: 决策被阻止的比例
  - 百分比显示,正常范围 5-10%
- **Guardian Coverage**: Guardian 验收覆盖率
  - 进度条显示,目标 > 80%

**设计意图:**
- 第一眼扫视即可获取系统状态
- 使用颜色快速传达严重程度
- 数值大小和粗体突出显示

### 2. Trends Section (趋势分析)

位置: Metrics 下方,支持时间范围切换 (7d/30d/90d)

**组成:**
- **Findings Trend**: 发现数量趋势
  - 当前值 vs 前一周期平均值
  - 趋势方向 (↑/↓/→) 和变化百分比
  - Sparkline 迷你图 (7 个数据点)
- **Blocked Decisions Trend**: 阻止率趋势
  - 同上结构,显示决策阻止率变化
- **Guardian Coverage Trend**: 覆盖率趋势
  - 同上结构,显示 Guardian 覆盖率变化

**Sparkline 设计:**
- 小型折线图,显示最近 7/30/90 天趋势
- 只显示形状不显示刻度,强调趋势方向
- 颜色根据趋势方向变化 (绿色↓好,红色↑差)

**设计意图:**
- 快速识别问题是否在恶化
- 趋势比单一数值更有决策价值
- 可切换时间范围进行深入分析

### 3. Top Risks Section (高优先级风险)

位置: Dashboard 中部,突出显示

**组成:**
- 显示最高优先级的 5 个风险
- 每个风险条目包含:
  - **Severity Badge**: 严重程度徽章 (CRITICAL/HIGH/MEDIUM)
  - **Title**: 风险标题 (简洁描述)
  - **Affected Tasks**: 影响的任务数量
  - **Time**: 首次发现时间 (相对时间,如 "2h ago")
  - **Type**: 风险类型代码 (如 `blocked_reason_spike`)

**风险评分算法:**
```python
score = severity_weight * time_weight + affected_tasks * 0.5

severity_weights = {
    "CRITICAL": 10,
    "HIGH": 5,
    "MEDIUM": 2,
    "LOW": 1
}

time_weight = 1.5 if hours_ago < 24 else 1.0
```

**设计意图:**
- 管理层无需查看所有 findings,只需关注 Top 5
- 评分算法确保最紧急问题排在前面
- 时间权重确保新发现的问题被优先处理

### 4. Health Section (治理系统健康度)

位置: Dashboard 底部

**组成:**
- **Guardian Coverage**: Guardian 验收覆盖率
  - 百分比 + 进度条
  - 目标: > 80%,低于 50% 显示警告
- **Avg Decision Latency**: 平均决策延迟
  - 毫秒显示,颜色编码 (<500ms 绿,<1500ms 黄,>1500ms 红)
  - 计算: `supervisor_processed_at - source_event_ts`
- **Tasks with Audits**: 有审计记录的任务比例
  - 百分比显示,目标 > 95%
- **Active Guardians**: 活跃的 Guardian 数量
  - 整数显示,至少 2-3 个
- **Last Scan**: 最近一次 Lead 扫描时间
  - 时间戳,应该是最近几小时内

**设计意图:**
- 评估治理系统本身是否健康运行
- 识别治理系统的配置问题 (如覆盖率过低)
- 监控性能指标 (如决策延迟过高)

## 数据源

Dashboard 不创建新表,而是聚合现有数据:

| 数据源 | 用途 | 关键字段 |
|--------|------|----------|
| `lead_findings` | 风险发现 | severity, linked_task_id, last_seen_at |
| `task_audits` | 决策审计 | event_type, decision_id, source_event_ts |
| `guardian_reviews` | Guardian 验收 | target_id, target_type, guardian_id |
| `tasks` | 任务元数据 | task_id, created_at, status |

**数据过滤:**
- 所有查询都按 `timeframe` 过滤 (7d/30d/90d)
- 可选按 `project_id` 过滤 (多项目场景)
- 使用索引字段 (`created_at`, `last_seen_at`) 确保性能

## 性能特性

### 响应时间

- **目标**: < 1s
- **实测**: ~0.5s (100+ 记录, 无缓存)
- **缓存命中**: < 0.001s

### 缓存机制

- **策略**: LRU cache, 5 分钟 TTL
- **缓存键**: `(timeframe, project_id, cache_key)`
- **缓存大小**: 32 个条目
- **实现**: Python `functools.lru_cache`

**缓存设计:**
```python
def get_cache_key() -> int:
    """返回基于当前时间的缓存键 (5 分钟粒度)"""
    now = datetime.now(timezone.utc)
    return int(now.timestamp() / 300)  # 每 5 分钟递增

@lru_cache(maxsize=32)
def get_cached_dashboard(timeframe, project_id, cache_key):
    """缓存的 dashboard 数据获取"""
    return _compute_dashboard(timeframe, project_id)
```

### 查询优化

- 所有时间过滤使用索引字段
- 单次请求并发查询多个数据源
- 聚合在内存中完成 (不使用复杂 SQL JOIN)

## 优雅降级

Dashboard 设计为在部分数据缺失时仍能提供有意义的结果:

### 场景 1: findings 表为空
- `risk_level`: 返回 `"LOW"` (无风险)
- `open_findings`: 返回 `0`
- `top_risks`: 返回 `[]` (空数组)

### 场景 2: guardian_reviews 表为空
- `guarded_percentage`: 返回 `0.0`
- `active_guardians`: 返回 `0`
- UI 显示警告: "Guardian verification not configured"

### 场景 3: task_audits 表为空
- `blocked_rate`: 返回 `0.0`
- `avg_decision_latency_ms`: 返回 `0`
- UI 显示警告: "Decision audit not available"

### 场景 4: 完全无数据
- 返回有效 JSON 结构,所有数值为 0 或空
- `risk_level`: `"UNKNOWN"`
- HTTP 200 (不是 500),允许前端显示空态

**实现方式:**
```python
def safe_aggregate(func, fallback_value, *args, **kwargs):
    """安全执行聚合函数,失败时返回降级值"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Aggregation failed: {func.__name__}, fallback: {e}")
        return fallback_value
```

## 技术栈

### 后端
- **框架**: FastAPI
- **数据库**: SQLite (with indexes)
- **聚合**: Python aggregation functions
- **缓存**: `functools.lru_cache`

### 前端
- **语言**: ES6+ JavaScript (无框架依赖)
- **布局**: CSS Grid + Flexbox
- **组件**:
  - RiskBadge (Task #7)
  - MetricCard (Task #7)
  - TrendSparkline (Task #7)
  - HealthIndicator (Task #7)
- **路由**: Hash-based SPA routing

### API 设计
- **端点**: `GET /api/governance/dashboard`
- **参数**: `?timeframe=7d&project_id=xxx` (可选)
- **响应**: JSON (见 API 文档)

## 使用场景

### 场景 1: 每日站会
**角色**: CTO
**用例**: 快速查看系统治理状态

1. 打开 Dashboard (7d 视图)
2. 查看 Risk Level → 如果是 HIGH/CRITICAL,询问团队
3. 查看 Trends → 确认问题是否在改善
4. 查看 Top Risks → 确认最严重问题有人负责

**时间**: 30 秒

### 场景 2: 审计准备
**角色**: 合规官
**用例**: 为外部审计准备治理报告

1. 切换到 90d 视图
2. 截图 Dashboard 主视图
3. 导出 Top Risks 列表 (未来功能)
4. 查看 Guardian Coverage 和 Audits 比例

**时间**: 5 分钟

### 场景 3: 事故响应
**角色**: SRE
**用例**: 系统出现大量阻止决策,需快速定位

1. 打开 Dashboard
2. 查看 Blocked Rate Trend → 确认异常峰值
3. 查看 Top Risks → 识别根因 (如 `blocked_reason_spike`)
4. 点击风险链接 (未来功能) → 进入详细分析页面

**时间**: 1 分钟

### 场景 4: 系统健康检查
**角色**: DevOps
**用例**: 定期检查治理系统是否正常工作

1. 查看 Health Section
2. 确认 Guardian Coverage > 80%
3. 确认 Avg Decision Latency < 2s
4. 确认 Last Scan 在最近几小时内

**时间**: 30 秒

## 未来增强

### Phase 2 (计划中)
- [ ] PDF 导出功能 (用于审计报告)
- [ ] 邮件摘要 (每日/每周发送给管理层)
- [ ] 自定义告警阈值 (如 Blocked Rate > 15% 时通知)
- [ ] 点击 Top Risk 进入详细页面
- [ ] 历史对比功能 (Week-over-Week)

### Phase 3 (未来规划)
- [ ] 多项目对比视图
- [ ] 自定义 Dashboard 布局
- [ ] 嵌入式图表 (用于外部展示)
- [ ] 实时 WebSocket 更新 (当前是轮询)

## 相关文档

- [Governance Dashboard API 文档](./dashboard_api.md) - API 端点详细规范
- [Dashboard 使用指南 (高管版)](./dashboard_for_executives.md) - 非技术人员指南
- [Lead Agent 文档](./lead_agent.md) - 风险发现来源
- [Guardian 验收文档](./guardian_workflow.md) - 验收覆盖率来源
- [Supervisor 文档](./supervisor.md) - 决策审计来源

## 版本历史

### v1.0.0 (2026-01-29)
- ✅ 初始实现
- ✅ 支持 7d/30d/90d 时间范围
- ✅ 4 个核心区域 (Metrics/Trends/Risks/Health)
- ✅ 5 分钟服务端缓存
- ✅ 优雅降级机制
- ✅ 响应式设计 (1400px → 480px)
- ✅ 完整测试覆盖 (单元 + 集成 + E2E)
