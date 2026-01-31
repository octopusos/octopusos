# Home Screen 使用指南

## 启动 AgentOS TUI

```bash
agentos tui
# 或
python -m agentos.cli.tui
```

## Home Screen 界面

```
AgentOS
Task Control Plane
v0.3.0

✓ Database ready · 🔔 Update available: v0.4.0

[Command Palette]
↑↓ navigate · Enter select · Type to search
```

## 系统状态指示器

Home Screen 顶部会显示系统状态信息，用不同的图标和颜色表示：

### 数据库状态

- `⚠️  Database not initialized` - 数据库未初始化，需要运行初始化
- `⚠️  Database needs migration (vX → vY)` - 数据库版本需要升级
- `✓ Database ready` - 数据库正常运行

### 更新状态

- `🔔 Update available: vX.Y.Z` - 有新版本可用
- `✓ Up to date` - 当前版本是最新的
- （无显示）- 网络错误或 PyPI 无响应

## 自动提示功能

### 首次启动（数据库未初始化）

当你首次启动 AgentOS TUI 时，如果数据库不存在，会自动弹出确认对话框：

```
┌───── Initialize Database ─────┐
│ Database not found.           │
│ Initialize now?               │
│                               │
│      [Yes]     [No]           │
└───────────────────────────────┘

快捷键:
  Y - 确认初始化
  N - 取消
  ESC - 取消
```

**选择 Yes**：
1. 自动创建 `store/registry.sqlite` 数据库
2. 初始化完整的 v0.6.0 schema（Task-Driven Architecture）
3. 显示成功通知：`✓ Database initialized at [path]`
4. 状态更新为 `✓ Database ready`

**选择 No**：
1. 保持当前状态，可以查看命令面板
2. 但执行需要数据库的命令时会报错
3. 状态栏持续显示警告

### 数据库版本过旧（需要迁移）

如果数据库版本低于当前版本，会自动弹出迁移确认对话框：

```
┌──────── Migrate Database ────────┐
│ Database version 0.5.0 needs     │
│ upgrade to v0.6.0.               │
│ Migrate now?                     │
│                                  │
│       [Yes]     [No]             │
└──────────────────────────────────┘

快捷键:
  Y - 确认迁移
  N - 取消
  ESC - 取消
```

**选择 Yes**：
1. 自动执行数据库迁移脚本
2. 从 v0.5.0 升级到 v0.6.0
3. 添加 Task-Driven Architecture 相关表
4. 显示成功通知：`✓ Database migrated to v0.6.0`
5. 状态更新为 `✓ Database ready`

**选择 No**：
1. 保持当前数据库版本
2. 某些新功能可能无法使用
3. 可以稍后使用 CLI 命令手动迁移：`agentos migrate`

## 手动操作

### 手动初始化数据库

如果你跳过了自动提示，可以使用 CLI 命令手动初始化：

```bash
agentos init
```

输出示例：
```
✅ AgentOS initialized at store/registry.sqlite
```

### 手动迁移数据库

使用 CLI 命令手动迁移数据库：

```bash
agentos migrate --to 0.6.0
```

输出示例：
```
Database: store/registry.sqlite
Current version: 0.5.0
Target version: 0.6.0
✓ Migration to 0.6.0 completed successfully
```

### 检查数据库版本

```bash
sqlite3 store/registry.sqlite "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
```

输出示例：
```
0.6.0
```

## 更新 AgentOS

### 查看当前版本

```bash
agentos --version
# 或在 TUI 中查看 Home Screen 顶部显示
```

### 升级到最新版本

```bash
pip install --upgrade agentos
```

### 检查是否有更新

Home Screen 会自动检查 PyPI 上的最新版本：
- 如果有更新，显示：`🔔 Update available: vX.Y.Z`
- 如果已是最新版本，显示：`✓ Up to date`

## 故障排除

### 问题 1：数据库初始化失败

**症状**：
```
❌ Initialization failed: [error message]
```

**解决方案**：
1. 检查 `store/` 目录权限
   ```bash
   ls -la store/
   ```

2. 手动创建目录
   ```bash
   mkdir -p store
   ```

3. 再次尝试初始化
   ```bash
   agentos init
   ```

### 问题 2：数据库迁移失败

**症状**：
```
❌ Migration failed: [error message]
```

**解决方案**：
1. 备份现有数据库
   ```bash
   cp store/registry.sqlite store/registry.sqlite.backup
   ```

2. 检查数据库文件是否损坏
   ```bash
   sqlite3 store/registry.sqlite "PRAGMA integrity_check"
   ```

3. 如果数据库损坏，恢复备份或重新初始化
   ```bash
   # 恢复备份
   cp store/registry.sqlite.backup store/registry.sqlite
   
   # 或重新初始化（会丢失数据）
   rm store/registry.sqlite
   agentos init
   ```

### 问题 3：无法检查更新

**症状**：
- Home Screen 没有显示更新状态
- 或一直显示 "Checking for updates..."

**可能原因**：
1. 网络连接问题
2. PyPI API 不可访问
3. 防火墙或代理设置

**解决方案**：
1. 检查网络连接
   ```bash
   curl https://pypi.org/pypi/agentos/json
   ```

2. 配置代理（如果需要）
   ```bash
   export https_proxy=http://proxy.example.com:8080
   ```

3. 手动检查更新
   ```bash
   pip index versions agentos
   ```

### 问题 4：状态栏不显示信息

**症状**：
- Home Screen 顶部状态栏为空
- 或显示不完整

**解决方案**：
1. 调整终端窗口大小（至少 80x24）
2. 重启 TUI
3. 检查主题文件是否正确加载

## 最佳实践

### 1. 定期检查更新

建议每周启动一次 TUI 检查是否有更新，或订阅 AgentOS GitHub Release 通知。

### 2. 迁移前备份

在执行数据库迁移前，建议先备份数据：

```bash
# 备份数据库
cp store/registry.sqlite store/registry.sqlite.backup.$(date +%Y%m%d)

# 备份整个 store 目录
tar czf store_backup_$(date +%Y%m%d).tar.gz store/
```

### 3. 测试环境验证

如果你在生产环境使用 AgentOS，建议先在测试环境验证迁移：

```bash
# 复制数据库到测试环境
cp store/registry.sqlite /tmp/test_registry.sqlite

# 测试迁移
agentos migrate --db-path /tmp/test_registry.sqlite --to 0.6.0
```

### 4. 保持版本一致性

确保所有团队成员使用相同的 AgentOS 版本和数据库 schema 版本，避免兼容性问题。

## 相关文档

- [数据库 Schema 文档](../agentos/store/schema_v06.sql)
- [迁移脚本文档](../agentos/store/migrations.py)
- [TUI 使用指南](../TUI_USAGE_GUIDE.md)
- [功能增强文档](./HOME_SCREEN_ENHANCEMENTS.md)

## 反馈和支持

如果遇到问题或有改进建议，请：

1. 查看 [GitHub Issues](https://github.com/your-org/agentos/issues)
2. 提交新 Issue
3. 加入社区讨论

---

最后更新：2026-01-26
