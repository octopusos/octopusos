# 按钮交互验收清单

**修复完成时间**: 2026-01-28

## 🔧 已修复的问题

### 1. ❌ 错误的 navigateToView 调用

| 文件 | 行号 | 错误调用 | 修复后 | 说明 |
|------|------|----------|--------|------|
| ConfigView.js | 427 | `navigateToView('selfcheck')` | `navigateToView('support')` | selfcheck 功能在 support 页面 |
| RuntimeView.js | 95 | `navigateToView('selfcheck')` | `navigateToView('support')` | 同上 |
| SupportView.js | 133 | `navigateToView('health-check')` | `navigateToView('overview')` | 健康检查在 overview 页面 |
| SupportView.js | 149 | `navigateToView('selfcheck')` | 改为刷新当前页 | 已在当前页，无需跳转 |

---

## ✅ 验收清单

### Config 页面 (ConfigView.js)

#### Quick Actions 区域

- [ ] **View Providers** 按钮
  - 点击后跳转到 Providers 页面
  - 验证：`navigateToView('providers')`

- [ ] **Run Self-check** 按钮 ✅ 已修复
  - 点击后跳转到 Support 页面
  - 验证：`navigateToView('support')`

- [ ] **Download Config** 按钮
  - 点击后下载配置文件
  - 验证：触发 `downloadConfig()` 方法
  - 文件名格式：`agentos-config-YYYY-MM-DD.json`

#### Header Actions 区域

- [ ] **Refresh** 按钮
  - 点击后重新加载配置
  - 显示 toast: "Configuration reloaded"

- [ ] **View Raw JSON** 按钮
  - 点击后打开 Modal 显示完整 JSON
  - Modal 可通过 overlay 或 × 关闭
  - Modal 内有 "Copy to Clipboard" 按钮

- [ ] **Download** 按钮
  - 点击后下载配置文件
  - 和 Quick Actions 的 Download 功能相同

#### Environment Variables 区域

- [ ] **Filter 输入框**
  - 输入文本即时过滤表格行
  - count badge 实时更新（如 "5 of 66 variables"）
  - 清空输入框恢复所有行

- [ ] **Show all** 按钮
  - 默认只显示前 20 条
  - 点击后展示全部环境变量
  - 展示后按钮消失

- [ ] **Copy 按钮**（每行）
  - 点击复制该环境变量的值
  - 显示 toast: "Value copied to clipboard"

---

### Runtime 页面 (RuntimeView.js)

#### System Actions 区域

- [ ] **Fix File Permissions** 按钮
  - 点击后执行权限修复
  - 显示操作结果

- [ ] **View Providers** 按钮
  - 点击后跳转到 Providers 页面
  - 验证：`navigateToView('providers')`

- [ ] **Run Self-check** 按钮 ✅ 已修复
  - 点击后跳转到 Support 页面
  - 验证：`navigateToView('support')`

---

### Support 页面 (SupportView.js)

#### Diagnostic Bundle 区域

- [ ] **Generate Diagnostics** 按钮
  - 点击后生成诊断数据
  - 显示加载状态

- [ ] **Download as JSON** 按钮
  - 点击后下载诊断数据文件
  - 文件名格式：`agentos-diagnostics-YYYY-MM-DD.json`

- [ ] **View Inline** 按钮
  - 点击后在页面内显示诊断数据
  - 使用 JSON Viewer 展示

- [ ] **Copy to Clipboard** 按钮
  - 点击后复制诊断数据到剪贴板
  - 显示 toast: "Diagnostic data copied to clipboard"

#### Quick Links 区域

- [ ] **System Health** 按钮 ✅ 已修复
  - 点击后跳转到 Overview 页面
  - 验证：`navigateToView('overview')`

- [ ] **Provider Status** 按钮
  - 点击后跳转到 Providers 页面
  - 验证：`navigateToView('providers')`

- [ ] **Run Self-check** 按钮 ✅ 已修复
  - 点击后刷新当前页的诊断数据
  - 页面滚动到顶部
  - 验证：调用 `this.autoGenerate()`

- [ ] **View Logs** 按钮
  - 点击后跳转到 Logs 页面
  - 验证：`navigateToView('logs')`

---

### 其他页面的跨页跳转

#### TasksView.js

- [ ] **View Session** 按钮
  - 跳转到 Chat 页面并切换到对应 session
  - 验证：`navigateToView('chat', { session_id: ... })`

