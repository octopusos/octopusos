# 🚀 快速重启指南

## 问题

- 代码已修改，但服务器（PID 57466）仍在运行旧代码
- PID 文件（`~/.agentos/webui.pid`）内容是 97238（已不存在的旧进程）
- `uv run agentos webui restart` 无法正确停止进程 57466

## 🔧 最新修复

**外键约束错误已修复**：

修改了 `agentos/core/extensions/registry.py:531` 的 `update_install_progress()` 方法，在更新 `extension_id` 时也临时禁用外键检查。

详见：[FK_CONSTRAINT_FIX.md](FK_CONSTRAINT_FIX.md)

测试验证：
```bash
python3 verify_fk_fix.py  # ✅ 所有测试通过
```

## ⚡ 一键解决

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./restart_server_complete.sh
```

**这个脚本会自动完成所有步骤！**

## 🔧 手动步骤（3 步完成）

如果脚本失败，执行以下命令：

```bash
# 步骤 1: 停止旧进程
kill 57466 && sleep 2

# 步骤 2: 清理 PID 文件
rm -f ~/.agentos/webui.pid

# 步骤 3: 启动新服务器
uv run agentos webui start
```

## ✅ 验证修复

```bash
# 测试 404 修复
python3 test_404_fix.py
```

期望输出：
```
✓ 测试 1 (错误 ZIP): ✓ 通过
✓ 测试 2 (正常 ZIP): ✓ 通过
```

---

**详细说明**：
- [HOW_TO_RESTART.md](HOW_TO_RESTART.md) - 完整重启指南
- [RESTART_ISSUE_DIAGNOSIS.md](RESTART_ISSUE_DIAGNOSIS.md) - 问题诊断报告
