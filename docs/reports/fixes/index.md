# 修复报告索引

本目录包含 Bug 修复和问题解决报告。

## Gate 相关修复

- [Gate 失败详细报告](./GATE_FAILURES_DETAILED_REPORT.md)
- [Gate 测试分析](./GATE_TESTS_ANALYSIS.md)
- [Gate 测试报告](./GATE_TESTS_REPORT.md)

## UI 修复

- [Enter 键修复](./ENTER_KEY_FIX.md)
- [ID 冒号修复完成](./ID_COLON_FIX_COMPLETE.md)
- [ListView 重复 ID 修复报告](./LISTVIEW_DUPLICATE_ID_FIX_REPORT.md) - 2026-01-26
- [Command Palette 参数输入修复](./COMMAND_PALETTE_ARG_INPUT_FIX_REPORT.md) - 2026-01-26
- [Command Palette UI 修复报告](./COMMAND_PALETTE_UI_FIX_REPORT.md) - 2026-01-27
- [Command Palette 焦点修复](./COMMAND_PALETTE_FOCUS_FIX.md)
- [Debug Command Palette](./DEBUG_COMMAND_PALETTE.md) - 调试报告
- [命令系统实现](./COMMAND_SYSTEM_IMPLEMENTATION.md)
- [Python 兼容性修复](./PYTHON_COMPATIBILITY_FIX.md)
- [ARG_INPUT 模式缺失修复](./ARG_INPUT_MODE_FIX.md) - 2026-01-26
  - 修复 `CommandPaletteMode.ARG_INPUT` 枚举值缺失导致的 AttributeError

## 焦点链修复

- [焦点 API 修复](./FOCUS_API_FIX.md) - 2026-01-27
- [焦点链修复报告](./FOCUS_CHAIN_FIX_REPORT.md) - 2026-01-27
- [焦点链修复最终版](./FOCUS_CHAIN_FIX_FINAL.md) - 2026-01-27
- [焦点修复最终版](./FOCUS_FIX_FINAL.md) - 2026-01-27
- [聊天激活修复](./CHAT_ACTIVATION_FIX.md) - 2026-01-27

## 迁移修复

- [迁移修复完成](./MIGRATION_FIX_COMPLETE.md) - 2026-01-27

## Task 系统修复

- [TaskLineageEntry Timestamp 属性修复](./TASK_LINEAGE_TIMESTAMP_FIX.md) - 2026-01-27
  - 修复 `'TaskLineageEntry' object has no attribute 'timestamp'` 错误
  - 统一模型字段命名（timestamp vs created_at）
  - 保持数据库兼容性和向后兼容

## KB 命令修复

- [KB 命令修复报告](./KB_COMMAND_FIX_REPORT.md) - 2026-01-26
  - 修复 `ProjectKBService.stats()` 方法缺失
  - 添加所有 KB 命令的详细帮助文档
  - 在命令面板中添加 `?` 帮助功能

---

[返回报告索引](../index.md) | [返回文档索引](../../index.md)
