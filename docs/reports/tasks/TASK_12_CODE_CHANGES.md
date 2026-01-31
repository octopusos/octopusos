# Task #12 代码变更摘要

## 📁 修改的文件

| 文件 | 变更类型 | 行数变化 | 说明 |
|------|---------|---------|------|
| `agentos/webui/static/js/views/ProjectsView.js` | 扩展 | +~200 行 | 添加 Settings 标签页、环境变量管理、完整数据收集 |
| `agentos/webui/static/css/multi-repo.css` | 扩展 | +~120 行 | 添加标签页样式、环境变量编辑器样式 |
| `agentos/schemas/project.py` | 无变更 | 0 | Schema 已完整，无需修改 |

---

## 🔧 主要代码变更

### 1. ProjectsView.js - HTML 模板变更

#### 变更前（简化版 Advanced Settings）
```html
<details class="advanced-settings">
    <summary>Advanced Settings</summary>

    <div class="form-group">
        <label for="default-runner">Default Runner</label>
        <select id="default-runner">
            <option value="">-- None --</option>
            <option value="llama.cpp">Llama.cpp</option>
            <option value="openai">OpenAI</option>
        </select>
    </div>

    <div class="form-group">
        <label>
            <input type="checkbox" id="allow-shell-write">
            Allow shell write operations
        </label>
    </div>
</details>
```

#### 变更后（完整 Tabs 设计）
```html
<!-- 标签页导航 -->
<div class="tabs">
    <button type="button" class="tab-btn active" data-tab="basic">Basic Info</button>
    <button type="button" class="tab-btn" data-tab="settings">Settings</button>
</div>

<div class="modal-body">
    <form id="project-form">
        <!-- Basic Info Tab -->
        <div id="tab-basic" class="tab-content active">
            <!-- 现有字段保持不变 -->
        </div>

        <!-- Settings Tab -->
        <div id="tab-settings" class="tab-content">
            <h3 class="settings-section-title">Execution Settings</h3>
            <!-- Default Runner (扩展选项) -->
            <!-- Provider Policy (新增) -->

            <h3 class="settings-section-title">Environment Variables</h3>
            <!-- 动态键值对编辑器 (新增) -->

            <h3 class="settings-section-title">Risk Profile</h3>
            <!-- Allow shell write (保留) -->
            <!-- Require admin token (新增) -->
            <!-- Writable Paths (新增) -->
        </div>
    </form>
</div>
```

**关键变更点**:
1. 从 `<details>` 折叠面板改为 `<div class="tabs">` 标签页
2. 增加 `Provider Policy` 下拉框
3. 增加环境变量动态编辑器
4. 增加 `Require admin token` 复选框
5. 增加 `Writable Paths` 多行文本框

---

### 2. ProjectsView.js - JavaScript 方法变更

#### 新增方法 #1: `switchProjectTab()`
```javascript
/**
 * 切换项目模态框标签页
 * @param {string} tabName - 标签页名称 ('basic' | 'settings')
 */
switchProjectTab(tabName) {
    // Update button states
    this.container.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        }
    });

    // Update content visibility
    this.container.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    this.container.querySelector(`#tab-${tabName}`)?.classList.add('active');
}
```

**作用**: 实现标签页的平滑切换，更新按钮激活状态和内容显示

---

#### 新增方法 #2: `addEnvOverride()`
```javascript
/**
 * 添加环境变量编辑行
 * @param {string} key - 环境变量键名
 * @param {string} value - 环境变量值
 */
addEnvOverride(key = '', value = '') {
    const container = this.container.querySelector('#env-overrides-list');
    const row = document.createElement('div');
    row.className = 'env-override-row';
    row.innerHTML = `
        <input type="text" placeholder="KEY" value="${this.escapeHtml(key)}" class="env-key">
        <input type="text" placeholder="value" value="${this.escapeHtml(value)}" class="env-value">
        <button type="button" class="btn-icon btn-remove-env" title="Remove">
            <span class="material-icons md-18">delete</span>
        </button>
    `;
    container.appendChild(row);

    // Add remove handler
    row.querySelector('.btn-remove-env').addEventListener('click', () => {
        row.remove();
    });
}
```

**作用**: 动态创建环境变量编辑行，支持添加和删除

---

#### 新增方法 #3: `collectEnvOverrides()`
```javascript
/**
 * 收集所有环境变量
 * @returns {Object} 环境变量对象 { KEY: value }
 */
