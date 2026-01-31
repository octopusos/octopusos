# Knowledge Health 优化报告

## 问题描述

Knowledge Health 页面存在以下问题：
1. 数据不准确：Total Chunks 和 Total Files 显示为 0
2. 缺少操作按钮：
   - "Needs refresh" 状态旁边需要快速刷新按钮
   - "Poor" coverage 状态旁边需要改善按钮
3. 后端 API 无法创建索引任务（外键约束错误）

## 根本原因

### 1. 数据不准确问题

**原因**：后端 API (`agentos/webui/api/knowledge.py`) 使用了不存在的方法：
- `kb_service.get_total_chunks()` - 不存在
- `kb_service.get_total_files()` - 不存在
- `kb_service.get_last_index_time()` - 不存在

**正确方法**：
- 使用 `kb_service.stats()` 获取统计信息
- 使用 `kb_service.indexer.get_existing_sources()` 获取文件数量

### 2. 外键约束错误

**原因**：`TaskManager.create_task()` 方法在自动生成 session_id 时，没有在 `task_sessions` 表中创建对应的记录，导致外键约束失败。

**影响**：无法创建后台索引任务。

## 解决方案

### 1. 修复后端数据获取 (`agentos/webui/api/knowledge.py`)

```python
# 修复前 (错误)
total_chunks = kb_service.get_total_chunks() if hasattr(kb_service, 'get_total_chunks') else 0
total_files = kb_service.get_total_files() if hasattr(kb_service, 'get_total_files') else 0

# 修复后 (正确)
stats = kb_service.stats()
total_chunks = stats.get("total_chunks", 0)
existing_sources = kb_service.indexer.get_existing_sources(kb_service.scanner.repo_id)
total_files = len(existing_sources)
```

### 2. 修复 TaskManager 外键约束 (`agentos/core/task/manager.py`)

在自动生成 session_id 时，同时创建对应的 session 记录：

```python
# 修复前
if not session_id:
    session_id = f"auto_{task_id[:8]}_{timestamp}"

# 修复后
auto_created_session = False
if not session_id:
    session_id = f"auto_{task_id[:8]}_{timestamp}"
    auto_created_session = True

# ... 在插入 task 前 ...

if auto_created_session:
    cursor.execute(
        """
        INSERT OR IGNORE INTO task_sessions (session_id, channel, metadata, created_at, last_activity)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, "auto", json.dumps({"auto_created": True, "task_id": task_id}), now, now)
    )
```

### 3. 前端添加操作按钮 (`agentos/webui/static/js/views/KnowledgeHealthView.js`)

#### 3.1 在 "Needs refresh" 旁边添加刷新按钮

```javascript
if (metrics.index_lag_seconds >= 3600) {
    lagStatus.textContent = 'Needs refresh';
    lagStatus.className = 'metric-status warn';
    // 添加刷新按钮
    this.addActionButton(indexLagCard, 'refresh', 'Refresh index', () => this.triggerRefresh());
}
```

#### 3.2 在 "Poor" 旁边添加重建按钮

```javascript
if (metrics.file_coverage <= 0.70) {
    coverageStatus.textContent = 'Poor';
    coverageStatus.className = 'metric-status error';
    // 添加重建按钮
    this.addActionButton(coverageCard, 'build', 'Rebuild index', () => this.triggerRebuild());
}
```

#### 3.3 添加操作按钮方法

```javascript
addActionButton(card, icon, tooltip, onClick) {
    const actionBtn = document.createElement('button');
    actionBtn.className = 'metric-action-btn';
    actionBtn.title = tooltip;
    actionBtn.innerHTML = `<span class="material-icons md-18">${icon}</span>`;
    actionBtn.addEventListener('click', onClick);

    const statusEl = card.querySelector('.metric-status');
    if (statusEl) {
        statusEl.parentNode.insertBefore(actionBtn, statusEl.nextSibling);
    }
}
```

#### 3.4 实现刷新和重建方法

```javascript
async triggerRefresh() {
    if (!confirm('执行增量索引刷新？')) return;

    const response = await fetch('/api/knowledge/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'incremental' })
    });

    const data = await response.json();
    if (data.ok) {
        window.showToast('索引刷新任务已启动', 'success');
        setTimeout(() => this.loadHealthData(), 2000);
    }
}

async triggerRebuild() {
    if (!confirm('执行完整索引重建？')) return;

    const response = await fetch('/api/knowledge/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'rebuild' })
    });

    const data = await response.json();
    if (data.ok) {
        window.showToast('索引重建任务已启动', 'success');
        setTimeout(() => this.loadHealthData(), 2000);
    }
}
```

### 4. 添加 CSS 样式 (`agentos/webui/static/css/components.css`)

```css
.metric-action-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 4px;
    margin-left: 8px;
    border-radius: 4px;
    color: #6c757d;
    transition: all 0.2s;
    vertical-align: middle;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.metric-action-btn:hover {
    background: #e9ecef;
    color: #007bff;
}

.metric-action-btn:active {
    background: #dee2e6;
    transform: scale(0.95);
}
```

## 测试结果

### 修复前
```json
{
  "total_chunks": 0,
  "total_files": 0,
  "file_coverage": 0.0
}
```

触发刷新任务：`❌ FOREIGN KEY constraint failed`

### 修复后
```json
{
  "total_chunks": 635,
  "total_files": 228,
  "file_coverage": 1.0,
  "index_lag_seconds": 160065
}
```

触发刷新任务：`✅ 任务已启动: 01KG1S8YCFNZZ5Y2ZA68X8QGR3`

## 修改的文件

1. **后端修复**
   - `agentos/webui/api/knowledge.py` - 修复数据获取方法
   - `agentos/core/task/manager.py` - 修复外键约束问题

2. **前端优化**
   - `agentos/webui/static/js/views/KnowledgeHealthView.js` - 添加操作按钮
   - `agentos/webui/static/css/components.css` - 添加按钮样式

3. **测试脚本**
   - `scripts/tests/test_knowledge_health_simple.sh` - 完整测试脚本
   - `scripts/tests/test_task_creation.py` - Task 创建测试

## 用户体验改进

1. **数据准确性**：现在显示真实的索引统计数据
2. **操作便捷性**：可以直接在 Health 页面点击按钮执行刷新/重建
3. **即时反馈**：操作后显示 Toast 通知，并自动刷新数据
4. **视觉反馈**：按钮 hover 和 active 状态有清晰的视觉反馈

## 后续改进建议

1. **实时进度显示**：添加 WebSocket 或轮询来实时显示索引任务进度
2. **错误详情**：当索引失败时，显示详细的错误信息
3. **历史记录**：显示最近的索引任务历史
4. **自动刷新**：当检测到 index lag 过大时，提示用户或自动触发刷新

## 相关链接

- Issue: [待补充]
- PR: [待补充]
- 测试脚本: `scripts/tests/test_knowledge_health_simple.sh`

---

**修复时间**: 2026-01-28
**修复人**: Claude Code
**影响范围**: Knowledge Health 功能
**优先级**: High
**状态**: ✅ 已完成并测试通过
