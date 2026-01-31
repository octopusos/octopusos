# E2E Landing Demo 实施进度报告

**日期**: 2026-01-25  
**状态**: 🟡 框架完成 70%，核心执行逻辑待补齐

---

## ✅ 已完成（不可抵赖证据的"骨架"）

### 1. 文档和规范

- ✅ `docs/demo/DEMO_LANDING_CHECKLIST.md` - 完整的 8 步验收标准
- ✅ `docs/demo/DEMO_LANDING_RUNBOOK.md` - Demo 运行和验证指南

### 2. 测试框架

- ✅ `tests/integration/test_executor_e2e_landing.py` - E2E 集成测试骨架
  - 创建临时 git repo
  - 构造 execution_request
  - 调用 ExecutorEngine
  - 验证 commits / 文件 / 审计日志

### 3. Gates 验证

- ✅ `scripts/gates/demo/g_ex_allowlist_strict.py` - Allowlist 严格检查
- ✅ `scripts/gates/demo/g_ex_no_shell.py` - 禁止 shell 调用检查
- ✅ `scripts/gates/demo/g_ex_audit_complete.py` - 审计完整性检查
- ✅ `scripts/gates/demo/g_ex_site_structure.py` - HTML 结构检查
- ✅ `scripts/gates/demo/run_demo_landing_gates.py` - Gates runner

### 4. Demo 运行脚本

- ✅ `scripts/demo/run_landing_demo.sh` - 一键运行脚本

### 5. 输入数据

- ✅ `examples/pipeline/nl/demo/nl_landing_page.txt` - Landing page 需求描述

---

## ❌ 关键缺口（无法产生"不可抵赖证据"）

### 问题 1: Executor 不真正执行文件操作

**当前状态**:
```python
# agentos/core/executor/executor_engine.py:120
# 5. 执行操作（简化版 - 只记录操作，不实际执行文件修改）
operations_executed = []
allowed_ops = execution_request.get("allowed_operations", [])
```

**影响**:
- ❌ 不会真正写 `index.html` / `style.css` / `README.md`
- ❌ 不会真正执行 `git commit`
- ❌ 无法产生 6 个真实的 commits
- ❌ 无法产生 diff 文件

**需要补齐**:
1. 实现 `write_file(path, content)` - 真正写文件
2. 实现 `git_commit(message)` - 真正提交
3. 实现 `update_file(path, content)` - 更新文件
4. 确保操作在 worktree 内执行

### 问题 2: execution_request 格式不匹配

**当前 Executor 期望**:
```python
execution_request.get("allowed_operations", [])
```

**测试提供的格式**:
```python
execution_request = {
    "patch_plan": {
        "steps": [
            {
                "operations": [...]  # 嵌套在 patch_plan.steps 下
            }
        ]
    }
}
```

**需要补齐**:
- 修改 Executor 以支持 `patch_plan.steps[].operations` 格式
- 或修改测试以匹配当前 Executor 的期望格式

### 问题 3: Allowlist 不支持 demo 所需的动作

**Demo 需要的动作**:
- `write_file`
- `update_file`
- `git_commit`
- `git_add`

**当前 Allowlist 支持**:
```python
# agentos/core/executor/allowlist.py
# 需要检查是否有这些动作
```

**需要补齐**:
- 确认或添加上述动作到 allowlist

---

## 🎯 最短收口路径（3 步）

你之前说的"最短 3 步收口"，我现在给你明确的实施计划：

### Step 1: 让 Executor 真正执行文件操作（最关键）

**文件**: `agentos/core/executor/executor_engine.py`

**需要添加的方法**:

```python
def _execute_write_file(self, op: Dict, worktree_path: Path):
    """执行 write_file 操作"""
    path = op["params"]["path"]
    content = op["params"]["content"]
    
    file_path = worktree_path / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    
    return {"path": str(path), "size": len(content)}

def _execute_git_commit(self, op: Dict, worktree_path: Path):
    """执行 git commit 操作"""
    message = op["params"]["message"]
    
    # git add -A
    subprocess.run(
        ["git", "add", "-A"],
        cwd=worktree_path,
        check=True,
        capture_output=True
    )
    
    # git commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        text=True
    )
    
    # 获取 commit hash
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()
    
    return {"commit_hash": commit_hash, "message": message}
```

