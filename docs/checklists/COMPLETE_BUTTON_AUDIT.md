# 完整按钮审计报告

## 🔍 所有 navigateToView 调用清单

### ✅ 有效的 View 名称（在 main.js 中定义）

```javascript
// main.js loadView() switch case
const validViews = [
    'chat',
    'overview',
    'sessions',
    'tasks',
    'events',
    'logs',
    'skills',
    'memory',
    'config',
    'context',
    'runtime',
    'support',
    'providers',
    'knowledge-playground'
];
```

---

## 📋 各页面按钮清单

### ConfigView.js

#### Quick Actions 区域
| 按钮ID | 文本 | Icon | 目标 View | 状态 |
|--------|------|------|-----------|------|
| `#view-providers` | View Providers | power | `providers` | ✅ 有效 |
| `#view-selfcheck` | Run Self-check | done | `support` | ✅ 已修复 |
| `#download-config-footer` | Download Config | download | （下载文件） | ✅ 功能调用 |

#### Header Actions
| 按钮ID | 文本 | Icon | 目标 View | 状态 |
|--------|------|------|-----------|------|
| `#config-refresh` | Refresh | refresh | （刷新） | ✅ 功能调用 |
| `#config-view-raw` | View Raw JSON | code | （打开 Modal） | ✅ 功能调用 |
| `#config-download` | Download | download | （下载文件） | ✅ 功能调用 |

---

### RuntimeView.js

#### System Actions
| 按钮ID | 文本 | Icon | 目标 View | 状态 |
|--------|------|------|-----------|------|
| `#runtime-fix-permissions` | Fix File Permissions | lock | （执行操作） | ✅ 功能调用 |
| `#runtime-view-providers` | View Providers | power | `providers` | ✅ 有效 |
| `#runtime-run-selfcheck` | Run Self-check | done | `support` | ✅ 已修复 |

#### Provider Summary (动态生成)
| 按钮ID | 文本 | 目标 View | 状态 |
|--------|------|-----------|------|
| `#runtime-goto-providers` | View Full Provider Status → | `providers` | ✅ 有效 |

---

### SupportView.js

#### Quick Links
| 按钮ID | 文本 | Icon | 目标 View | 状态 |
|--------|------|------|-----------|------|
| `#support-view-health` | System Health | favorite | `overview` | ✅ 已修复 |
| `#support-view-providers` | Provider Status | power | `providers` | ✅ 有效 |
| `#support-run-selfcheck` | Run Self-check | done | （刷新当前页） | ✅ 已修复 |
| `#support-view-logs` | View Logs | description | `logs` | ✅ 有效 |

#### Diagnostic Actions
| 按钮ID | 文本 | 目标 View | 状态 |
|--------|------|-----------|------|
| `#support-generate` | Generate Diagnostics | （执行操作） | ✅ 功能调用 |
| `#support-download-json` | Download as JSON | （下载文件） | ✅ 功能调用 |
| `#support-view-inline` | View Inline | （展示内容） | ✅ 功能调用 |
| `#support-copy` | Copy to Clipboard | （复制） | ✅ 功能调用 |

---

### SkillsView.js

#### Skill Detail Drawer (动态生成)
| 按钮ID | 文本 | Icon | 目标 View | 状态 |
|--------|------|------|-----------|------|
| `#view-logs` | View Logs | description | `logs` (with filter) | ✅ 有效 |
| `#copy-skill-name` | Copy Skill Name | content_copy | （复制） | ✅ 功能调用 |

---

### TasksView.js

#### Task Detail Drawer (动态生成)
| 按钮 | 文本 | 目标 View | 状态 |
|------|------|-----------|------|
| View Session | - | `chat` (with session_id) | ✅ 有效 |
| View Events | - | `events` (with task_id) | ✅ 有效 |
| View Logs | - | `logs` (with task_id) | ✅ 有效 |

---

### EventsView.js

#### Event Detail Drawer (动态生成)
| 按钮 | 文本 | 目标 View | 状态 |
|------|------|-----------|------|
| View Task | - | `tasks` (with task_id) | ✅ 有效 |
| View Session | - | `chat` (with session_id) | ✅ 有效 |

---

### LogsView.js

#### Log Detail Drawer (动态生成)
| 按钮 | 文本 | 目标 View | 状态 |
|------|------|-----------|------|
| View Task | - | `tasks` (with task_id) | ✅ 有效 |

---

### SessionsView.js

#### Session Detail Drawer (动态生成)
| 按钮ID | 文本 | Icon | 目标 View | 状态 |
|--------|------|------|-----------|------|
| `#session-open-chat` | Open Chat | chat_bubble | `chat` (with session_id) | ✅ 有效 |
| `#session-view-tasks` | View Tasks | task | `tasks` (with session_id) | ✅ 有效 |
| `#session-view-events` | View Events | 📡 | `events` (with session_id) | ✅ 有效 |
| `#session-view-logs` | View Logs | edit_note | `logs` (with session_id) | ✅ 有效 |

---

### MemoryView.js

#### Memory Detail Drawer (动态生成)
| 链接 | 文本 | 目标 View | 状态 |
|------|------|-----------|------|
| View Task | - | `tasks` (with task_id) | ✅ 有效 |
| View Session | - | `sessions` (with session_id) | ✅ 有效 |

---

## 🧪 浏览器控制台测试脚本

### 测试所有 View 是否可访问

