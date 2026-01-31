# BrainOS WebUI 快速入门

**版本**: v0.1 (P0 实现)
**日期**: 2026-01-30

---

## 快速访问

### 启动 WebUI
```bash
agentos webui
```

### 访问地址
- Dashboard: http://localhost:8000/#/brain-dashboard
- Query Console: http://localhost:8000/#/brain-query

### 导航入口
左侧导航栏 → Knowledge → BrainOS

---

## Dashboard 快速查看

### 6 个核心指标

1. **Graph Status** - 图状态
   - Version, Commit, Built time, Duration

2. **Data Scale** - 数据规模
   - Entities, Edges, Evidence, Density

3. **Input Coverage** - 输入覆盖
   - Git ✅/❌, Doc ✅/❌, Code ✅/❌

4. **Cognitive Coverage** - 认知覆盖
   - Doc Refs %, Dep Graph %

5. **Blind Spots** - 盲区
   - Top 3 knowledge gaps

6. **Actions** - 快速操作
   - Rebuild Index, Query Console, Golden Queries

---

## Query Console 快速查询

### Why Query - 追溯起源
**示例**:
```
file:agentos/core/task/manager.py
capability:retry_with_backoff
term:ExecutionBoundary
doc:ADR_TASK_STATE_MACHINE.md
```

**输出**: 路径列表 + 证据

### Impact Query - 影响分析
**示例**:
```
file:agentos/core/task/models.py
doc:ADR_TASK_STATE_MACHINE.md
```

**输出**: 受影响节点 + 风险提示

### Trace Query - 演进追踪
**示例**:
```
file:agentos/core/executor/executor_engine.py
capability:pipeline_runner
```

**输出**: 时间线 + 事件

### Map Query - 子图提取
**示例**:
```
file:agentos/core/brain/service/query_why.py
term:BrainOS
```

**输出**: 节点 + 边

---

## API 快速测试

### 获取统计信息
```bash
curl http://localhost:8000/api/brain/stats | jq .
```

### Why 查询
```bash
curl -X POST http://localhost:8000/api/brain/query/why \
  -H "Content-Type: application/json" \
  -d '{"seed": "file:agentos/core/task/manager.py"}' | jq .
```

### Impact 查询
```bash
curl -X POST http://localhost:8000/api/brain/query/impact \
  -H "Content-Type: application/json" \
  -d '{"seed": "file:agentos/core/task/models.py", "depth": 1}' | jq .
```

### Trace 查询
```bash
curl -X POST http://localhost:8000/api/brain/query/trace \
  -H "Content-Type: application/json" \
  -d '{"seed": "file:agentos/core/executor/executor_engine.py"}' | jq .
```

### Subgraph 查询
```bash
curl -X POST http://localhost:8000/api/brain/query/subgraph \
  -H "Content-Type: application/json" \
  -d '{"seed": "term:BrainOS", "k_hop": 1}' | jq .
```

---

## 常见问题

### Q: Dashboard 显示 "No index built yet"？
**A**: 运行 BrainIndexJob 构建索引
```bash
python -c "
from agentos.core.brain.service import BrainIndexJob
result = BrainIndexJob.run(repo_path='.', db_path='.brainos/v0.1_mvp.db')
print(f'Build complete: {result.manifest.graph_version}')
"
```

或在 Dashboard 点击 "Build Index Now" 按钮。

### Q: Query 返回 404 "BrainOS index not found"？
**A**: 同上，需要先构建索引。

### Q: 如何指定数据库路径？
**A**: 设置环境变量 `BRAINOS_DB_PATH`
```bash
export BRAINOS_DB_PATH=/path/to/custom.db
agentos webui
```

### Q: Query 结果为空？
**A**: 检查：
1. 索引是否包含该实体（查看 Dashboard 的 Entities count）
2. 实体 key 格式是否正确（`file:`, `doc:`, `term:`, `capability:`）
3. 查看 Console 输出是否有错误

---

## 文件位置

### Backend
- API: `agentos/webui/api/brain.py`
- Tests: `tests/unit/webui/api/test_brain_api.py`

### Frontend
- Dashboard: `agentos/webui/static/js/views/BrainDashboardView.js`
- Query Console: `agentos/webui/static/js/views/BrainQueryConsoleView.js`
- Styles: `agentos/webui/static/css/brain.css`

### BrainOS Core
- Services: `agentos/core/brain/service/`
- Database: `.brainos/v0.1_mvp.db`

---

## 下一步

### P1 功能（即将推出）
- ✨ Explain 按钮（Tasks/Extensions/Context 页面）
- 📊 Coverage 计算（真实指标）
- 🔍 Blind Spots 检测（自动发现盲区）
- 🔤 Autocomplete（查询输入自动补全）

### P2 功能（规划中）
- ⭐ Golden Queries 预置列表
- 📈 子图可视化（图形化展示）
- 🔧 高级过滤和排序

---

## 技术支持

- 文档: `PR_WEBUI_BRAINOS_1_IMPLEMENTATION_REPORT.md`
- Issues: 提交到项目 Issue Tracker
- 反馈: 在 Dashboard 点击 "Support" 按钮

---

**快速开始 → 访问 http://localhost:8000/#/brain-dashboard** 🚀