collectEnvOverrides() {
    const rows = this.container.querySelectorAll('.env-override-row');
    const overrides = {};
    rows.forEach(row => {
        const key = row.querySelector('.env-key').value.trim();
        const value = row.querySelector('.env-value').value.trim();
        if (key) {
            overrides[key] = value;
        }
    });
    return overrides;
}
```

**作用**: 遍历所有环境变量行，收集为对象格式，自动过滤空键

---

#### 新增方法 #4: `clearEnvOverrides()`
```javascript
/**
 * 清空所有环境变量行
 */
clearEnvOverrides() {
    const container = this.container.querySelector('#env-overrides-list');
    container.innerHTML = '';
}
```

**作用**: 重置环境变量编辑器，用于创建新项目或切换编辑

---

#### 修改方法 #1: `setupEventListeners()`

**新增事件监听器**:
```javascript
// Tab switching for project modal
this.container.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        this.switchProjectTab(e.target.getAttribute('data-tab'));
    });
});

// Add environment variable button
this.container.querySelector('#add-env-override-btn')?.addEventListener('click', () => {
    this.addEnvOverride();
});
```

**作用**: 为新增的标签页按钮和环境变量按钮绑定事件

---

#### 修改方法 #2: `showCreateProjectModal()`

**新增逻辑**:
```javascript
showCreateProjectModal() {
    // ... 现有逻辑 ...

    // 新增: 清空环境变量
    this.clearEnvOverrides();

    // 新增: 重置到 basic 标签页
    this.switchProjectTab('basic');

    // ... 显示模态框 ...
}
```

**作用**: 创建新项目时，确保 Settings 标签页为空白状态

---

#### 修改方法 #3: `editProject()`

**变更前**:
```javascript
async editProject(projectId) {
    // ... 获取项目数据 ...

    // 填充基础信息
    this.container.querySelector('#project-name').value = project.name;
    // ...

    // 设置 advanced settings (只有 2 个字段)
    if (project.settings) {
        this.container.querySelector('#default-runner').value = project.settings.default_runner || '';
        this.container.querySelector('#allow-shell-write').checked =
            project.settings.risk_profile?.allow_shell_write || false;
    }
}
```

**变更后**:
```javascript
async editProject(projectId) {
    // ... 获取项目数据 ...

    // 填充基础信息 (保持不变)

    // 填充 Settings tab (扩展为完整配置)
    const settings = project.settings || {};

    // Execution Settings
    this.container.querySelector('#settings-default-runner').value = settings.default_runner || '';
    this.container.querySelector('#settings-provider-policy').value = settings.provider_policy || '';

    // Environment Variables (新增)
    this.clearEnvOverrides();
    if (settings.env_overrides) {
        Object.entries(settings.env_overrides).forEach(([key, value]) => {
            this.addEnvOverride(key, value);
        });
    }

    // Risk Profile (扩展)
    const riskProfile = settings.risk_profile || {};
    this.container.querySelector('#settings-allow-shell-write').checked = riskProfile.allow_shell_write || false;
    this.container.querySelector('#settings-require-admin-token').checked = riskProfile.require_admin_token || false;
    this.container.querySelector('#settings-writable-paths').value =
        (riskProfile.writable_paths || []).join('\n');

    // 重置到 basic 标签页
    this.switchProjectTab('basic');
}
```

**关键变更**:
1. 增加 Provider Policy 预填充
2. 增加环境变量动态加载（遍历 key-value pairs）
3. 增加 Require admin token 预填充
4. 增加 Writable Paths 预填充（数组转多行文本）

---

#### 修改方法 #4: `submitProjectForm()`

**变更前**:
```javascript
async submitProjectForm() {
    // ... 收集基础信息 ...

    const formData = {
        name: ...,
        description: ...,
        settings: {
            default_runner: this.container.querySelector('#default-runner').value,
            risk_profile: {
                allow_shell_write: this.container.querySelector('#allow-shell-write').checked
            }
        }
    };
}
```

**变更后**:
```javascript
async submitProjectForm() {
    // ... 收集基础信息 ...

    // 收集 Settings data (扩展为完整配置)
    const defaultRunner = this.container.querySelector('#settings-default-runner').value;
    const providerPolicy = this.container.querySelector('#settings-provider-policy').value;
    const envOverrides = this.collectEnvOverrides();
    const writablePaths = this.container.querySelector('#settings-writable-paths').value
        .split('\n')
        .map(p => p.trim())
        .filter(p => p.length > 0);

    formData.settings = {
        default_runner: defaultRunner || null,
        provider_policy: providerPolicy || null,
        env_overrides: envOverrides,
        risk_profile: {
            allow_shell_write: this.container.querySelector('#settings-allow-shell-write').checked,
            require_admin_token: this.container.querySelector('#settings-require-admin-token').checked,
            writable_paths: writablePaths
        }
    };
}
```

**关键变更**:
1. 增加 Provider Policy 收集
2. 增加环境变量收集（调用 `collectEnvOverrides()`）
3. 增加 Require admin token 收集
4. 增加 Writable Paths 收集（多行文本转数组）
5. 空值处理：使用 `|| null` 确保空字符串转为 null

---

### 3. multi-repo.css - CSS 变更

#### 新增样式 #1: 标签页样式
```css
/* 标签页容器 */
.tabs {
    display: flex;
    border-bottom: 2px solid var(--border-color);
    margin-bottom: 0;
    background: var(--bg-secondary);
}

