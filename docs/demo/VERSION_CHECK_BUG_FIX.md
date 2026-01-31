# 数据库版本检查 Bug 修复报告

## 🐛 问题描述

用户启动 AgentOS TUI 时，看到错误提示：

```
Database version 0.10.0 needs upgrade to v0.6.0
```

这是一个**逻辑错误**：当前版本 `0.10.0` **比** 目标版本 `0.6.0` **更新**，系统却提示需要"升级"。

## 🔍 根本原因

在多个文件中**硬编码**了 `0.6.0` 作为目标版本，没有使用 `migrations.py` 中定义的 `LATEST_VERSION` 常量：

### 问题文件

1. **`agentos/ui/screens/home.py`** (2 处)
   - 第 69 行：版本比较 `elif current_version != "0.6.0":`
   - 第 119 行：迁移调用 `migrate(db_path, target_version="0.6.0")`
   - 第 128 行：提示消息 `needs upgrade to v0.6.0`

2. **`agentos/cli/health.py`** (1 处)
   - 第 32 行：硬编码 `EXPECTED_VERSION = "0.6.0"`

### 为什么会出现这个问题？

在迁移系统重构时（commit 22b39ed），我们：
- ✅ 在 `migrations.py` 中定义了 `LATEST_VERSION = "0.10.0"`
- ✅ 更新了迁移链，支持到 v0.10.0
- ❌ **但忘记更新 UI 和 CLI 中的硬编码版本号**

## ✅ 修复方案

### 修改 1: `agentos/ui/screens/home.py`

```python
# 导入 LATEST_VERSION
from agentos.store.migrations import get_current_version, migrate, LATEST_VERSION

# 版本比较（第 69 行）
elif current_version != LATEST_VERSION:
    status_messages.append(f"⚠️  Database needs migration (v{current_version} → v{LATEST_VERSION})")

# 迁移调用（第 119 行）
migrate(db_path, target_version=LATEST_VERSION)

# 提示消息（第 128 行）
message=f"Database version {current_version} needs upgrade to v{LATEST_VERSION}. Migrate now?"
```

### 修改 2: `agentos/cli/health.py`

```python
# 导入并使用 LATEST_VERSION（第 27 行）
from agentos.store.migrations import get_current_version, LATEST_VERSION

if current != LATEST_VERSION:
    return False, (
        f"Database schema version is {current}, expected {LATEST_VERSION}. "
        f"Please run: agentos migrate"
    )
```

## 🎯 修复后的行为

### 场景 1: 数据库版本 = 最新版本 (0.10.0)
- ✅ 显示：`✓ Database ready`
- ✅ 不弹出迁移提示

### 场景 2: 数据库版本 < 最新版本 (如 0.6.0)
- ✅ 显示：`⚠️  Database needs migration (v0.6.0 → v0.10.0)`
- ✅ 弹出迁移提示
- ✅ 点击 Yes 后执行 `migrate(db_path, "0.10.0")`

### 场景 3: 数据库版本 > 最新版本（不应发生，除非降级代码）
- ✅ 显示警告（与场景 2 相同）
- ✅ 用户可以选择回滚或更新代码

## 🔒 预防措施

### 1. 使用中心化的版本常量

**正确做法**：
```python
from agentos.store.migrations import LATEST_VERSION

if current != LATEST_VERSION:
    migrate(db_path, target_version=LATEST_VERSION)
```

**错误做法**：
```python
# ❌ 不要硬编码版本号
if current != "0.6.0":
    migrate(db_path, target_version="0.6.0")
```

### 2. 添加到 Code Review Checklist

在未来的 PR 中检查：
- [ ] 是否有新的版本号硬编码？
- [ ] 是否使用了 `LATEST_VERSION` 常量？
- [ ] 是否更新了 `migrations.py` 中的 `LATEST_VERSION`？

### 3. 考虑添加 Lint Rule

可以添加一个 lint 规则检测硬编码的版本号：
```bash
# 搜索可疑的版本号硬编码
rg '["'"'"']0\.\d+\.\d+["'"'"']' --type py --ignore-file migrations.py --ignore-file schema*.sql
```

## 📋 测试验证

### 手动测试步骤

1. **确保数据库是 v0.10.0**
   ```bash
   python3 -c "import sqlite3; from agentos.store import get_db_path; \
   conn = sqlite3.connect(str(get_db_path())); \
   print(conn.execute('SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1').fetchone()[0])"
   ```

2. **启动 TUI**
   ```bash
   agentos
   ```

3. **验证状态**
   - 应该显示：`✓ Database ready`
   - **不应该**弹出迁移提示

4. **测试旧版本场景**（可选）
   ```bash
   # 降级到 v0.6.0
   python3 -m agentos.store.migrations rollback 0.6.0
   
   # 重新启动 TUI
   agentos
   
   # 应该显示：Database needs migration (v0.6.0 → v0.10.0)
   # 点击 Yes 应该成功迁移
   ```

## 🎉 总结

### 修复的文件
- `agentos/ui/screens/home.py` - 3 处硬编码版本号
- `agentos/cli/health.py` - 1 处硬编码版本号

### 影响范围
- ✅ TUI 启动时的版本检查
- ✅ CLI health check
- ✅ 迁移提示消息

### 向后兼容性
- ✅ 完全兼容（只是修复了 bug）
- ✅ 不影响已有数据
- ✅ 不改变迁移逻辑

---

**修复日期**: 2026-01-26  
**相关 Commit**: 22b39ed (迁移系统重构)  
**Bug 影响**: 用户看到错误的版本提示  
**修复优先级**: P0 (阻塞用户使用)
