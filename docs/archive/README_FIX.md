# Extension 安装修复 - 执行指南

## 🎯 问题

1. ❌ 安装 Extension 返回 404，用户不知道失败原因
2. ❌ 报错 "FOREIGN KEY constraint failed"

## ✅ 已修复

1. ✅ 立即创建 install record，前端始终能查询到状态
2. ✅ 验证失败返回 FAILED（不是 404）
3. ✅ 更新 extension_id 时禁用外键检查

## 🚀 一键应用修复

```bash
cd /Users/pangge/PycharmProjects/AgentOS
./apply_fix.sh
```

这个脚本会：
1. 验证代码修复已就位
2. 重启服务器（停止 PID 57466）
3. 运行完整测试

## 📋 预期结果

执行 `./apply_fix.sh` 后应该看到：

```
✓ registry.py 修复已就位
✓ extensions.py 修复已就位
✓ 服务器进程已启动
✓ API 响应正常
✓ 上传成功
✓ Install Record 立即被创建
✓ 能查询到安装进度
✅ 所有测试通过
```

## 🔧 手动步骤（如果脚本失败）

```bash
# 1. 停止旧服务器
kill 57466 && rm -f ~/.agentos/webui.pid

# 2. 启动新服务器
uv run agentos webui start

# 3. 测试验证
python3 debug_install_step_by_step.py
```

## 📚 详细文档

- **快速参考**：[FINAL_FIX_STEPS.md](FINAL_FIX_STEPS.md)
- **404 修复**：[NO_MORE_404_FIX.md](NO_MORE_404_FIX.md)
- **外键修复**：[FK_CONSTRAINT_FIX.md](FK_CONSTRAINT_FIX.md)
- **重启指南**：[HOW_TO_RESTART.md](HOW_TO_RESTART.md)

## 💡 修复效果

### Before ❌
```
上传 ZIP → 404 → 用户不知道为什么失败
上传 ZIP → FOREIGN KEY error → 安装失败
```

### After ✅
```
上传 ZIP → 立即显示进度 → FAILED + 清晰错误信息
用户："哦，ZIP 结构不对，我重新打包"
```

---

**立即执行**：`./apply_fix.sh` 🚀
