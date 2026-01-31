# AgentOS 任务产物展示功能 - 使用指南

**版本**: 1.0  
**更新日期**: 2026-01-27  
**状态**: ✅ 已完成并验证

---

## 功能概述

任务执行产物展示功能已成功实现，解决了"任务 succeeded 但看不到结果"的问题。现在你可以在 TUI 任务详情页直观地查看：

- ✅ 执行产物列表（Artifacts Tab）
- ✅ 执行日志和结果摘要（Output Tab）
- ✅ 产物文件内容查看器
- ✅ 自动生成的 Session ID

---

## 快速开始

### 1. 启动 TUI

```bash
cd /Users/pangge/PycharmProjects/AgentOS
PYTHONPATH=$PWD python3 -m agentos.ui.main_tui tasks
```

### 2. 查看测试任务

已有2个测试任务包含完整产物：

**任务 1**: `0bec228a-6a36-446f-b776-ee2b303f0206`
- 2 个 artifacts（open_plan.json, execution_result.json）
- 2 个 commits
- 完整的执行日志

**任务 2**: `7fd85f7c-45d1-4250-a9af-303d57b1c3b6`
- 2 个 artifacts
- 2 个 commits
- 完整的执行日志

### 3. 在 TUI 中操作

1. 在任务列表中，找到测试任务（按任务 ID 前8位识别：`0bec228a` 或 `7fd85f7c`）
2. 按 `Enter` 进入任务详情页
3. 你会看到 **5个 Tab**：
   - Timeline（时间线）
   - Audits（审计日志）
   - Agents（Agent 执行记录）
   - **Artifacts**（新增：产物列表）✨
   - **Output**（新增：执行输出）✨

4. 切换到 **Artifacts Tab**：
   - 查看所有产物（类型、路径、大小、创建时间）
   - 点击任意行查看产物内容

5. 切换到 **Output Tab**：
   - 查看执行日志
   - 查看结果摘要
   - 查看 commits 列表

---

## 功能详解

### Artifacts Tab

**显示内容**：
- Artifact Type（产物类型）：open_plan, execution_result
- Path（路径）：相对路径或绝对路径
- Size（大小）：文件大小（KB）
- Created（创建时间）：生成时间

**交互**：
- 点击任意行 → 自动切换到 Output Tab 并显示文件内容

**支持格式**：
- ✅ JSON（自动格式化）
- ✅ JSONL（逐行解析）
- ✅ TXT/MD（纯文本）
- ✅ LOG（日志文件）

### Output Tab

**显示内容**：
1. **执行日志**：
   - 从 task_audits 表加载
   - 按时间排序
   - 按级别着色（ERROR/WARN/INFO）

2. **执行结果**：
   - 从 execution_result.json 加载
   - 显示状态、操作数、摘要

3. **Commits 列表**：
   - 从 task_lineage 查询 kind="commit"
   - 显示 commit hash（前12位）

---

## 历史任务兼容性

### 旧任务（无产物）

**症状**：
- Artifacts Tab 显示 "No artifacts yet"
- Output Tab 只有审计日志，没有执行结果

**原因**：
- 该任务运行于旧版本 Runner（模拟执行）
- 当时 executing 阶段只是 `sleep 3`，未生成产物

**解决方案**（未来实现）：
- 在空态时显示提示："该任务运行于旧版本 Runner（模拟执行），未记录产物。建议重新运行任务以生成 artifacts。"
- 提供 "Re-run with real pipeline" 按钮

### 新任务（有产物）

**条件**：
- 使用 `--real-pipeline` flag 启动的任务
- 或通过新版 TaskRunner 执行的任务

**效果**：
- 完整的 artifacts 记录
- execution_result.json
- commits（如果有代码变更）

---

## 验证清单

运行验证脚本确认功能正常：

```bash
cd /Users/pangge/PycharmProjects/AgentOS
python3 verify_artifacts_feature.py
```

**预期输出**：
```
✅ Method exists: load_artifacts_list
✅ Method exists: load_output
✅ Method exists: action_view_artifact
✅ Artifacts Tab found in compose()
✅ Output Tab found in compose()
✅ executing 分支包含真实执行逻辑
✅ execution_result.json exists
✅ 所有验证通过
```

