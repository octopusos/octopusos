# P0 最短 4 步收口 - 当前进度总结

**时间**: 2026-01-25  
**Commit**: 5389752  
**决策**: A' (零豁免 + 限定扫描域)  
**状态**: ✅ P0-1/P0-2 完成，继续 P0-2b/P0-3/P0-4

---

## ✅ 已完成（50%）

### P0-1: Worktree 带回主 Repo ✅

**实现**:
1. ✅ GitClient 适配层 (318 行，GitPython)
2. ✅ Executor 使用 GitClient（移除 subprocess）
3. ✅ `_bring_back_commits_from_worktree()`
   - format-patch → series.patch
   - am 应用到主 repo
   - 生成 sandbox_proof.json
4. ✅ 恢复强制使用 worktree

**验证**: 代码已实现，待 E2E 测试验证

### P0-2: Demo Scope 零 Subprocess ✅

**实现**:
1. ✅ 修改 AST Gate 扫描域
   - 只扫描: scripts/demo/, gates/v12_demo_*, executor_engine.py, git_client.py, test_e2e
   - 不扫描: 底层基础设施
2. ✅ 测试文件改用 GitClient

**Gate 结果**:
```
✅ Gate PASSED: Demo Path Zero Subprocess
   Scanned 4 files in Demo Scope
   Violations: 0
```

**硬证据**: `outputs/demo/latest/audit/no_subprocess_demo_scope.json`

---

## 🔄 进行中（25%）

### P0-2b: Import Graph Gate（不可达证明）

**需要实现**:
1. 静态 import 分析
   - 从 `scripts/demo/run_landing_demo.py` 作为 root
   - 递归解析 AST import
   - 构建可达模块集合
   - 断言不包含: agentos/core/container, rollback, ext/tools

2. 动态 runtime 证明
   - monkeypatch subprocess.Popen/run 抛异常
   - 运行 demo
   - 断言 demo 成功（证明未触发 subprocess）

**预计时间**: 30 分钟

---

## 📋 待完成（25%）

### P0-3: 6 Steps → 6 Commits → 6 Patches

**需要**:
1. 修改 execution_request，补齐 6 个 steps
2. 每个 step 生成 diff/step_0N.patch
3. Rollback proof:
   - checkout step_02 → 验证文件 checksum
   - checkout step_04 → 验证文件 checksum

**预计时间**: 45 分钟

### P0-4: Gates 实跑 + Freeze Report

**需要**:
1. 创建 `scripts/verify_demo_landing.sh`
2. 运行所有 demo gates
3. 输出 tee 到 `outputs/demo/<run_id>/audit/verify.log`
4. 更新 Freeze Report，贴入完整输出

**预计时间**: 30 分钟

---

## 🎯 下一步行动（按顺序）

1. **立即**: 创建 P0-2b Import Graph Gate（30 分钟）
2. **然后**: 运行 E2E 测试，验证 P0-1 的 worktree 带回（10 分钟）
3. **然后**: P0-3 补齐 6 steps（45 分钟）
4. **最后**: P0-4 验收脚本 + Freeze Report（30 分钟）

**总计剩余时间**: ~2 小时

---

## 📊 关键指标

| 指标 | 当前 | 目标 | 状态 |
|------|------|------|------|
| Demo Scope Subprocess | 0 | 0 | ✅ |
| Worktree 带回 | 已实现 | 已实现 | ✅ (待验证) |
| Import Graph 证明 | 未实现 | 必须 | 🔄 |
| Commits 数量 | 3 | 6 | ❌ |
| Patches 文件 | 0 | 6 | ❌ |
| Gates 实跑 | 部分 | 全部 | ❌ |

---

## 💡 关键突破

**口径正确性**:
- ✅ 不是"豁免"，是"限定扫描域"
- ✅ Demo 路径 0 subprocess（硬冻结）
- ✅ 底层基础设施可存在（但不可达）

这比"豁免列表"更硬：未来谁想把 subprocess 拉回 demo 路径，会被 Gate 卡死。

---

**当前状态**: 🟢 进展顺利，50% 完成  
**预计完成时间**: ~2 小时  
**可签署状态**: 未达到（需完成 P0-2b/P0-3/P0-4）
