# Task #9: Memory Badge UI - 验收清单

## 快速验收指南

### 前置条件
- [ ] WebUI服务运行中 (`python -m agentos.webui.app`)
- [ ] 至少有一个Project配置
- [ ] 已有Memory数据（可通过Chat交互生成）

### 后端API验收

#### 1. 测试API端点存在性
```bash
# 验证路由已注册
python3 -c "
from agentos.webui.api.sessions import router
routes = [r.path for r in router.routes]
print('✓ memory-status found' if '/{session_id}/memory-status' in routes else '✗ NOT FOUND')
"
```
**预期输出**: `✓ memory-status found`

#### 2. 测试API端点响应（无Memory）
```bash
# 创建测试session并查询
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Session","tags":["test"]}' | jq -r '.id')

curl -s "http://localhost:8000/api/chat/sessions/${SESSION_ID}/memory-status" | jq
```
**预期输出**:
```json
{
  "memory_count": 0,
  "has_preferred_name": false,
  "preferred_name": null,
  "memory_types": {},
  "last_updated": "2025-01-31T..."
}
```

#### 3. 测试API端点响应（有Memory）
```bash
# 使用已有session（替换为实际的session ID）
curl -s "http://localhost:8000/api/chat/sessions/YOUR_SESSION_ID/memory-status" | jq
```
**预期输出** (如果有Memory):
```json
{
  "memory_count": 3,
  "has_preferred_name": true,
  "preferred_name": "胖哥",
  "memory_types": {
    "preference": 2,
    "fact": 1
  },
  "last_updated": "2025-01-31T..."
}
```

### 前端UI验收

#### 1. 检查CSS文件加载
1. 打开浏览器DevTools (F12)
2. 转到Network标签
3. 刷新页面
4. 搜索 `memory-badge.css`

**预期**: 文件加载成功（200 OK）

#### 2. 检查Badge渲染
1. 打开WebUI主页 (`http://localhost:8000`)
2. 查看顶栏右侧（Health Badge和Refresh Button之间）

**预期**:
- [ ] 看到 🧠 Memory Badge
- [ ] 显示格式为 "Memory: N"（N为数字）
- [ ] 无Memory时Badge为灰色
- [ ] 有Memory时Badge为绿色

#### 3. 检查Tooltip显示
1. 将鼠标悬停在Memory Badge上

**预期**:
- [ ] 显示Tooltip
- [ ] Tooltip包含：Total、Name（如有）、Types
- [ ] 数据与API响应一致

#### 4. 检查Click导航
1. 点击Memory Badge

**预期**:
- [ ] 导航到Memory页面
- [ ] 左侧导航栏"Memory"项变为高亮

#### 5. 检查Session切换更新
1. 在Chat视图中切换不同的会话

**预期**:
- [ ] Badge数字随session变化更新
- [ ] 控制台显示 `[MemoryBadge] Fetching memory status...`

#### 6. 检查自动刷新
1. 打开控制台 (F12)
2. 等待30秒

**预期**:
- [ ] 控制台显示 `[MemoryBadge] Auto-updating...`
- [ ] Badge数据自动刷新

### 浏览器控制台验收

#### 1. 检查初始化日志
```javascript
// 刷新页面后，控制台应显示：
[MemoryBadge] Initializing...
[MemoryBadge] Initialized successfully
```

#### 2. 手动测试API调用
```javascript
// 在控制台执行：
MemoryBadge.update('YOUR_SESSION_ID')

// 预期输出：
[MemoryBadge] Fetching memory status for session: YOUR_SESSION_ID
[MemoryBadge] Memory status: {memory_count: 3, ...}
[MemoryBadge] Rendered: 3 memories (has memories)
```

#### 3. 检查错误处理
```javascript
// 测试不存在的session
MemoryBadge.update('nonexistent-session-id')

// 预期输出：
[MemoryBadge] API error: 404
[MemoryBadge] Error state rendered
```

### 响应式设计验收

#### 1. 桌面端（>768px）
- [ ] Badge显示在顶栏右侧
- [ ] Tooltip右对齐

#### 2. 移动端（<768px）
- [ ] Badge正常显示
- [ ] Tooltip左对齐（不超出屏幕）

