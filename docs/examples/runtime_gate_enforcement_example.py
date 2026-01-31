"""
示例：如何在 Orchestrator 的 publish/apply 流程中集成运行时 Gate 强制执行

这个文件展示了如何在实际代码中使用 GateEnforcer。
"""

from pathlib import Path
from agentos.core.gates import GateEnforcer
from agentos.core.policy.execution_policy import PolicyViolation


def example_publish_with_gate_enforcement(
    run_id: int,
    execution_mode: str,
    commit_sha: str | None,
    memory_pack: dict | None,
    artifacts_dir: Path,
    db_cursor,
):
    """
    示例：在 publish 前添加 Gate 强制执行
    
    这是 Orchestrator._run_publish() 应该做的事情。
    """
    
    # ========================================
    # 运行时 Gate 检查（最后防线）
    # ========================================
    try:
        GateEnforcer.pre_publish_gate_check(
            run_id=run_id,
            execution_mode=execution_mode,
            commit_sha=commit_sha,
            memory_pack=memory_pack,
            artifacts_dir=artifacts_dir,
            db_cursor=db_cursor,
            question_attempts=0  # 从 run metadata 或 context 中获取
        )
        
        # 记录 Gate 通过
        audit_event = GateEnforcer.create_audit_event(
            gate_name="Pre-Publish Gate Check",
            run_id=run_id,
            status="passed",
            violation_reason=None
        )
        
        # TODO: 将 audit_event 写入数据库或日志
        print(f"✅ Gate check passed for run {run_id}")
        
    except PolicyViolation as e:
        # 记录 Gate 失败
        audit_event = GateEnforcer.create_audit_event(
            gate_name="Pre-Publish Gate Check",
            run_id=run_id,
            status="failed",
            violation_reason=str(e)
        )
        
        # TODO: 将 audit_event 写入数据库
        
        # 更新 run 状态为 BLOCKED
        if db_cursor:
            db_cursor.execute(
                "UPDATE runs SET status = 'BLOCKED', error = ? WHERE id = ?",
                (str(e), run_id)
            )
        
        # 重新抛出异常，阻止发布
        raise
    
    # ========================================
    # 正常的 publish 逻辑
    # ========================================
    print(f"Publishing run {run_id}...")
    # ... 实际的 publish 代码 ...


def example_orchestrator_integration():
    """
    示例：完整的 Orchestrator 集成示例
    
    展示如何修改 Orchestrator._run_publish() 方法。
    """
    
    code_template = '''
    def _run_publish(self, project_id: str, agent_type: str):
        """Run publish phase (with runtime Gate enforcement)"""
        
        # 获取 run 信息
        db = get_db()
        cursor = db.cursor()
        
        # 查询最近的 run
        run = cursor.execute(
            "SELECT id, execution_mode, memory_pack FROM runs "
            "WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
            (project_id,)
        ).fetchone()
        
        if not run:
            raise ValueError(f"No run found for project {project_id}")
        
        run_id = run["id"]
        execution_mode = run.get("execution_mode", "semi_auto")
        memory_pack = json.loads(run["memory_pack"]) if run.get("memory_pack") else None
        
        # 查询 commit (如果有)
        commit = cursor.execute(
            "SELECT commit_sha FROM artifacts "
            "WHERE run_id = ? AND type = 'commit' LIMIT 1",
            (run_id,)
        ).fetchone()
        commit_sha = commit["commit_sha"] if commit else None
        
        # Artifacts 目录
        artifacts_dir = Path("artifacts") / project_id
        
        # ========================================
        # 运行时 Gate 强制执行（关键！）
        # ========================================
        try:
            from agentos.core.gates import GateEnforcer
            
            GateEnforcer.pre_publish_gate_check(
                run_id=run_id,
                execution_mode=execution_mode,
                commit_sha=commit_sha,
                memory_pack=memory_pack,
                artifacts_dir=artifacts_dir,
                db_cursor=cursor,
                question_attempts=0  # 从 run metadata 获取
            )
            
            console.print(f"    ✅ Runtime Gate check passed")
            
        except PolicyViolation as e:
            console.print(f"    ❌ [red]Gate violation: {e}[/red]")
            
            # 更新状态
            cursor.execute(
                "UPDATE runs SET status = 'BLOCKED', error = ? WHERE id = ?",
                (str(e), run_id)
            )
            db.commit()
            db.close()
            
            # 阻止发布
            raise
        
        # ========================================
        # 正常的 publish 逻辑
        # ========================================
        console.print(f"    📦 Published to artifacts/{project_id}/")
        
        db.close()
    '''
    
    print("Orchestrator Integration Template:")
    print("=" * 70)
    print(code_template)
    print("=" * 70)


if __name__ == "__main__":
    example_orchestrator_integration()
