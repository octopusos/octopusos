# 操作历史页面（History View）

## 🎯 功能说明

操作历史页面用于查看和管理 AgentOS 的命令执行历史记录，提供完整的操作追溯能力。

---

## 📋 已实现的功能

### 1. **历史记录列表**
- ✅ 显示所有命令执行历史
- ✅ 包含：时间、命令ID、状态、执行时长、结果摘要
- ✅ 支持分页（每页 50 条）
- ✅ 支持点击行查看详情

### 2. **过滤功能**
- ✅ 按命令ID过滤（如 `kb:search`）
- ✅ 按状态过滤（Success / Failure / Running）
- ✅ 按 Session ID 过滤
- ✅ 默认显示最近 100 条记录

### 3. **Pin/Unpin 功能**
- ✅ 可以将重要的命令固定（Pin）
- ✅ 查看所有已固定的命令（Pinned 按钮）
- ✅ 取消固定（Unpin）
- ✅ 固定的命令在列表中有 📌 图标标识

### 4. **详情视图**
- ✅ 显示完整的命令信息
- ✅ 显示命令参数（JSON 格式）
- ✅ 显示执行结果或错误信息
- ✅ 关联的 Session ID 和 Task ID（可点击跳转）
- ✅ 复制命令 ID 功能

### 5. **跨页跳转**
- ✅ 从 History 跳转到 Session（Chat 页面）
- ✅ 从 History 跳转到 Task（Tasks 页面）

---

## 📁 文件清单

### 新增文件

1. **API 层**
   - `agentos/webui/api/history.py` - History API endpoint
     - GET `/api/history` - 查询历史记录
     - GET `/api/history/pinned` - 获取固定的命令
     - GET `/api/history/{id}` - 获取单条记录
     - POST `/api/history/{id}/pin` - 固定命令
     - DELETE `/api/history/{id}/pin` - 取消固定

2. **前端 View**
   - `agentos/webui/static/js/views/HistoryView.js` - 历史视图组件
     - 使用 DataTable 和 FilterBar 组件
     - 实现详情 Drawer
     - 实现 Pin/Unpin 功能

### 修改文件

3. **后端集成**
   - `agentos/webui/app.py` - 注册 history router
   - `agentos/webui/api/__init__.py` - 导出 history module

4. **前端集成**
   - `agentos/webui/templates/index.html` - 添加导航菜单和脚本标签
   - `agentos/webui/static/js/main.js` - 添加 renderHistoryView 函数

---

## 🔧 技术实现

### 后端架构

```python
# 使用现有的 CommandHistoryService
from agentos.core.command.history import CommandHistoryService

service = CommandHistoryService()
entries = service.list(
    command_id=None,
    status=None,
    task_id=None,
    limit=100
)
```

### 数据模型

```typescript
interface HistoryEntry {
    id: string;                    // hist_xxx
    command_id: string;            // e.g., "kb:search"
    args: Record<string, any>;     // 命令参数
    executed_at: string;           // ISO 8601 timestamp
    duration_ms: number | null;    // 执行时长（毫秒）
    status: 'success' | 'failure' | 'running';
    result_summary: string | null; // 结果摘要
    error: string | null;          // 错误信息
    task_id: string | null;        // 关联的 Task ID
    session_id: string | null;     // 关联的 Session ID
    is_pinned: boolean;            // 是否固定
}
```

### 前端组件

```javascript
class HistoryView {
    constructor(container)
    loadHistory()          // 加载历史记录
    loadPinned()          // 加载固定的命令
    showHistoryDetail()   // 显示详情
    pinCommand()          // 固定命令
    unpinCommand()        // 取消固定
}
```

---

## 🎨 UI 特性

### 1. 状态 Badge
- **Success** - 绿色 ✅
- **Failed** - 红色 ❌
- **Running** - 蓝色 🔄

### 2. Pin 图标
- 固定的命令显示黄色 📌 图标
- 在详情页可以 Pin/Unpin

### 3. Filter Bar
- 文本输入：Command ID、Session ID
- 下拉选择：Status（All / Success / Failure / Running）

