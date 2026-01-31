# Demo Runbook: Landing Page E2E

**目标**: 一键运行 AgentOS Executor 在空目录创建 Landing Page，产出不可抵赖证据。

---

## 🚀 快速开始

### 方式 1: 一键脚本（推荐）

```bash
cd /path/to/AgentOS
./scripts/demo/run_landing_demo.sh
```

### 方式 2: 手动步骤

```bash
# 1. 运行 E2E 测试
uv run pytest tests/integration/test_executor_e2e_landing.py -v -s

# 2. 运行 Gates 验证
python3 scripts/gates/demo/run_demo_landing_gates.py
```

---

## 📋 Demo 流程说明

### 输入

- **NL 需求**: `examples/pipeline/nl/demo/nl_landing_page.txt`
- **空目录**: 临时创建的 git repo

### 执行步骤

1. **Executor 启动**: 读取 execution_request
2. **创建 Sandbox**: 在 worktree 隔离执行
3. **执行 6 个 Steps**:
   - Step 1: 初始化骨架（HTML + CSS + README）
   - Step 2: 添加 Hero section
   - Step 3: 添加 Features section
   - Step 4: 添加 Architecture section
   - Step 5: 添加 Use cases section
   - Step 6: 添加 Footer 并收尾
4. **每步产生 Commit**: 清晰的 git 历史
5. **审计记录**: 完整的 `run_tape.jsonl`

### 输出

- **Landing Site**: 完整的 HTML/CSS 网站
- **Git 历史**: 6+ commits（含初始 commit）
- **审计日志**: `outputs/demo_landing_001/run_tape.jsonl`
- **Diff 文件**: `outputs/demo_landing_001/diffs/*.patch`

---

## 🔍 验证 Demo 成功

### 1. 检查文件生成

```bash
ls -la demo_output/landing_site_*/
# 应看到:
# - index.html
# - style.css
# - README.md
# - .git/
```

### 2. 检查 Git 历史

```bash
cd demo_output/landing_site_*/
git log --oneline
# 应看到 6-7 个 commits:
# - chore: init landing skeleton
# - feat: add hero section
# - feat: add features section
# ...
```

### 3. 检查审计日志

```bash
cat outputs/demo_landing_001/run_tape.jsonl | jq .
# 每一步都应有 operation_start 和 operation_end
```

### 4. 运行 Gates

```bash
python3 scripts/gates/demo/run_demo_landing_gates.py
# 应输出: All Gates PASSED (exit code 0)
```

---

## 🎯 演示亮点（对外展示用）

### 亮点 1: 受控执行

✅ 所有动作在 **allowlist** 内  
✅ 无 shell/subprocess 调用  
✅ 在隔离 sandbox 执行

### 亮点 2: 完整审计

✅ 每步都有 **start/end** 事件  
✅ 输入/输出有 **hash** 追踪  
✅ 可机器验证（Gates 100% 通过）

### 亮点 3: 可回滚

✅ 6 个清晰的 commits  
✅ 任意时刻可 `git reset --hard`  
✅ 回滚后文件状态可验证

---

## 🛠️ 故障排查

### 问题 1: 测试失败 - "Executor not found"

**原因**: 未安装依赖

**解决**:
```bash
uv sync
uv run pytest tests/integration/test_executor_e2e_landing.py -v
```

### 问题 2: Gates 失败 - "run_tape.jsonl not found"

**原因**: Executor 未实际执行

**解决**:
1. 检查测试是否真的运行成功
2. 检查 `outputs/` 目录是否有输出

### 问题 3: HTML 结构检查失败

**原因**: 生成的 HTML 缺少必需的 sections

**解决**:
1. 检查 `index.html` 内容
2. 确保有 5 个 `<section id="...">` 标签

---

## 📊 性能基准

**典型执行时间** (MacBook Pro M1):
- Executor 执行: ~5-10 秒
- Gates 验证: ~1 秒
- 总计: **~10 秒**

**资源占用**:
- 磁盘: < 200KB（HTML + CSS + 审计日志）
- 内存: < 100MB

---

## 🎬 录制 Demo 视频

### 推荐录制流程

1. **开场**: 展示空目录
   ```bash
   ls -la demo_output/landing_site_*/
   # (空)
   ```

2. **运行**: 一键执行
   ```bash
   ./scripts/demo/run_landing_demo.sh
   ```

3. **验证**: 展示产物
   ```bash
   # 1. 查看网站
   open demo_output/landing_site_*/index.html
   
   # 2. 查看 git 历史
   cd demo_output/landing_site_*/
   git log --oneline --graph
   
   # 3. 查看审计
   cat outputs/demo_landing_001/run_tape.jsonl | head -20
   ```

4. **Gates**: 验证通过
   ```bash
   python3 scripts/gates/demo/run_demo_landing_gates.py
   # 🎉 All Gates PASSED
   ```

5. **回滚**: 演示时间旅行
   ```bash
   git reset --hard HEAD~3
   ls -la  # 文件回到第 3 步
   ```

---

## 📚 相关文档

- [Demo Checklist](DEMO_LANDING_CHECKLIST.md) - 完整验收标准
- [Executor 架构](../../docs/architecture/EXECUTOR_PARALLEL.md) - 并行执行设计
- [Gates 说明](../gates/demo/README.md) - Demo Gates 详解

---

**最后更新**: 2026-01-25  
**维护者**: AgentOS Team  
**状态**: ✅ Ready for Demo
