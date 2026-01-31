# AgentOS v0.2 Invariants（不变量冻结）

**版本**: v0.2.0  
**状态**: 🔒 已冻结  
**日期**: 2026-01-25

## 目的

定义 AgentOS v0.2 的核心不变量（Invariants），v0.3 升级必须继续满足这些约束。

## 10 条护城河（v0.2）

以下约束在 v0.3 及后续版本中**不可削弱**：

### 1. 无 MemoryPack 不允许执行
```python
# 强制要求
assert memory_pack is not None, "MemoryPack required for execution"
assert memory_pack.get("memories") is not None  # 可以为空数组，但字段必须存在
```

### 2. full_auto question_budget = 0
```python
if execution_mode == "full_auto":
    assert execution_policy["question_budget"] == 0, "full_auto cannot ask questions"
```

### 3. 命令/路径禁止编造
```python
# 所有命令必须来自 FactPack 或 MemoryPack
assert command in factpack["commands"] or command in memory_pack["allowed_commands"]

# 所有路径必须来自 allowed_paths
assert all(path in allowed_paths for path in target_paths)
```

### 4. 每次执行必须写 run_steps
```python
# Plan/Apply/Verify 不可缺
required_steps = ["plan", "apply", "verify"]
recorded_steps = [step["step_type"] for step in run_steps]
assert all(step in recorded_steps for step in required_steps)
```

### 5. 每次执行必须有 review_pack.md
```python
# 执行完成后必须生成 ReviewPack
review_pack_path = artifacts_dir / f"review_pack_run_{run_id}.md"
assert review_pack_path.exists(), "ReviewPack required"
```

### 6. 每个 patch 必须记录 intent + files + diff_hash
```python
for patch in patches:
    assert "intent" in patch and patch["intent"], "Patch intent required"
    assert "files" in patch and len(patch["files"]) > 0, "Patch files required"
    assert "diff_hash" in patch and patch["diff_hash"], "Patch diff_hash required"
```

### 7. 每次发布必须绑定 commit hash
```python
if status == "publish":
    assert commit_links, "Commit binding required for publish"
    for link in commit_links:
        assert "commit_hash" in link and link["commit_hash"]
```

### 8. 文件锁冲突必须 WAIT 并 rebase
```python
if file_lock_conflict:
    assert status == "WAITING_LOCK", "Must wait on lock conflict"
    # 解锁后必须 rebase
    assert "rebase" in next_steps, "Rebase required after lock release"
```

### 9. 并发执行必须受 locks 限制
```python
# 不会同时修改同一文件
for task_a, task_b in concurrent_tasks:
    assert not (set(task_a.target_files) & set(task_b.target_files)), \
        "Concurrent tasks cannot modify same files"
```

### 10. scheduler 触发必须可审计
```python
# 所有 task_run 必须记录触发方式
assert task_run["triggered_by"] in ["cron", "manual", "dependency", "retry"]
```

## v0.3 扩展（新增约束，不削弱旧约束）

以下是 v0.3 新增的约束，与 v0.2 护城河共同构成完整防线：

### 11. Memory 必须有 retention_policy
```python
# v0.3 起所有 memory_item 必须定义生命周期
assert "retention_policy" in memory_item, "Retention policy required"
assert memory_item["retention_policy"]["type"] in ["temporary", "project", "permanent"]
```

### 12. 高风险 ReviewPack 必须人工批准
```python
# 基于风险评估自动判定
if review_pack["risk_assessment"]["overall_risk"] in ["high", "critical"]:
    assert review_level == ReviewLevel.APPROVAL_REQUIRED, \
        "High risk requires approval"
```

### 13. Rebase 必须验证 intent 一致性
```python
# 文件变更后必须检查原 intent 是否仍成立
if rebase_triggered:
    assert intent_validator.validate(original_intent, changed_files), \
        "Intent must remain valid after rebase"
```

### 14. Policy 组合必须在预设范围内
```python
# 禁止任意组合，只允许预设
combination = (execution_mode, risk_profile, scheduling)
assert combination in POLICY_PRESETS, \
    "Policy combination must be predefined"
```

### 15. 自愈动作必须白名单
```python
# v0.3 自愈机制只能执行预定义动作
assert healing_action in HEALING_ACTIONS_WHITELIST, \
    "Healing action must be whitelisted"
```

### 16. Learning 先提案后应用
```python
# 学习产出必须先生成 LearningPack
assert learning_pack is not None, "LearningPack required before apply"

# 应用必须可回滚
if apply_learning:
    assert rollback_plan is not None, "Rollback plan required"
```

### 17. Policy 演化必须 canary
```python
# 新 policy 必须先 canary 验证
if policy_changed:
    assert policy["status"] == "canary", "New policy must start as canary"
    assert policy["applied_to"]["project_ids"], "Canary scope required"
```

### 18. RunTape 必须可重放
```python
# 所有 run 必须记录完整 tape
assert run_tape is not None, "RunTape required"
assert run_tape["steps"], "RunTape steps required"

# 必须支持 dry-run replay
assert replay_validator.can_replay(run_tape, dry_run=True)
```

## 验证机制

### 单元测试
```bash
# 所有护城河都有对应测试
pytest tests/test_invariants.py -v
```

### 集成测试
```bash
# 端到端验证
pytest tests/integration/test_v03_invariants.py -v
```

### CI 强制检查
```yaml
# .github/workflows/ci.yml
- name: Verify v0.2 Invariants
  run: |
    pytest tests/test_invariants.py --strict
    # 任何失败立即阻止 merge
```

## 破坏检测

如果 PR 破坏了任一不变量，CI 将：
1. 标记为 ❌ BLOCKED
2. 自动评论指出违反的约束
3. 要求架构团队审查

## 版本兼容性

- v0.3 必须满足所有 v0.2 护城河（1-10）
- v0.3 新增护城河（11-18）不影响 v0.2 兼容性
- 未来版本只能**增加**约束，不能**削弱**现有约束

---

**维护**: 架构团队  
**审查周期**: 每个大版本升级前  
**状态**: 🔒 已冻结，不可修改