---

## 技术实现

### 代码变更

**修改文件**（3个）：
1. `agentos/core/runner/task_runner.py` (+197 行)
   - 新增4个方法：_load_open_plan_artifact, _record_execution_artifacts, _execute_with_coordinator, _extract_execution_result
   - 修改 executing 分支：use_real_pipeline 时真实执行

2. `agentos/ui/screens/inspect.py` (+267 行)
   - 新增2个 Tab：Artifacts, Output
   - 新增3个方法：load_artifacts_list, load_output, action_view_artifact
   - 增强交互：点击 artifacts 表格查看内容

3. `agentos/core/task/manager.py` (+21 行)
   - session_id 自动生成：`auto_{task_id[:8]}_{timestamp}`
   - metadata 添加 execution_context

**修复文件**（1个）：
4. `agentos/core/task/manager_extended.py` (SQL修复)
   - 将列名 `timestamp` 改为 `created_at`

### Git Commits

```
689d3d1 docs: 添加任务执行产物展示功能完成报告和测试
a6cf825 fix(task-audits): 修正 task_audits 查询的列名
c90d635 feat(task-execution): 实现真实任务执行和产物展示
```

### 数据流

```
Planning → open_plan.json (artifact) → Approval → 
Executing → executor → execution_result.json (artifact) → 
commits (lineage) → UI 展示（Artifacts/Output Tab）
```

---

## 常见问题

### Q1: 为什么我看不到新 Tab？

**A**: 可能的原因：
1. TUI 未使用最新代码 → 确保 `PYTHONPATH` 指向工作区
2. 数据库需要迁移 → 在 TUI 启动时选择 "Yes" 迁移数据库
3. CSS 缓存问题 → 重启 TUI

**验证方法**：
```bash
python3 -c "import agentos.ui.screens.inspect as m; print(m.__file__)"
# 应该输出：/Users/pangge/PycharmProjects/AgentOS/agentos/ui/screens/inspect.py
```

### Q2: Artifacts Tab 是空的？

**A**: 可能的原因：
1. 该任务是旧任务（模拟执行） → 正常，重新运行任务
2. 任务还在执行中 → 等待任务完成
3. lineage 未记录 → 检查任务 Timeline

### Q3: 如何创建带产物的新任务？

**A**: 使用 `--real-pipeline` flag：
```bash
python3 -m agentos.cli.main task create \
  --nl "实现一个 python helloworld 脚本" \
  --mode assisted \
  --real-pipeline
```

### Q4: Output Tab 显示什么？

**A**: 按顺序显示：
1. 执行日志（task_audits）
2. 执行结果摘要（execution_result.json）
3. Commits 列表（如果有）

---

## 下一步优化

### 短期（已规划）
1. 空态提示："旧任务无产物，建议重新运行"
2. Re-run 按钮：一键用 real_pipeline 重新执行
3. Artifacts 下载：打包下载整个 execution 目录

### 中期
4. 实时日志流：WebSocket 推送 run_tape 事件
5. Diff 展示：显示代码变更 diff
6. Pipeline 可视化：流程图展示 mode pipeline

### 长期
7. Artifacts 预览增强：Markdown 渲染、图片预览
8. 搜索和过滤：按类型、时间过滤产物
9. 导出功能：导出任务报告（PDF/HTML）

---

## 总结

任务执行产物展示功能已完全实现并验证通过：

- ✅ 代码已落地（3个 commits）
- ✅ 功能已验证（verify_artifacts_feature.py 通过）
- ✅ TUI 可启动（数据库迁移后即可使用）
- ✅ 测试任务有完整产物

**用户价值**：
- 不再需要手动 `find` 查找产物
- 可视化查看执行结果和日志
- 点击即可查看产物内容
- 完整的任务可追溯性

**开发者价值**：
- 清晰的产物存储结构
- 完整的 lineage 记录
- 易于扩展的 artifact 查看器
- 良好的向后兼容性

---

**文档维护者**: AI Agent  
**联系方式**: 见 README.md  
**许可证**: 与项目相同
