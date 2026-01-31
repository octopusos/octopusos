# Phase Update Bug - Quick Fix Guide

## 问题

WebUI 中切换 execution phase 时出现 "Failed to update phase" 错误。

## 快速修复

### 已修复的文件

1. **`agentos/webui/api/sessions.py`**
   - 将 audit 日志改为"尽力而为"模式
   - Audit 失败不影响 phase 更新
   - 添加详细日志和错误信息

2. **`agentos/webui/static/js/components/PhaseSelector.js`**
   - 支持结构化错误响应
   - 改进错误信息展示

### 核心改动

**Before**:
```python
# Audit 失败会导致整个 API 失败
audit_id = emit_audit_event(...)
```

**After**:
```python
# Audit 失败只记录警告,不影响 API
audit_id = None
try:
    audit_id = emit_audit_event(...)
except Exception as audit_error:
    logger.warning(f"Failed to emit audit event: {audit_error}")
```

## 测试

### 后端测试
```bash
python3 test_phase_update.py
```

### API 测试 (需要先启动服务器)
```bash
# Terminal 1: 启动服务器
python3 -m agentos.webui.app

# Terminal 2: 运行测试
./test_phase_api.sh
```

### WebUI 测试
1. 访问 http://localhost:8000
2. 切换 Phase Selector
3. 验证成功提示

## 验证修复

**预期行为**:
- ✓ Phase 切换成功
- ✓ 显示成功提示: "Phase changed to: execution"
- ✓ 即使 audit 失败,phase 仍然更新
- ✓ Audit 失败时记录警告日志

**检查点**:
```bash
# 检查日志中的成功信息
grep "Updated execution_phase" logs/agentos.log

# 检查日志中的 audit 警告 (如果有)
grep "Failed to emit audit event" logs/agentos.log
```

## 回滚方案

如果修复引入新问题,回滚步骤:

```bash
# 恢复修改前的文件
git checkout HEAD~1 -- agentos/webui/api/sessions.py
git checkout HEAD~1 -- agentos/webui/static/js/components/PhaseSelector.js

# 重启服务
pkill -f "agentos.webui.app"
python3 -m agentos.webui.app
```

## 联系信息

如有问题,检查:
1. `PHASE_UPDATE_FIX_REPORT.md` - 详细修复报告
2. 日志文件: `logs/agentos.log`
3. 浏览器控制台错误

---
**修复日期**: 2026-01-31
**状态**: ✓ 已修复并测试