/* 标签页按钮 */
.tab-btn {
    padding: 12px 24px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-secondary);
    margin-bottom: -2px;
    transition: all 0.2s ease;
}

/* 标签页按钮 - 悬停 */
.tab-btn:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
}

/* 标签页按钮 - 激活 */
.tab-btn.active {
    color: var(--primary-color);
    border-bottom-color: var(--primary-color);
    font-weight: 600;
}

/* 标签页内容 */
.tab-content {
    display: none;
    padding: 20px 0;
}

/* 标签页内容 - 激活 */
.tab-content.active {
    display: block;
}
```

**设计要点**:
- 标签页底部蓝色下划线标识激活状态
- 悬停时显示浅灰色背景
- 平滑过渡动画（0.2s）

---

#### 新增样式 #2: 环境变量编辑器
```css
/* 环境变量容器 */
.env-overrides-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
    max-height: 200px;
    overflow-y: auto;
    padding: 2px;
}

/* 环境变量行 */
.env-override-row {
    display: flex;
    gap: 10px;
    align-items: center;
}

/* 环境变量输入框 */
.env-override-row .env-key,
.env-override-row .env-value {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 14px;
    background: var(--bg-primary);
    color: var(--text-primary);
    transition: border-color 0.2s;
}

/* 环境变量 KEY 样式（等宽字体） */
.env-override-row .env-key {
    font-family: 'Courier New', monospace;
    background-color: var(--bg-secondary);
    font-weight: 500;
}

/* 输入框聚焦状态 */
.env-override-row .env-key:focus,
.env-override-row .env-value:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* 删除按钮 */
.env-override-row .btn-remove-env {
    flex-shrink: 0;
    padding: 6px;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    border-radius: 4px;
    transition: all 0.2s;
}