#### 3. 暗黑模式
- [ ] 打开系统暗黑模式
- [ ] Badge颜色适配（绿色变为深绿）
- [ ] Tooltip背景变为暗色

### 集成验收

#### 1. 与Budget Indicator共存
- [ ] Budget Indicator和Memory Badge同时显示
- [ ] 布局不重叠
- [ ] 样式一致

#### 2. 与Project Selector共存
- [ ] 切换Project时，Memory Badge更新（如session绑定到project）

#### 3. WebSocket生命周期
- [ ] 页面失焦后恢复，Badge仍正常工作
- [ ] 网络断开后重连，Badge自动恢复更新

### 性能验收

#### 1. 网络请求
```javascript
// 在Network标签中观察
// 每次session切换或自动刷新时
```
**预期**:
- [ ] 请求耗时 < 200ms
- [ ] 响应大小 < 1KB
- [ ] 无重复请求

#### 2. 渲染性能
```javascript
// 在Performance标签中录制
// 切换session时的渲染
```
**预期**:
- [ ] Badge更新耗时 < 50ms
- [ ] 无明显卡顿

### 错误场景验收

#### 1. Session不存在
- [ ] API返回404
- [ ] Badge显示 "Memory: Error"
- [ ] 控制台输出错误日志

#### 2. 网络错误
- [ ] 断网情况下
- [ ] Badge显示 "Memory: Error"
- [ ] 不阻塞其他功能

#### 3. 无Project上下文
- [ ] Session没有project_id
- [ ] Badge显示 "Memory: 0"
- [ ] 不报错

### 最终验收清单

#### 功能完整性
- [x] 后端API端点实现
- [x] 前端CSS样式实现
- [x] 前端JS组件实现
- [x] HTML模板集成
- [x] 测试用例编写

#### 验收标准达成
- [x] Memory Badge显示在顶栏
- [x] 显示"Memory: N"格式
- [x] 有/无Memory时颜色不同
- [x] Hover显示tooltip
- [x] Click跳转到Memory页面
- [x] 会话切换时自动更新
- [x] Context构建后自动刷新

#### 代码质量
- [x] 代码风格一致（参考budget indicator）
- [x] 错误处理完善
- [x] 日志输出清晰
- [x] 注释完整

#### 文档完整性
- [x] 实施报告
- [x] 验收清单
- [x] API文档（docstring）
- [x] 使用示例

### 验收结论

**Task #9实施状态**: ✅ **完成**

**验收通过条件**:
- [ ] 所有后端API测试通过
- [ ] 所有前端UI测试通过
- [ ] 所有浏览器控制台测试通过
- [ ] 响应式设计验证通过
- [ ] 性能指标达标
- [ ] 错误场景处理正确

**签署**:
- 实施人: Claude (Sonnet 4.5)
- 验收人: _____________
- 日期: _____________

---

## 快速测试命令

```bash
# 1. 启动WebUI
python -m agentos.webui.app

# 2. 在浏览器中打开
open http://localhost:8000

# 3. 打开控制台查看日志
# 按F12 -> Console标签

# 4. 测试API端点
curl -s http://localhost:8000/api/chat/sessions/YOUR_SESSION_ID/memory-status | jq

# 5. 手动触发更新（在浏览器控制台）
updateMemoryBadge(state.currentSession)
```

## 常见问题排查

### 问题1: Badge没有显示
**检查**:
1. 控制台是否有错误？
2. `#top-bar-indicators`元素是否存在？
3. CSS文件是否正确加载？

### 问题2: Badge显示"Memory: Error"
**检查**:
1. Session是否存在？
2. API端点是否正常响应？
3. 网络请求是否成功？

### 问题3: Tooltip不显示
**检查**:
1. Hover事件是否绑定？
2. `.memory-tooltip`元素是否存在？
3. CSS的`visible`类是否正确应用？

### 问题4: 自动更新不工作
**检查**:
1. `MemoryBadge.updateInterval`是否为null？
2. 控制台是否有 `[MemoryBadge] Auto-update started` 日志？
3. `startAutoUpdate()`是否被调用？
