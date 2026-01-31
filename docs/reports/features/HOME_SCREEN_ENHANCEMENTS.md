# Home Screen 功能增强

## 概述

Home Screen 现在包含数据库管理和系统更新检查功能，在用户启动 AgentOS TUI 时自动检测系统状态。

## 新增功能

### 1. 数据库初始化检查 (DB Init)

**功能**：启动时自动检测数据库是否已初始化

**工作流程**：
1. 检查 `store/registry.sqlite` 是否存在
2. 如果不存在，显示确认对话框
3. 用户确认后，调用 `init_db()` 创建数据库
4. 创建完整的 v0.6.0 schema（Task-Driven Architecture）

**用户体验**：
```
⚠️  Database not initialized

┌─ Initialize Database ─┐
│ Database not found.   │
│ Initialize now?       │
│                       │
│   [Yes]     [No]      │
└───────────────────────┘
```

**代码位置**：
- `agentos/ui/screens/home.py::_check_system_status()`
- `agentos/ui/screens/home.py::_show_init_prompt()`

### 2. 数据库迁移检查 (DB Migration)

**功能**：检测数据库版本并提供迁移选项

**工作流程**：
1. 连接数据库并查询 `schema_version` 表
2. 比较当前版本与目标版本（v0.6.0）
3. 如果版本不匹配，显示确认对话框
4. 用户确认后，调用 `migrate()` 执行迁移

**支持的迁移路径**：
- v0.5.0 → v0.6.0（添加 Task-Driven Architecture 表）

**用户体验**：
```
⚠️  Database needs migration (v0.5.0 → v0.6.0)

┌────── Migrate Database ──────┐
│ Database version 0.5.0 needs │
│ upgrade to v0.6.0.           │
│ Migrate now?                 │
│                              │
│      [Yes]     [No]          │
└──────────────────────────────┘
```

**代码位置**：
- `agentos/ui/screens/home.py::_check_system_status()`
- `agentos/ui/screens/home.py::_show_migrate_prompt()`
- `agentos/store/migrations.py`

### 3. 更新检查 (Update Check)

**功能**：查询 PyPI 检查 AgentOS 是否有新版本

**工作流程**：
1. 向 PyPI API 发送 HTTP 请求（超时 2 秒）
2. 解析最新版本号
3. 与当前版本比较
4. 显示状态信息

**状态信息**：
- `✓ Up to date` - 当前版本是最新的
- `🔔 Update available: v0.4.0` - 有新版本可用
- 无显示 - 网络错误或超时（静默失败）

**用户体验**：
```
AgentOS
Task Control Plane
v0.3.0

✓ Database ready · 🔔 Update available: v0.4.0

[Command Palette]
```

**代码位置**：
- `agentos/ui/screens/home.py::_check_for_updates()`

**技术细节**：
- API 端点：`https://pypi.org/pypi/agentos/json`
- 超时时间：2 秒
- 错误处理：静默失败（不影响用户体验）

### 4. 系统状态显示

**功能**：在 Home Screen 顶部显示系统状态摘要

**显示格式**：
```
[Status Message 1] · [Status Message 2] · [Status Message 3]
```

**可能的状态**：
- `⚠️  Database not initialized`
- `⚠️  Database needs migration (vX → vY)`
- `⚠️  Database check failed: [error]`
- `✓ Database ready`
- `🔔 Update available: vX.Y.Z`
- `✓ Up to date`

**代码位置**：
- `agentos/ui/screens/home.py::_check_system_status()`
- Status text widget: `#status-text`

## 技术实现

### 数据库检查逻辑

```python
def _check_system_status(self) -> None:
    """检查系统状态：数据库、版本、更新等"""
    status_messages = []
    
    # 1. 检查数据库是否已初始化
    db_path = get_db_path()
    if not db_path.exists():
        status_messages.append("⚠️  Database not initialized")
        self._show_init_prompt()
        return
    
    # 2. 检查数据库版本
    conn = sqlite3.connect(str(db_path))
    current_version = get_current_version(conn)
    conn.close()
    
    if current_version != "0.6.0":
        status_messages.append(f"⚠️  Database needs migration")
        self._show_migrate_prompt(current_version)
        return
    
    # 3. 检查是否有更新
    update_info = self._check_for_updates()
    if update_info:
        status_messages.append(update_info)
```

### 确认对话框集成

使用现有的 `ConfirmDialog` widget：