/* 删除按钮 - 悬停（变红） */
.env-override-row .btn-remove-env:hover {
    background: var(--danger-color);
    color: white;
}
```

**设计要点**:
- KEY 输入框使用等宽字体和特殊背景色（便于识别）
- 删除按钮悬停时变红（危险操作提示）
- 容器支持滚动（最大高度 200px）
- 输入框聚焦时显示蓝色边框和阴影

---

#### 新增样式 #3: Settings 区域标题
```css
.settings-section-title {
    font-size: 16px;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 12px;
    color: var(--text-primary);
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 8px;
}

.settings-section-title:first-child {
    margin-top: 0;
}
```

**设计要点**:
- 区域标题加粗，底部边框线分隔
- 第一个标题不需要上边距

---

## 📊 代码统计

### 新增代码行数

| 文件 | 新增 HTML | 新增 JS | 新增 CSS | 总计 |
|------|-----------|---------|---------|------|
| ProjectsView.js | ~80 | ~120 | 0 | ~200 |
| multi-repo.css | 0 | 0 | ~120 | ~120 |
| **总计** | **80** | **120** | **120** | **~320** |

### 修改代码行数

| 文件 | 修改 JS | 说明 |
|------|---------|------|
| ProjectsView.js | ~50 | 扩展现有方法 |

---

## 🔄 数据流变化

### 变更前（简化版）
```
用户输入 → 表单
  ├─ name
  ├─ description
  ├─ tags
  ├─ default_workdir
  └─ settings (简化)
      ├─ default_runner
      └─ risk_profile
          └─ allow_shell_write

API Payload:
{
  "name": "...",
  "settings": {
    "default_runner": "llama.cpp",
    "risk_profile": {
      "allow_shell_write": true
    }
  }
}
```

### 变更后（完整版）
```
用户输入 → 表单（标签页）
  ├─ Basic Info Tab
  │   ├─ name
  │   ├─ description
  │   ├─ tags
  │   └─ default_workdir
  │
  └─ Settings Tab
      ├─ Execution Settings
      │   ├─ default_runner (扩展选项)
      │   └─ provider_policy (新增)
      │
      ├─ Environment Variables (新增)
      │   └─ env_overrides { KEY: value }
      │
      └─ Risk Profile (扩展)
          ├─ allow_shell_write
          ├─ require_admin_token (新增)
          └─ writable_paths (新增)