**修改主执行循环**:

```python
# 当前 (Line 124):
for i, op in enumerate(allowed_ops):
    # ... 只记录，不执行

# 修改为:
for step in execution_request["patch_plan"]["steps"]:
    for op in step["operations"]:
        action = op["action"]
        
        # 真正执行
        if action == "write_file":
            result = self._execute_write_file(op, worktree_path)
        elif action == "update_file":
            result = self._execute_write_file(op, worktree_path)  # 同样逻辑
        elif action == "git_commit":
            result = self._execute_git_commit(op, worktree_path)
        else:
            raise ValueError(f"Unknown action: {action}")
```

### Step 2: 修正测试的断言

**文件**: `tests/integration/test_executor_e2e_landing.py`

**修改**:

```python
# Line 182:
# assert result["status"] == "completed"
assert result["status"] == "success"  # Executor 返回 "success"
```

### Step 3: 运行并产生证据

```bash
# 1. 运行测试
uv run pytest tests/integration/test_executor_e2e_landing.py -v -s

# 2. 验证产物
ls -la /tmp/agentos_demo_*/
git -C /tmp/agentos_demo_*/ log --oneline

# 3. 运行 Gates
python3 scripts/gates/demo/run_demo_landing_gates.py

# 4. 生成证据报告
# 包含:
# - git log 输出 (commit hashes)
# - run_tape.jsonl 摘要
# - Gates 通过截图
# - index.html 截图
```

---

## 📊 时间估算

| 步骤 | 预计时间 | 说明 |
|------|---------|------|
| Step 1: 真实文件操作 | 30 分钟 | 添加 _execute_* 方法 + 修改主循环 |
| Step 2: 修正测试 | 5 分钟 | 改 assert |
| Step 3: 运行验证 | 10 分钟 | 运行 + 收集证据 |
| **总计** | **~45 分钟** | 可产生不可抵赖证据 |

---

## 🚩 红旗警告（必须注意）

### 红旗 1: 当前 Executor 是"模拟"而非"真实"

你之前的 v0.12 总结声称"Executor 完成"，但实际上：
- ❌ 不执行真实文件操作
- ❌ 不提交真实 git commits
- ❌ run_tape.jsonl 存在，但不代表"真正执行"

这是你说的"空壳完成"的典型例子。

### 红旗 2: 没有一个"端到端运行成功"的证据

- ❌ 没有真实的 `index.html` 产出
- ❌ 没有真实的 git log 截图
- ❌ Gates 无法验证（因为没有真实产物）

### 红旗 3: 如果现在发朋友圈/LinkedIn

你会被问：
1. "能看看生成的网站吗？" → ❌ 无法展示
2. "git log 是什么样的？" → ❌ 没有真实 commits
3. "audit 日志在哪？" → ✅ 有，但内容是"假执行"

---

## ✅ 下一步行动（你决定）

**选项 A: 补齐真实执行（推荐）**

- 实施上面的 Step 1-3
- 时间: ~45 分钟
- 产出: 真实的不可抵赖证据
- 可以对外展示

**选项 B: 接受当前状态，明确标注**

- 文档中说明 "Executor 为 mock 实现"
- 不对外声称"生产可用"
- 用于概念验证（PoC）

**选项 C: 暂停，先完成其他 TODO**

- Phase 1 (TUI) 的 headless test
- Phase 3 (Tool Adapter) 的 mock 闭环
- 之后再回来补 Executor

---

## 我的建议

**立即做 选项 A（补齐真实执行）**

原因:
1. 这是你说的"最震撼的 demo"的核心
2. 只需 45 分钟就能从"空壳"变成"真实"
3. 产出的证据可以直接对外展示
4. 符合你自己的"不可抵赖证据"标准

---

**报告生成时间**: 2026-01-25  
**状态**: 🟡 等待决策 - 补齐真实执行 or 接受当前状态？
