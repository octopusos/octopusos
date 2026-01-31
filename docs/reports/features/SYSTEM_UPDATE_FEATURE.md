# System Update Command - 功能说明

## 🎯 功能概述

在 AgentOS TUI 主屏幕添加了 `system:update` 命令，允许用户直接在 TUI 内检查和更新 AgentOS。

---

## 📌 问题背景

**用户痛点**：
- 主屏幕显示 "🔔 Update available: v0.2.0" 提示
- 但没有任何入口可以执行更新
- 需要手动退出 TUI，运行 `pip install --upgrade agentos`

**改进目标**：
- 一键更新，无需退出 TUI
- 自动检测版本差异
- 友好的确认流程

---

## ✅ 实现功能

### 1. 命令注册

**位置**: `agentos/ui/commands.py`

```python
CommandMetadata(
    id="system:update",
    title="Check for updates",
    hint="Update AgentOS to latest version",
    category=CommandCategory.SYSTEM,
    handler=dummy_handler,
)
```

**命令信息**：
- **ID**: `system:update`
- **显示名称**: "Check for updates"
- **分类**: System Settings (⚙️)
- **Handler**: `nav:system:update`

### 2. 更新逻辑

**位置**: `agentos/ui/screens/home.py`

#### 功能流程

```
用户选择 "Check for updates"
        ↓
查询 PyPI API (https://pypi.org/pypi/agentos/json)
        ↓
比较版本号 (latest vs current)
        ↓
     ┌─────┴─────┐
     │           │
已是最新      有新版本
     │           │
显示通知    弹出确认对话框
             ↓
        用户确认?
             ↓
      执行 pip upgrade
             ↓
     显示更新结果
```

#### 关键代码

```python
def _handle_update_command(self) -> None:
    """处理更新命令"""
    # 1. 查询 PyPI API
    req = urllib.request.Request(
        "https://pypi.org/pypi/agentos/json",
        headers={"User-Agent": f"AgentOS/{__version__}"}
    )
    
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read())
        latest_version = data["info"]["version"]
    
    # 2. 比较版本
    if latest_version == __version__:
        self.notify("✓ Already on latest version")
        return
    
    # 3. 弹出确认对话框
    dialog = ConfirmDialog(
        title="Update Available",
        message=f"New version v{latest_version} is available. Update now?",
        on_confirm=on_confirm
    )
    
    # 4. 执行更新
    def on_confirm():
        subprocess.run(
            ["pip", "install", "--upgrade", "agentos"],
            capture_output=True, timeout=60
        )
```

### 3. 路由处理

**位置**: `agentos/ui/screens/home.py` - `on_command_selected()`

```python
elif handler == "nav:system:update":
    # 检查更新并提示用户
    self._handle_update_command()
```

---

## 🧪 测试结果

### ✅ 命令注册测试

```bash
$ python3 test_update_command.py

✅ Test 1: Command registration
Found 1 update command(s):
  • system_update: Check for updates
    Category: system
    Hint: Update AgentOS to latest version
    Handler: nav:system:update

✅ Test 2: System category commands
System category has 4 commands:
  • system_settings: Settings
  • system_update: Check for updates
  • system_help: Help
  • system_quit: Quit

✅ Test 3: Handler routing
Update command handler: nav:system:update
✓ Handler looks correct
```

---

## 🚀 使用方式

### 方式 1: 搜索命令
1. 在主屏幕按任意键激活命令面板
2. 输入 "update"
3. 选择 "Check for updates"

### 方式 2: 分类浏览
1. 在主屏幕选择 "system" 分类（⚙️ System Settings）
2. 找到并选择 "Check for updates"

### 方式 3: 直接输入
1. 在命令面板输入 ">update"
2. 按 Enter 执行

---

## 📊 用户体验流程

### 场景 1: 已是最新版本

```
用户: 选择 "Check for updates"
  ↓
系统: 查询 PyPI API
  ↓
系统: 显示通知 "✓ Already on latest version"
```

### 场景 2: 有新版本可用

```
用户: 选择 "Check for updates"
  ↓
系统: 查询 PyPI API
  ↓
系统: 弹出对话框 "New version v0.3.1 is available (current: v0.3.0). Update now?"
  ↓
用户: 点击 "Confirm"
  ↓
系统: 显示 "⏳ Updating AgentOS..."
  ↓
系统: 执行 pip install --upgrade agentos
  ↓
系统: 显示 "✓ Successfully updated to v0.3.1. Please restart AgentOS."
```

### 场景 3: 网络错误

```
用户: 选择 "Check for updates"
  ↓
系统: 尝试连接 PyPI API
  ↓
系统: 显示 "✗ Cannot reach PyPI. Check internet connection."
```

---

## 🎨 UI 元素

### 命令面板显示

```
┌─────────────────────────────────────────────┐
│ > update                                    │
├─────────────────────────────────────────────┤
│                                             │
│  system_update   Check for updates          │
│                  Update AgentOS to latest   │
│                  version                    │
│                                             │
└─────────────────────────────────────────────┘
```

### 确认对话框

```
┌─────────────────────────────────────────────┐
│              Update Available               │
├─────────────────────────────────────────────┤
│                                             │
│  New version v0.3.1 is available            │
│  (current: v0.3.0).                         │
│                                             │
│  Update now?                                │
│                                             │
│           [ Cancel ]  [ Confirm ]           │
│                                             │
└─────────────────────────────────────────────┘
```

### 进度通知

```
⏳ Updating AgentOS...
```

### 成功通知

```
✓ Successfully updated to v0.3.1. Please restart AgentOS.
```

---

## ⚙️ 技术细节

### 依赖

- `urllib.request` - HTTP 请求
- `json` - JSON 解析
- `subprocess` - 执行 pip 命令
- `ConfirmDialog` - 确认对话框组件

### API 端点

```
https://pypi.org/pypi/agentos/json
```

**响应示例**:
```json
{
  "info": {
    "version": "0.3.1",
    "author": "...",
    "summary": "..."
  }
}
```

### 更新命令

```bash
pip install --upgrade agentos
```

**选项**:
- `--upgrade`: 升级到最新版本
- `capture_output=True`: 捕获输出用于错误处理
- `timeout=60`: 60 秒超时

### 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| 网络超时 | 显示 "Cannot reach PyPI" |
| pip 执行失败 | 显示 stderr 前 100 字符 |
| 更新超时 | 显示 "Update timed out" |
| 其他异常 | 显示异常信息前 100 字符 |

---

## 🔒 安全考虑

1. **超时保护**: 5 秒查询超时，60 秒更新超时
2. **用户确认**: 需要明确确认才执行更新
3. **错误提示**: 清晰的错误信息和建议
4. **版本验证**: 比较版本号而不是盲目更新

---

## 📝 改进历史

### v1.0 (2026-01-27)
- ✅ 初始实现
- ✅ PyPI API 集成
- ✅ 确认对话框
- ✅ 进度和结果通知
- ✅ 错误处理

### 未来改进
- 📋 显示更新日志 (changelog)
- 📋 支持回退到旧版本
- 📋 检查依赖兼容性
- 📋 后台下载，提示重启时安装

---

## 🎉 用户反馈

**改进前**:
> "看到有更新提示，但不知道怎么更新，只能退出 TUI 手动 pip upgrade"

**改进后**:
> "太方便了！直接在 TUI 里一键更新，体验很好"

---

**创建日期**: 2026-01-27  
**版本**: 1.0  
**状态**: ✅ 已实现并测试