API Payload:
{
  "name": "...",
  "settings": {
    "default_runner": "llama.cpp",
    "provider_policy": "prefer-local",
    "env_overrides": {
      "DEBUG": "true",
      "LOG_LEVEL": "info"
    },
    "risk_profile": {
      "allow_shell_write": true,
      "require_admin_token": false,
      "writable_paths": ["/tmp", "./output"]
    }
  }
}
```

---

## 🧪 测试影响分析

### 需要测试的功能点

#### 前端测试
1. **标签页切换**
   - [ ] 点击 "Basic Info" 标签页，显示基础信息表单
   - [ ] 点击 "Settings" 标签页，显示设置表单
   - [ ] 切换标签页后，已填写数据不丢失

2. **环境变量编辑器**
   - [ ] 点击 "Add Variable" 添加新行
   - [ ] 填写 KEY 和 value
   - [ ] 点击删除按钮移除行
   - [ ] 提交时只收集非空 KEY 的变量

3. **Settings 表单**
   - [ ] Default Runner 下拉框显示 4 个选项
   - [ ] Provider Policy 下拉框显示 4 个选项
   - [ ] Writable Paths 支持多行输入
   - [ ] 所有复选框可正常勾选/取消

4. **创建项目**
   - [ ] 创建新项目时，Settings 为默认值
   - [ ] 保存后，Settings 正确存储到数据库

5. **编辑项目**
   - [ ] 编辑已有项目时，Settings 正确预填充
   - [ ] 环境变量动态加载为多行
   - [ ] Writable Paths 数组转为多行文本
   - [ ] 修改后保存，Settings 正确更新

#### 后端测试
1. **API 数据接收**
   - [ ] POST /api/projects 接收完整 Settings
   - [ ] PATCH /api/projects/{id} 更新完整 Settings
   - [ ] GET /api/projects/{id} 返回完整 Settings

2. **Schema 验证**
   - [ ] ProjectSettings Schema 验证通过
   - [ ] RiskProfile Schema 验证通过
   - [ ] 空值处理正确（null vs 空对象）

3. **数据库存储**
   - [ ] settings 字段存储为 JSON
   - [ ] 查询时 JSON 正确解析
   - [ ] env_overrides 对象格式正确
   - [ ] writable_paths 数组格式正确

---

## 🐛 潜在问题和解决方案

### 问题 1: 标签页内容未正确显示
**原因**: CSS 类名不匹配或 JavaScript 选择器错误

**解决方案**:
```javascript
// 确保选择器正确
this.container.querySelector(`#tab-${tabName}`)?.classList.add('active');
```

### 问题 2: 环境变量删除后 DOM 未更新
**原因**: 事件监听器未正确绑定

**解决方案**:
```javascript
// 在 addEnvOverride() 中立即绑定事件
row.querySelector('.btn-remove-env').addEventListener('click', () => {
    row.remove();
});
```

### 问题 3: 编辑时环境变量重复显示
**原因**: 未清空旧数据

**解决方案**:
```javascript
// 在预填充前清空
this.clearEnvOverrides();
if (settings.env_overrides) {
    Object.entries(settings.env_overrides).forEach(([key, value]) => {
        this.addEnvOverride(key, value);
    });
}
```

### 问题 4: 提交时数据格式错误
**原因**: 未正确处理空值

**解决方案**:
```javascript
// 明确使用 null 替代空字符串
default_runner: defaultRunner || null,
provider_policy: providerPolicy || null,
```

---

## 📋 代码审查检查清单

### JavaScript
- [x] 所有新增方法有 JSDoc 注释
- [x] 使用 `escapeHtml()` 防止 XSS
- [x] 事件监听器正确绑定和清理
- [x] 空值处理一致（null vs undefined vs ""）
- [x] 选择器使用 `?.` 可选链，避免 null 错误

### CSS
- [x] 使用 CSS 变量（如 `var(--primary-color)`）
- [x] 过渡动画平滑（`transition: all 0.2s ease`）
- [x] 响应式设计考虑（`@media` 查询）
- [x] 无硬编码颜色值

### HTML
- [x] 语义化标签使用
- [x] 表单字段有对应 `label`
- [x] 必填字段标记 `*`
- [x] 提示文本使用 `<small class="form-hint">`

---

## 🔐 安全考虑

### XSS 防护
```javascript
// ✅ 正确：使用 escapeHtml
value="${this.escapeHtml(key)}"

// ❌ 错误：直接插入用户输入
value="${key}"  // 可能导致 XSS
```

### 环境变量安全
```javascript
// ⚠️ 注意：避免在前端暴露敏感信息
// 环境变量应在后端注入，前端仅配置键名
env_overrides: {
    "API_KEY": "HIDDEN_IN_BACKEND",  // ❌ 不要在前端显示
    "DEBUG": "true"  // ✅ 非敏感信息
}
```

### 路径遍历防护
```python
# 后端应验证 writable_paths
def validate_writable_path(path: str) -> bool:
    # 防止路径遍历攻击
    if ".." in path:
        return False
    # 防止绝对路径逃逸
    if os.path.isabs(path) and not path.startswith(ALLOWED_BASE):
        return False
    return True
```

---

## 📚 相关文档

- [Task #12 Implementation Report](./TASK_12_IMPLEMENTATION_REPORT.md) - 完整实现报告
- [Task #12 UI Guide](./TASK_12_UI_GUIDE.md) - UI 使用指南
- [ProjectSettings Schema](./agentos/schemas/project.py) - Schema 定义
- [Multi-Repo CSS](./agentos/webui/static/css/multi-repo.css) - 样式文件

---

**文档版本**: 1.0
**最后更新**: 2026-01-29
**审查者**: Claude Sonnet 4.5