```javascript
// 复制到浏览器控制台运行
const testAllViews = () => {
    const validViews = [
        'chat', 'overview', 'sessions', 'tasks', 'events', 'logs',
        'skills', 'memory', 'config', 'context', 'runtime', 'support', 'providers'
    ];

    const results = [];

    validViews.forEach((view, index) => {
        setTimeout(() => {
            console.log(`\n[${index + 1}/${validViews.length}] Testing: ${view}`);
            window.navigateToView(view);

            setTimeout(() => {
                const container = document.getElementById('view-container');
                const hasError = container.innerHTML.includes('View not implemented');

                if (hasError) {
                    console.error(`❌ FAILED: ${view} - "View not implemented"`);
                    results.push({ view, status: 'FAILED' });
                } else {
                    console.log(`✅ PASSED: ${view}`);
                    results.push({ view, status: 'PASSED' });
                }

                if (index === validViews.length - 1) {
                    console.log('\n=== Test Summary ===');
                    console.table(results);

                    const failures = results.filter(r => r.status === 'FAILED');
                    if (failures.length > 0) {
                        console.error(`\n❌ ${failures.length} view(s) failed:`, failures.map(f => f.view));
                    } else {
                        console.log('\n✅ All views passed!');
                    }
                }
            }, 200);
        }, index * 500);
    });
};

testAllViews();
```

### 测试 Config 页面所有按钮

```javascript
// 先导航到 Config 页面
window.navigateToView('config');

setTimeout(() => {
    console.log('=== Testing Config View Buttons ===\n');

    // 测试 Quick Actions
    const buttons = [
        { id: 'view-providers', name: 'View Providers', target: 'providers' },
        { id: 'view-selfcheck', name: 'Run Self-check', target: 'support' },
        { id: 'download-config-footer', name: 'Download Config', target: 'download' }
    ];

    buttons.forEach(btn => {
        const element = document.getElementById(btn.id);
        if (element) {
            console.log(`✅ Button found: #${btn.id} - "${btn.name}"`);
            console.log(`   → Target: ${btn.target}`);
        } else {
            console.error(`❌ Button NOT found: #${btn.id}`);
        }
    });
}, 500);
```

### 测试 Support 页面所有按钮

```javascript
// 先导航到 Support 页面
window.navigateToView('support');

setTimeout(() => {
    console.log('=== Testing Support View Buttons ===\n');

    const buttons = [
        { id: 'support-view-health', name: 'System Health', target: 'overview' },
        { id: 'support-view-providers', name: 'Provider Status', target: 'providers' },
        { id: 'support-run-selfcheck', name: 'Run Self-check', target: 'refresh' },
        { id: 'support-view-logs', name: 'View Logs', target: 'logs' }
    ];

    buttons.forEach(btn => {
        const element = document.getElementById(btn.id);
        if (element) {
            console.log(`✅ Button found: #${btn.id} - "${btn.name}"`);
            console.log(`   → Target: ${btn.target}`);
        } else {
            console.error(`❌ Button NOT found: #${btn.id}`);
        }
    });
}, 500);
```

### 测试 Runtime 页面所有按钮

```javascript
// 先导航到 Runtime 页面
window.navigateToView('runtime');

setTimeout(() => {
    console.log('=== Testing Runtime View Buttons ===\n');

    const buttons = [
        { id: 'runtime-view-providers', name: 'View Providers', target: 'providers' },
        { id: 'runtime-run-selfcheck', name: 'Run Self-check', target: 'support' }
    ];

    buttons.forEach(btn => {
        const element = document.getElementById(btn.id);
        if (element) {
            console.log(`✅ Button found: #${btn.id} - "${btn.name}"`);
            console.log(`   → Target: ${btn.target}`);
        } else {
            console.error(`❌ Button NOT found: #${btn.id}`);
        }
    });
}, 500);
```

---

## 🔧 已修复的问题汇总

| 文件 | 行号 | 原错误 | 修复后 |
|------|------|--------|--------|
| ConfigView.js | 427 | `navigateToView('selfcheck')` | `navigateToView('support')` |
| RuntimeView.js | 95 | `navigateToView('selfcheck')` | `navigateToView('support')` |
| SupportView.js | 133 | `navigateToView('health-check')` | `navigateToView('overview')` |
| SupportView.js | 149 | `navigateToView('selfcheck')` | 改为 `this.autoGenerate()` |

---

## ✅ 验证结果

所有 `navigateToView` 调用的目标 view 都已验证为有效：

- ✅ `chat` - 有效
- ✅ `overview` - 有效
- ✅ `sessions` - 有效
- ✅ `tasks` - 有效
- ✅ `events` - 有效
- ✅ `logs` - 有效
- ✅ `skills` - 有效
- ✅ `memory` - 有效
- ✅ `providers` - 有效
- ✅ `config` - 有效
- ✅ `context` - 有效
- ✅ `runtime` - 有效
- ✅ `support` - 有效

**不再使用的无效 view 名称**:
- ❌ `selfcheck` (已全部替换为 `support`)
- ❌ `health-check` (已替换为 `overview`)

---

## 📝 使用说明

1. **启动 WebUI**
   ```bash
   agentos webui start
   ```

2. **在浏览器中打开 DevTools (F12)**

3. **粘贴并运行测试脚本**
   - 测试所有 view 是否可访问
   - 测试各页面按钮是否存在

4. **手动点击测试**
   - 逐页点击所有按钮
   - 验证跳转行为正确
   - 验证无 "View not implemented" 错误

---

## 🎯 预期结果

- ✅ 所有按钮点击后能正确跳转或执行功能
- ✅ 无 "View not implemented" 错误
- ✅ Toast 提示信息正常显示
- ✅ 跨页跳转携带的过滤器参数正确应用

---

**审计完成时间**: 2026-01-28
**修复的问题数**: 4
**验证的按钮数**: 30+
