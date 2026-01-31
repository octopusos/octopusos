# Home Screen 功能快速参考

## 🎯 核心功能

### 1️⃣ 数据库初始化 (DB Init)
**触发条件**: `store/registry.sqlite` 不存在  
**提示**: `⚠️  Database not initialized`  
**操作**: 显示确认对话框 → 执行 `init_db()`  
**快捷键**: `Y` 确认 / `N` 取消 / `ESC` 取消

### 2️⃣ 数据库迁移 (DB Migrate)
**触发条件**: 数据库版本 < v0.6.0  
**提示**: `⚠️  Database needs migration (vX → v0.6.0)`  
**操作**: 显示确认对话框 → 执行 `migrate()`  
**快捷键**: `Y` 确认 / `N` 取消 / `ESC` 取消

### 3️⃣ 更新检查 (Update Check)
**触发条件**: 每次启动 TUI  
**提示**: `🔔 Update available: vX.Y.Z` 或 `✓ Up to date`  
**操作**: 被动显示，不需要操作  
**特性**: 2秒超时，静默失败

## 📊 状态指示器

| 图标 | 含义 | 操作建议 |
|-----|------|---------|
| ⚠️  | 需要处理 | 按提示操作 |
| ✓ | 正常 | 无需操作 |
| 🔔 | 提醒 | 考虑升级 |

## 🖥️ 界面示例

```
AgentOS
Task Control Plane
v0.3.0

✓ Database ready · 🔔 Update available: v0.4.0

[Command Palette]
↑↓ navigate · Enter select · Type to search
```

## 🔧 手动操作

```bash
# 初始化数据库
agentos init

# 迁移数据库
agentos migrate --to 0.6.0

# 检查版本
agentos --version

# 升级 AgentOS
pip install --upgrade agentos
```

## 🐛 故障排除

### 问题: 初始化失败
**解决**: 检查目录权限 → `mkdir -p store`

### 问题: 迁移失败
**解决**: 备份数据库 → `cp store/registry.sqlite store/registry.sqlite.backup`

### 问题: 无法检查更新
**解决**: 检查网络 → `curl https://pypi.org/pypi/agentos/json`

## 📚 完整文档

- [技术文档](docs/HOME_SCREEN_ENHANCEMENTS.md) - 实现细节
- [用户指南](docs/HOME_SCREEN_USER_GUIDE.md) - 使用说明
- [实施总结](HOME_SCREEN_IMPLEMENTATION_SUMMARY.md) - 完成报告
- [验收清单](HOME_SCREEN_ACCEPTANCE.md) - 质量保证

## 🧪 测试

```bash
# 运行测试
python3 tests/test_home_enhancements.py

# 查看演示
python3 scripts/demo_home_enhancements.py
```

---

**版本**: v0.3.0+enhancement  
**日期**: 2026-01-26