```python
from agentos.ui.widgets.confirm_dialog import ConfirmDialog

def on_confirm():
    # 执行数据库初始化或迁移
    pass

dialog = ConfirmDialog(
    title="Title",
    message="Message",
    on_confirm=on_confirm
)

self.app.push_screen(dialog)
```

### 样式更新

在 `theme.tcss` 中添加：

```css
.status-text {
    text-align: center;
    color: $text-secondary;
    margin-bottom: 2;
    min-height: 1;
}

/* Confirmation Dialog */
#confirm-dialog {
    align: center middle;
    width: 60;
    height: auto;
    padding: 2;
    background: #1a1a1a;
    border: solid $text-dim;
}
```

## 依赖关系

### 导入的模块
- `pathlib.Path` - 文件路径操作
- `sqlite3` - 数据库连接
- `typing.Optional` - 类型提示
- `urllib.request` - HTTP 请求（PyPI API）
- `json` - JSON 解析

### AgentOS 模块
- `agentos.store` - 数据库路径和初始化
- `agentos.store.migrations` - 版本检查和迁移
- `agentos.ui.widgets.confirm_dialog` - 确认对话框

## 测试场景

### 场景 1：首次启动（未初始化）

**前置条件**：
- `store/registry.sqlite` 不存在

**期望行为**：
1. Home Screen 显示 "⚠️  Database not initialized"
2. 自动弹出初始化确认对话框
3. 用户点击 "Yes" 后，创建数据库
4. 显示通知 "✓ Database initialized at [path]"
5. 状态更新为 "✓ Database ready"

### 场景 2：数据库需要迁移

**前置条件**：
- 数据库存在但版本为 v0.5.0

**期望行为**：
1. Home Screen 显示 "⚠️  Database needs migration (v0.5.0 → v0.6.0)"
2. 自动弹出迁移确认对话框
3. 用户点击 "Yes" 后，执行迁移
4. 显示通知 "✓ Database migrated to v0.6.0"
5. 状态更新为 "✓ Database ready"

### 场景 3：系统正常 + 有更新

**前置条件**：
- 数据库版本正确
- PyPI 上有新版本

**期望行为**：
1. 状态显示 "✓ Database ready · 🔔 Update available: v0.4.0"
2. 用户可正常使用命令面板

### 场景 4：网络异常

**前置条件**：
- 无网络连接或 PyPI API 超时

**期望行为**：
1. 更新检查静默失败（不显示错误）
2. 状态只显示 "✓ Database ready"
3. 不影响其他功能

## 未来改进

### 短期 (v0.4)
- [ ] 添加 "Check for updates" 命令（手动触发）
- [ ] 在命令面板中添加 "Migrate database" 命令
- [ ] 支持更多迁移路径（v0.6 → v0.7）

### 中期 (v0.5)
- [ ] 自动下载和安装更新
- [ ] 迁移进度条显示
- [ ] 数据库备份和恢复

### 长期 (v1.0)
- [ ] 在线帮助和文档查看
- [ ] 系统健康检查（磁盘空间、权限等）
- [ ] 诊断和修复工具

## 常见问题

### Q: 如果用户取消初始化怎么办？

A: 用户仍可查看命令面板，但执行需要数据库的命令时会报错。状态栏会持续显示警告。

### Q: 迁移失败会怎样？

A: 显示错误通知，数据库保持原版本。用户可重试或使用 CLI 命令 `agentos migrate`。

### Q: 更新检查会阻塞 UI 吗？

A: 不会。超时设置为 2 秒，失败时静默处理。UI 响应不受影响。

### Q: 是否支持代理设置？

A: 当前版本使用系统默认代理设置（通过 `urllib`）。未来版本会添加配置选项。

## 相关文件

### 修改的文件
- `agentos/ui/screens/home.py` - 主要逻辑实现
- `agentos/ui/theme.tcss` - 样式更新

### 依赖的文件
- `agentos/store/__init__.py` - `init_db()`, `get_db_path()`
- `agentos/store/migrations.py` - `migrate()`, `get_current_version()`
- `agentos/ui/widgets/confirm_dialog.py` - 确认对话框

### 测试文件
- `tests/unit/test_home_screen.py` - 单元测试（待创建）
- `tests/integration/test_db_migration.py` - 集成测试（待创建）

## 实施日期

2026-01-26

## 作者

AI Assistant (Cursor)