- [ ] **View Events** 按钮
  - 跳转到 Events 页面并过滤该 task
  - 验证：`navigateToView('events', { task_id: ... })`

- [ ] **View Logs** 按钮
  - 跳转到 Logs 页面并过滤该 task
  - 验证：`navigateToView('logs', { task_id: ... })`

#### EventsView.js

- [ ] **View Task** 按钮
  - 跳转到 Tasks 页面并过滤该 task
  - 验证：`navigateToView('tasks', { task_id: ... })`

- [ ] **View Session** 按钮
  - 跳转到 Chat 页面并切换到对应 session
  - 验证：`navigateToView('chat', { session_id: ... })`

#### LogsView.js

- [ ] **View Task** 按钮
  - 跳转到 Tasks 页面并过滤该 task
  - 验证：`navigateToView('tasks', { task_id: ... })`

#### SessionsView.js

- [ ] **Open Chat** 按钮
  - 跳转到 Chat 页面并切换到对应 session
  - 验证：`navigateToView('chat', { session_id: ... })`

- [ ] **View Tasks** 按钮
  - 跳转到 Tasks 页面并过滤该 session
  - 验证：`navigateToView('tasks', { session_id: ... })`

- [ ] **View Events** 按钮
  - 跳转到 Events 页面并过滤该 session
  - 验证：`navigateToView('events', { session_id: ... })`

- [ ] **View Logs** 按钮
  - 跳转到 Logs 页面并过滤该 session
  - 验证：`navigateToView('logs', { session_id: ... })`

#### MemoryView.js

- [ ] **View Task** 链接
  - 跳转到 Tasks 页面并过滤该 task
  - 验证：`navigateToView('tasks', { task_id: ... })`

- [ ] **View Session** 链接
  - 跳转到 Sessions 页面并过滤该 session
  - 验证：`navigateToView('sessions', { session_id: ... })`

#### SkillsView.js

- [ ] **View Logs** 按钮
  - 跳转到 Logs 页面并搜索该 skill
  - 验证：`navigateToView('logs', { contains: ... })`

---

## 📊 修复总结

| 类型 | 数量 | 说明 |
|------|------|------|
| 修复的错误调用 | 4 | selfcheck → support (3) + health-check → overview (1) |
| Config 页面按钮 | 9 | Header (3) + Quick Actions (3) + Env Vars (3) |
| Runtime 页面按钮 | 3 | System Actions 区域 |
| Support 页面按钮 | 8 | Diagnostic (4) + Quick Links (4) |
| 其他页面跨页按钮 | 11+ | Tasks/Events/Logs/Sessions/Memory/Skills |

---

## 🧪 测试方法

### 自动化测试脚本（可选）

```javascript
// 在浏览器控制台运行
const testNavigateToView = (viewName) => {
    console.log(`Testing: ${viewName}`);
    window.navigateToView(viewName);
    setTimeout(() => {
        const content = document.getElementById('view-container');
        if (content.innerHTML.includes('View not implemented')) {
            console.error(`❌ FAILED: ${viewName}`);
        } else {
            console.log(`✅ PASSED: ${viewName}`);
        }
    }, 100);
};

// 测试所有 view
const allViews = [
    'chat', 'overview', 'sessions', 'tasks', 'events', 'logs',
    'skills', 'memory', 'providers', 'config', 'context', 'runtime', 'support'
];

allViews.forEach((view, index) => {
    setTimeout(() => testNavigateToView(view), index * 500);
});
```

### 手动测试步骤

1. **启动 WebUI**
   ```bash
   cd /Users/pangge/PycharmProjects/AgentOS
   agentos webui start
   ```

2. **逐页测试**
   - 打开浏览器访问 WebUI
   - 依次进入 Config / Runtime / Support 页面
   - 点击所有按钮，验证行为符合预期

3. **验收标准**
   - ✅ 所有按钮点击后无错误提示
   - ✅ 跳转按钮能正确导航到目标页面
   - ✅ 操作按钮能正确执行功能
   - ✅ Toast 提示信息正确显示

---

## ✅ 完成确认

- [x] 修复所有错误的 navigateToView 调用
- [ ] 测试 Config 页面所有按钮
- [ ] 测试 Runtime 页面所有按钮
- [ ] 测试 Support 页面所有按钮
- [ ] 测试跨页跳转功能

**修复完成，等待用户验收！** 🎉
