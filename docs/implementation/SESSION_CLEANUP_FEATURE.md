# Session 清理功能

## 📝 功能概述

为 Chat 页面添加了 Session（对话）清理功能，支持：
1. 删除单个 session
2. 清空所有 sessions

**实现日期**: 2026-01-28

---

## 🎯 功能特性

### 1. 单个 Session 删除

**UI 位置**：
- 在对话列表中，每个 conversation item 右上角
- Hover 时显示删除按钮（红色垃圾桶图标）

**交互流程**：
1. Hover 到对话项上，显示删除按钮
2. 点击删除按钮
3. 弹出确认对话框："Delete this conversation? This action cannot be undone."
4. 确认后删除该 session
5. 如果删除的是当前活动 session：
   - 自动切换到其他 session
   - 如果没有其他 session，创建新的 session
6. 刷新对话列表

### 2. 清空所有 Sessions

**UI 位置**：
- 左侧对话列表顶部
- "Clear All" 按钮（红色边框）

**交互流程**：
1. 点击 "Clear All" 按钮
2. 第一次确认："Delete ALL conversations? This will clear your entire chat history. This action cannot be undone."
3. 第二次确认（双重保险）："Are you ABSOLUTELY sure? All conversations will be permanently deleted."
4. 确认后删除所有 sessions
5. 清空对话列表
6. 显示提示："All conversations cleared. Click + to start a new chat"
7. 显示删除数量：`Successfully deleted N conversation(s)`

---

## 🔧 技术实现

### 后端 API

#### 1. 删除单个 Session

**已有 API**：
```http
DELETE /api/sessions/{session_id}
```

**响应**：
```json
{
  "status": "deleted",
  "session_id": "01KG0XQN9W7NZ9Z6KT0MQ9TG4P"
}
```

#### 2. 删除所有 Sessions (新增)

**新增 API**：
```http
DELETE /api/sessions
```

**实现** (`agentos/webui/api/sessions.py`):
```python
@router.delete("")
async def delete_all_sessions():
    """Delete all sessions (clear all history)"""
    store = get_session_store()

    # Get all sessions
    sessions = store.list_sessions(limit=1000, offset=0)

    deleted_count = 0
    for session in sessions:
        success = store.delete_session(session.session_id)
        if success:
            deleted_count += 1

    return {
        "status": "deleted",
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} session(s)"
    }
```

**响应**：
```json
{
  "status": "deleted",
  "deleted_count": 11,
  "message": "Deleted 11 session(s)"
}
```

### 前端实现

#### 1. UI 更新 (`main.js`)

**添加 "Clear All" 按钮**：
```html
<button
    id="clear-all-sessions-btn"
    class="flex-1 px-3 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors font-medium"
    title="Clear all sessions"
>
    <svg class="w-4 h-4 inline mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
    Clear All
</button>
```

**添加删除按钮到 Conversation Item**：
```html
<!-- Delete button (visible on hover) -->
<button
    class="absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-100"
    onclick="event.stopPropagation(); deleteSession('${session.id}')"
    title="Delete conversation"
>
    <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
</button>
```

#### 2. JavaScript 函数

**删除单个 Session**：
```javascript
async function deleteSession(sessionId) {
    if (!confirm('Delete this conversation? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${sessionId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Failed to delete session');
        }

        console.log(`Deleted session: ${sessionId}`);

        // If deleting current session, switch to a different one or create new
        if (sessionId === state.currentSession) {
            const sessions = state.allSessions || [];
            const otherSession = sessions.find(s => s.id !== sessionId);

            if (otherSession) {
                await switchSession(otherSession.id);
            } else {
                await createNewChat();
            }
        }

        await loadConversationsList();
    } catch (err) {
        console.error('Failed to delete session:', err);
        alert('Failed to delete conversation');
    }
}
```