### 4. Drawer（侧边栏详情）
- 基本信息（ID、命令、状态、时间）
- 参数（JSON Viewer）
- 结果摘要或错误信息
- 操作按钮（Pin/Unpin、Copy、跳转）

---

## 🧪 测试方法

### 1. 启动 WebUI

```bash
agentos webui start
```

### 2. 访问 History 页面

- 点击左侧导航栏的 **History** 链接
- 或访问：`http://localhost:8000/#history`

### 3. 测试功能

#### 查看历史记录
1. 页面加载后自动显示最近的 100 条历史
2. 表格显示：时间、命令ID、状态、时长、结果

#### 过滤功能
1. 在 Filter Bar 中输入命令ID（如 `kb:search`）
2. 选择状态（Success / Failure）
3. 点击 Apply

#### 查看详情
1. 点击任意一行
2. 右侧 Drawer 打开，显示完整信息
3. 如果有参数，会显示 JSON Viewer

#### Pin/Unpin
1. 在详情页点击 **Pin** 按钮
2. 命令被标记为固定（📌 图标）
3. 点击顶部的 **Pinned** 按钮查看所有固定的命令
4. 再次点击 **Unpin** 取消固定

#### 跨页跳转
1. 如果历史记录关联了 Session ID
   - 点击 **View Session** 跳转到 Chat 页面
2. 如果关联了 Task ID
   - 点击 **View Task** 跳转到 Tasks 页面

---

## 📊 API 端点测试

### 查询历史记录

```bash
curl http://localhost:8000/api/history?limit=10
```

### 查询固定的命令

```bash
curl http://localhost:8000/api/history/pinned
```

### 固定一个命令

```bash
curl -X POST http://localhost:8000/api/history/{history_id}/pin \
  -H "Content-Type: application/json" \
  -d '{"note": "重要操作"}'
```

### 取消固定

```bash
curl -X DELETE http://localhost:8000/api/history/{history_id}/pin
```

---

## 🔍 常见问题

### Q: 为什么没有看到历史记录？

A: 命令历史需要通过 CommandHistoryService 记录。确保：
1. 数据库 migration 已执行（`v14_command_history.sql`）
2. 命令执行时调用了 `service.record()` 方法

### Q: 如何清空历史记录？

A: 通过 CommandHistoryService 的 `clear()` 方法：

```python
from agentos.core.command.history import CommandHistoryService
service = CommandHistoryService()
service.clear(older_than_days=30)  # 清空 30 天前的记录
```

### Q: Pin 功能有什么用？

A: Pin 功能用于标记重要的命令，方便快速查找和回顾。适用场景：
- 关键操作的记录
- 需要重复执行的命令
- 调试时的重要线索

---

## 🚀 后续优化建议

### 短期（已实现）
- ✅ 基本列表和过滤
- ✅ 详情查看
- ✅ Pin/Unpin 功能
- ✅ 跨页跳转

### 中期（可选）
- ⏳ 搜索功能（支持模糊搜索结果摘要）
- ⏳ 导出功能（导出为 JSON 或 CSV）
- ⏳ 统计图表（按命令类型、成功率等）
- ⏳ 命令重放（Replay）功能

### 长期（可选）
- ⏳ 历史记录分组（按 Session、Task、时间范围）
- ⏳ 高级过滤（时间范围、执行时长）
- ⏳ 历史记录对比（Compare 两次执行的差异）
- ⏳ 收藏夹（Favorites）功能

---

## ✅ 验收清单

### 功能验收
- [ ] 历史记录列表正常显示
- [ ] 过滤功能工作正常
- [ ] Refresh 按钮刷新数据
- [ ] Pinned 按钮显示固定的命令
- [ ] 点击行打开详情 Drawer
- [ ] Pin/Unpin 功能正常
- [ ] 跨页跳转（Session、Task）正常

### 视觉验收
- [ ] 和其他 Observability 页面风格一致
- [ ] Status Badge 颜色正确
- [ ] Pin 图标显示正常
- [ ] Drawer 样式统一

### 性能验收
- [ ] 100 条记录加载时间 < 1秒
- [ ] 过滤响应快速
- [ ] 无 Console 错误

---

**实现完成时间**: 2026-01-28
**页面位置**: 导航栏 → Observability → History
**测试状态**: ✅ 待验收