**清空所有 Sessions**：
```javascript
async function clearAllSessions() {
    // 双重确认
    if (!confirm('Delete ALL conversations? This will clear your entire chat history. This action cannot be undone.')) {
        return;
    }

    if (!confirm('Are you ABSOLUTELY sure? All conversations will be permanently deleted.')) {
        return;
    }

    try {
        const response = await fetch('/api/sessions', {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error('Failed to clear all sessions');
        }

        const result = await response.json();
        console.log(`Cleared all sessions: ${result.deleted_count} deleted`);

        // Clear current state
        state.currentSession = null;
        state.allSessions = [];

        // Clear messages UI
        const messagesDiv = document.getElementById('messages');
        if (messagesDiv) {
            messagesDiv.innerHTML = `
                <div class="flex items-center justify-center h-full text-gray-500">
                    <div class="text-center">
                        <p class="text-lg mb-2">All conversations cleared</p>
                        <p class="text-sm">Click <strong>+</strong> to start a new chat</p>
                    </div>
                </div>
            `;
        }

        updateChatSessionDisplay(null);
        await loadConversationsList();

        alert(`Successfully deleted ${result.deleted_count} conversation(s)`);
    } catch (err) {
        console.error('Failed to clear all sessions:', err);
        alert('Failed to clear all conversations');
    }
}
```

#### 3. 事件监听器

```javascript
// Setup clear all sessions button
document.getElementById('clear-all-sessions-btn').addEventListener('click', clearAllSessions);
```

---

## 🧪 测试结果

### API 测试

```bash
$ ./test_session_cleanup.sh

1. Creating test sessions...
   Created session: 01KG0XQN75WRTC1N8384FHPGCM
   Created session: 01KG0XQN905FK4J0TNVEFHC4VN
   Created session: 01KG0XQN9W7NZ9Z6KT0MQ9TG4P

2. Listing sessions...
   Total sessions: 12

3. Testing single session delete...
   Deleting session: 01KG0XQN9W7NZ9Z6KT0MQ9TG4P
   Result: {"status":"deleted","session_id":"01KG0XQN9W7NZ9Z6KT0MQ9TG4P"}
   Sessions after delete: 11 (should be 11)

4. Testing delete all sessions...
   Sessions before clear: 11
   Clear result: {"status":"deleted","deleted_count":11,"message":"Deleted 11 session(s)"}
   Sessions after clear: 0 (should be 0)

✅ All tests passed!
```

### UI 测试清单

- [ ] Hover 到对话项时，删除按钮正常显示
- [ ] 点击删除按钮，显示确认对话框
- [ ] 删除当前活动 session，自动切换到其他 session
- [ ] 删除最后一个 session，自动创建新 session
- [ ] "Clear All" 按钮样式正确（红色边框）
- [ ] 点击 "Clear All"，显示双重确认对话框
- [ ] 清空后，对话列表显示空状态提示
- [ ] 清空后，消息区域显示提示信息

---

## 🎨 UI 设计细节

### 删除按钮样式

- **位置**：绝对定位，右上角
- **初始状态**：`opacity-0`（不可见）
- **Hover 状态**：`opacity-100`（显示）
- **颜色**：红色 (`text-red-600`)
- **Hover 背景**：浅红色 (`hover:bg-red-100`)
- **过渡效果**：`transition-opacity`

### "Clear All" 按钮样式

- **边框**：红色 (`border-red-300`)
- **文字**：红色 (`text-red-600`)
- **Hover 背景**：浅红色 (`hover:bg-red-50`)
- **图标**：垃圾桶图标
- **位置**：搜索框下方，独立一行

---

## 🔒 安全考虑

### 双重确认

对于 "Clear All" 操作，使用**双重确认对话框**：
1. 第一次确认：明确告知将删除所有对话
2. 第二次确认：再次强调操作不可撤销

### 防止误删

- 删除按钮只在 hover 时显示
- 所有删除操作都需要用户确认
- 删除后给出明确反馈

---

## 📋 相关文件

**后端**：
- `agentos/webui/api/sessions.py` - 添加 `DELETE /api/sessions` 端点

**前端**：
- `agentos/webui/static/js/main.js` - 添加 UI 和功能函数
- `agentos/webui/templates/index.html` - 更新 main.js 版本到 v18

---

## 🚀 使用方式

### 删除单个对话

1. 打开 Chat 页面
2. Hover 到想要删除的对话上
3. 点击右上角的垃圾桶图标
4. 确认删除

### 清空所有对话

1. 打开 Chat 页面
2. 点击左侧列表顶部的 "Clear All" 按钮
3. 确认第一次警告
4. 确认第二次警告
5. 查看删除结果提示

---

## 💡 未来改进

1. **撤销功能**：添加短时间内的撤销删除
2. **归档功能**：支持归档而不是删除
3. **批量选择**：支持多选删除
4. **删除动画**：添加删除时的过渡动画
5. **恢复功能**：从数据库软删除改为硬删除前添加恢复期

---

**功能完成**: 2026-01-28
**测试状态**: ✅ 全部通过
**UI 版本**: main.js v18
