"""Task Runner: Background task execution engine

This module provides the background runner that executes tasks.
It runs as a subprocess and communicates with the CLI through the database.

P1: Integrated with real ModePipelineRunner for production execution.
PR-3: Integrated with Router for route verification and failover.
"""

import time
import logging
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from agentos.core.task import TaskManager, Task, RunMode
from agentos.core.task.run_mode import TaskMetadata
from agentos.core.gates.pause_gate import (
    can_pause_at,
    PauseCheckpoint,
    create_pause_metadata,
    PauseGateViolation
)
from agentos.core.mode.pipeline_runner import ModePipelineRunner
from agentos.core.mode.mode_selector import ModeSelection
from agentos.router import Router, RoutePlan, RerouteReason

logger = logging.getLogger(__name__)


class TaskRunner:
    """Background task runner (subprocess-based)
    
    This runner executes tasks in the background and updates their status
    in the database. The CLI monitors the status for progress updates.
    
    P1: Uses real ModePipelineRunner for production execution.
    """
    
    def __init__(
        self,
        task_manager: Optional[TaskManager] = None,
        repo_path: Optional[Path] = None,
        policy_path: Optional[Path] = None,
        use_real_pipeline: bool = False,
        router: Optional[Router] = None,
    ):
        """Initialize task runner

        Args:
            task_manager: TaskManager instance
            repo_path: Repository path for pipeline execution
            policy_path: Sandbox policy path
            use_real_pipeline: If True, use ModePipelineRunner; if False, use simulation
            router: Router instance for route verification (PR-3)
        """
        self.task_manager = task_manager or TaskManager()
        self.repo_path = repo_path or Path(".")
        self.policy_path = policy_path
        self.use_real_pipeline = use_real_pipeline
        self.router = router or Router(task_manager=self.task_manager)

        if self.use_real_pipeline:
            self.pipeline_runner = ModePipelineRunner()
            logger.info("TaskRunner initialized with real ModePipelineRunner")
        else:
            self.pipeline_runner = None
            logger.info("TaskRunner initialized in simulation mode")
    
    def run_task(self, task_id: str, max_iterations: int = 100):
        """Run a task in the background

        Args:
            task_id: Task ID to run
            max_iterations: Maximum number of state transitions (safety)
        """
        import os

        logger.info(f"Starting task runner for task {task_id}")

        # P0-3: Record runner spawn in lineage
        # Include timestamp to ensure uniqueness when multiple runners in same process
        import time
        run_id = f"runner_{task_id}_{os.getpid()}_{int(time.time() * 1000)}"
        try:
            self.task_manager.add_lineage(
                task_id=task_id,
                kind="runner_spawn",
                ref_id=run_id,
                phase="execution",
                metadata={"pid": os.getpid(), "max_iterations": max_iterations}
            )
        except Exception as e:
            logger.error(f"Failed to record runner spawn: {e}")

        # PR-3: Verify or reroute before execution starts
        route_plan = None
        try:
            route_plan = self._load_route_plan(task_id)
            if route_plan:
                logger.info(f"Loaded route plan for task {task_id}: selected={route_plan.selected}")
                # Verify route and reroute if needed
                import asyncio
                route_plan, reroute_event = asyncio.run(
                    self.router.verify_or_reroute(task_id, route_plan)
                )

                if reroute_event:
                    logger.warning(
                        f"Task {task_id} rerouted: {reroute_event.from_instance} -> {reroute_event.to_instance}"
                    )
                    # Save updated route plan
                    self._save_route_plan(task_id, route_plan)

                    # Log reroute event
                    self._log_audit(
                        task_id, "warn",
                        f"TASK_REROUTED: {reroute_event.from_instance} -> {reroute_event.to_instance} "
                        f"(reason: {reroute_event.reason_code.value})"
                    )
                else:
                    logger.info(f"Route verified for task {task_id}: {route_plan.selected}")
                    self._log_audit(task_id, "info", f"TASK_ROUTE_VERIFIED: {route_plan.selected}")
            else:
                logger.warning(f"No route plan found for task {task_id}, will execute without routing")
        except RuntimeError as e:
            logger.error(f"Route verification failed: {e}")
            self._log_audit(task_id, "error", f"Route verification failed: {str(e)}")
            # Mark task as BLOCKED
            self.task_manager.update_task_status(task_id, "failed")
            return
        except Exception as e:
            logger.error(f"Unexpected error during route verification: {e}", exc_info=True)
            # Continue execution despite routing error
            self._log_audit(task_id, "warn", f"Route verification error (continuing): {str(e)}")

        iteration = 0
        exit_reason = "unknown"
        
        try:
            while iteration < max_iterations:
                iteration += 1
                
                # 1. Load task from DB
                try:
                    task = self.task_manager.get_task(task_id)
                except Exception as e:
                    logger.error(f"Failed to load task {task_id}: {e}")
                    exit_reason = f"task_load_error: {e}"
                    break
                
                # 2. Check if task is in terminal state
                if task.status in ["succeeded", "failed", "canceled"]:
                    logger.info(f"Task {task_id} is in terminal state: {task.status}")
                    exit_reason = f"terminal_state: {task.status}"
                    break
                
                # 3. Execute current stage
                try:
                    next_status = self._execute_stage(task)
                    
                    # 4. Update task status
                    if next_status != task.status:
                        self.task_manager.update_task_status(task_id, next_status)
                        logger.info(f"Task {task_id} status: {task.status} -> {next_status}")
                    
                    # 5. Check if waiting for approval
                    if next_status == "awaiting_approval":
                        logger.info(f"Task {task_id} awaiting approval, pausing runner")
                        self._log_audit(task_id, "info", "Task paused for approval")
                        exit_reason = "awaiting_approval"
                        break
                    
                    # Small delay between iterations
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
                    self.task_manager.update_task_status(task_id, "failed")
                    self._log_audit(task_id, "error", f"Task failed: {str(e)}")
                    exit_reason = f"execution_error: {e}"
                    break
            
            if iteration >= max_iterations:
                logger.warning(f"Task {task_id} exceeded max iterations")
                self._log_audit(task_id, "warn", "Task exceeded max iterations")
                exit_reason = "max_iterations_exceeded"
        
        finally:
            # P0-3: Record runner exit in lineage
            try:
                self.task_manager.add_lineage(
                    task_id=task_id,
                    kind="runner_exit",
                    ref_id=run_id,
                    phase="execution",
                    metadata={
                        "pid": os.getpid(),
                        "exit_reason": exit_reason,
                        "iterations": iteration
                    }
                )
            except Exception as e:
                logger.error(f"Failed to record runner exit: {e}")
    
    def _execute_stage(self, task: Task) -> str:
        """Execute current stage and return next status
        
        This is a simplified pipeline that demonstrates the state machine.
        In production, this would call the actual coordinator/executor.
        
        Args:
            task: Task to execute
            
        Returns:
            Next status string
        """
        current_status = task.status
        metadata = TaskMetadata.from_dict(task.metadata)
        
        # State machine transitions
        if current_status == "created":
            # Start intent processing
            self._log_audit(task.task_id, "info", "Starting intent processing")
            return "intent_processing"
        
        elif current_status == "intent_processing":
            # Simulate intent processing
            self._log_audit(task.task_id, "info", "Processing intent")
            time.sleep(1)  # Simulate work
            return "planning"
        
        elif current_status == "planning":
            # P1: Planning stage - Use real pipeline if enabled
            self._log_audit(task.task_id, "info", "Generating execution plan")
            
            if self.use_real_pipeline:
                # Use real ModePipelineRunner
                try:
                    nl_request = metadata.nl_request or "Execute task"
                    
                    # Create mode selection for planning stage
                    mode_selection = ModeSelection(
                        primary_mode="experimental_open_plan",
                        pipeline=["experimental_open_plan"],
                        reason="Task runner planning stage"
                    )
                    
                    self._log_audit(task.task_id, "info", "Running real pipeline with open_plan mode")
                    
                    # Run real pipeline (this will generate open_plan)
                    pipeline_result = self.pipeline_runner.run_pipeline(
                        mode_selection=mode_selection,
                        nl_input=nl_request,
                        repo_path=self.repo_path,
                        policy_path=self.policy_path,
                        task_id=task.task_id
                    )
                    
                    # Check pipeline result
                    if pipeline_result.overall_status != "success":
                        self._log_audit(task.task_id, "error", f"Pipeline failed: {pipeline_result.summary}")
                        return "failed"
                    
                    self._log_audit(task.task_id, "info", f"Pipeline completed: {pipeline_result.summary}")
                    
                    # P2-C1: Save open_plan proposal as artifact
                    self._save_open_plan_artifact(task.task_id, pipeline_result)
                    
                except Exception as e:
                    logger.error(f"Pipeline execution failed: {e}", exc_info=True)
                    self._log_audit(task.task_id, "error", f"Pipeline error: {str(e)}")
                    return "failed"
            else:
                # Simulation mode
                time.sleep(2)
            
            # RED LINE (P0-2): Pause can ONLY happen at open_plan checkpoint
            run_mode_str = metadata.run_mode.value
            checkpoint = PauseCheckpoint.OPEN_PLAN.value
            
            # Check if we should pause at open_plan
            try:
                if can_pause_at(checkpoint, run_mode_str):
                    self._log_audit(task.task_id, "info", "Plan generated, awaiting approval at open_plan checkpoint")
                    
                    # P1: Record pause checkpoint in lineage (for auditability)
                    self.task_manager.add_lineage(
                        task_id=task.task_id,
                        kind="pause_checkpoint",
                        ref_id="open_plan",
                        phase="awaiting_approval",
                        metadata={
                            "checkpoint": checkpoint,
                            "reason": "Awaiting approval for open_plan",
                            "run_mode": run_mode_str
                        }
                    )
                    
                    return "awaiting_approval"
                else:
                    return "executing"
            except PauseGateViolation as e:
                # RED LINE: If pause checkpoint is invalid, fail the task
                logger.error(f"Pause gate violation: {e}")
                self._log_audit(task.task_id, "error", f"Pause gate violation: {str(e)}")
                return "failed"
        
        elif current_status == "executing":
            # Execute the plan
            self._log_audit(task.task_id, "info", "Executing plan")
            
            if self.use_real_pipeline:
                try:
                    # 1. Load open_plan artifact
                    plan_artifact = self._load_open_plan_artifact(task.task_id)
                    if not plan_artifact:
                        logger.warning(f"No open_plan artifact found for task {task.task_id}, proceeding anyway")
                    
                    # 2. Call real executor/coordinator
                    execution_result = self._execute_with_coordinator(task, plan_artifact)
                    
                    # 3. Record execution_request/commit/artifact lineage
                    self._record_execution_artifacts(task.task_id, execution_result)
                    
                    self._log_audit(task.task_id, "info", "Execution completed successfully")
                    return "succeeded"
                except Exception as e:
                    logger.error(f"Execution failed: {e}", exc_info=True)
                    self._log_audit(task.task_id, "error", f"Execution error: {str(e)}")
                    return "failed"
            else:
                # Simulation mode - keep original behavior
                time.sleep(3)
                self._log_audit(task.task_id, "info", "Execution completed (simulated)")
                return "succeeded"
        
        else:
            # Unknown status, keep as-is
            logger.warning(f"Unknown status: {current_status}")
            return current_status
    
    def _log_audit(self, task_id: str, level: str, message: str):
        """Log audit entry"""
        try:
            self.task_manager.add_audit(
                task_id=task_id,
                event_type=message,  # Use message as event_type
                level=level,
                payload={"message": message, "component": "task_runner"}
            )
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")
    
    def _save_open_plan_artifact(self, task_id: str, pipeline_result: Any):
        """Save open_plan proposal as artifact file
        
        P2-C1: Store open_plan proposal in a stable location and record in lineage.
        
        Args:
            task_id: Task ID
            pipeline_result: Pipeline execution result
        """
        try:
            # Create artifacts directory
            artifacts_dir = Path("store/artifacts") / task_id
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare artifact data
            artifact_data = {
                "task_id": task_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_status": pipeline_result.overall_status,
                "pipeline_summary": pipeline_result.summary,
                "stages": []
            }
            
            # Extract stage results if available
            if hasattr(pipeline_result, 'stage_results') and pipeline_result.stage_results:
                for stage_name, stage_result in pipeline_result.stage_results.items():
                    stage_data = {
                        "stage": stage_name,
                        "status": getattr(stage_result, 'status', 'unknown'),
                        "summary": getattr(stage_result, 'summary', ''),
                    }
                    
                    # Include outputs if available
                    if hasattr(stage_result, 'outputs'):
                        stage_data["outputs"] = stage_result.outputs
                    
                    artifact_data["stages"].append(stage_data)
            
            # Save to file
            artifact_path = artifacts_dir / "open_plan.json"
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(artifact_data, f, indent=2, ensure_ascii=False)
            
            # Get relative path for lineage
            relative_path = f"artifacts/{task_id}/open_plan.json"
            
            # P2-C1: Record artifact in lineage
            self.task_manager.add_lineage(
                task_id=task_id,
                kind="artifact",
                ref_id=relative_path,
                phase="awaiting_approval",
                metadata={
                    "artifact_kind": "open_plan",
                    "artifact_path": str(artifact_path),
                    "file_size": artifact_path.stat().st_size,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            )
            
            self._log_audit(task_id, "info", f"Open plan artifact saved: {relative_path}")
            logger.info(f"Saved open_plan artifact: {artifact_path}")
            
        except Exception as e:
            logger.error(f"Failed to save open_plan artifact: {e}", exc_info=True)
            self._log_audit(task_id, "warn", f"Failed to save open_plan artifact: {str(e)}")
            # Don't fail the task if artifact save fails (non-critical)
    
    def _load_open_plan_artifact(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load open_plan artifact from store
        
        Args:
            task_id: Task ID
            
        Returns:
            Artifact data dict or None if not found
        """
        try:
            artifact_path = Path("store/artifacts") / task_id / "open_plan.json"
            if not artifact_path.exists():
                logger.warning(f"Open plan artifact not found: {artifact_path}")
                return None
            
            with open(artifact_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load open_plan artifact: {e}", exc_info=True)
            return None
    
    def _record_execution_artifacts(self, task_id: str, execution_result: Dict[str, Any]):
        """Record execution artifacts to lineage
        
        Args:
            task_id: Task ID
            execution_result: Execution result from pipeline/executor
        """
        try:
            # Extract execution_request_id
            exec_req_id = execution_result.get("execution_request_id") or execution_result.get("execution_result_id")
            if exec_req_id:
                # Record execution_request lineage
                self.task_manager.add_lineage(
                    task_id=task_id,
                    kind="execution_request",
                    ref_id=exec_req_id,
                    phase="execution",
                    metadata={"execution_status": execution_result.get("status", "unknown")}
                )
            
            # Record execution_result.json artifact
            result_path = execution_result.get("result_path")
            if result_path:
                file_path = Path(result_path)
                self.task_manager.add_lineage(
                    task_id=task_id,
                    kind="artifact",
                    ref_id=str(result_path),
                    phase="execution",
                    metadata={
                        "artifact_kind": "execution_result",
                        "artifact_path": str(result_path),
                        "file_size": file_path.stat().st_size if file_path.exists() else 0,
                        "generated_at": datetime.now(timezone.utc).isoformat()
                    }
                )
            
            # Record commits if any
            commits = execution_result.get("commits_brought_back", [])
            for commit_hash in commits:
                self.task_manager.add_lineage(
                    task_id=task_id,
                    kind="commit",
                    ref_id=commit_hash,
                    phase="execution",
                    metadata={"commit_hash": commit_hash}
                )
            
            logger.info(f"Recorded execution artifacts for task {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to record execution artifacts: {e}", exc_info=True)
            self._log_audit(task_id, "warn", f"Failed to record execution artifacts: {str(e)}")
    
    def _execute_with_coordinator(self, task: Task, plan_artifact: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute task using coordinator/executor pipeline
        
        This method runs the real implementation pipeline (e.g., experimental_open_implement)
        to execute the approved plan.
        
        Args:
            task: Task object
            plan_artifact: Loaded open_plan artifact (can be None)
            
        Returns:
            Execution result dict with keys:
                - execution_request_id: Execution request ID
                - status: Execution status (success/failed)
                - result_path: Path to execution_result.json
                - commits_brought_back: List of commit hashes
                
        Raises:
            Exception: If execution fails
        """
        metadata = TaskMetadata.from_dict(task.metadata)
        nl_request = metadata.nl_request or "Execute task"
        
        # Create mode selection for implementation stage
        mode_selection = ModeSelection(
            primary_mode="experimental_open_implement",
            pipeline=["experimental_open_implement"],
            reason="Task runner execution stage"
        )
        
        self._log_audit(task.task_id, "info", "Running implementation pipeline")
        
        # Run real pipeline (this will call executor)
        pipeline_result = self.pipeline_runner.run_pipeline(
            mode_selection=mode_selection,
            nl_input=nl_request,
            repo_path=self.repo_path,
            policy_path=self.policy_path,
            task_id=task.task_id
        )
        
        # Check pipeline result
        if pipeline_result.overall_status != "success":
            error_msg = f"Implementation pipeline failed: {pipeline_result.summary}"
            self._log_audit(task.task_id, "error", error_msg)
            raise Exception(error_msg)
        
        self._log_audit(task.task_id, "info", f"Implementation pipeline completed: {pipeline_result.summary}")
        
        # Extract execution result from pipeline stages
        execution_result = self._extract_execution_result(pipeline_result)
        
        return execution_result
    
    def _extract_execution_result(self, pipeline_result) -> Dict[str, Any]:
        """Extract execution result from pipeline result

        Args:
            pipeline_result: PipelineResult from ModePipelineRunner

        Returns:
            Simplified execution result dict
        """
        result = {
            "execution_request_id": pipeline_result.pipeline_id,
            "status": pipeline_result.overall_status,
            "commits_brought_back": [],
            "result_path": None
        }

        # Try to extract from stage outputs
        if hasattr(pipeline_result, 'stages') and pipeline_result.stages:
            for stage in pipeline_result.stages:
                stage_output = stage.output

                # Look for executor output
                if "execution_result_id" in stage_output:
                    result["execution_result_id"] = stage_output["execution_result_id"]

                # Look for commits
                if "commits_brought_back" in stage_output:
                    result["commits_brought_back"].extend(stage_output["commits_brought_back"])

                # Look for result file path
                if "result_file" in stage_output:
                    result["result_path"] = stage_output["result_file"]

        # If no result_path found, construct from pipeline_id
        if not result["result_path"]:
            # Construct path based on pipeline output structure
            result["result_path"] = f"outputs/pipeline/{pipeline_result.pipeline_id}/pipeline_result.json"

        return result

    def _load_route_plan(self, task_id: str) -> Optional[RoutePlan]:
        """
        Load route plan from task metadata

        Args:
            task_id: Task ID

        Returns:
            RoutePlan or None if not found
        """
        try:
            task = self.task_manager.get_task(task_id)
            if not task or not task.metadata:
                return None

            # Check if route_plan exists in metadata
            route_plan_data = task.metadata.get("route_plan")
            if not route_plan_data:
                return None

            # Parse route plan
            if isinstance(route_plan_data, str):
                route_plan_data = json.loads(route_plan_data)

            route_plan = RoutePlan.from_dict(route_plan_data)
            return route_plan

        except Exception as e:
            logger.error(f"Failed to load route plan for task {task_id}: {e}")
            return None

    def _save_route_plan(self, task_id: str, route_plan: RoutePlan):
        """
        Save route plan to task metadata

        Args:
            task_id: Task ID
            route_plan: RoutePlan to save
        """
        try:
            task = self.task_manager.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found, cannot save route plan")
                return

            # Update metadata
            if not task.metadata:
                task.metadata = {}

            task.metadata["route_plan"] = route_plan.to_dict()

            # Save to database
            conn = self.task_manager._get_conn()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tasks SET metadata = ? WHERE task_id = ?",
                    (json.dumps(task.metadata), task_id)
                )
                conn.commit()
                logger.debug(f"Saved route plan for task {task_id}")
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Failed to save route plan for task {task_id}: {e}")


def run_task_subprocess(task_id: str, use_real_pipeline: bool = False):
    """Entry point for subprocess execution
    
    This function is called when starting a task runner as a subprocess.
    
    Args:
        task_id: Task ID to run
        use_real_pipeline: If True, use real ModePipelineRunner (P1)
    """
    # Setup logging for subprocess
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    logger.info(f"Starting task runner: task_id={task_id}, real_pipeline={use_real_pipeline}")
    
    runner = TaskRunner(use_real_pipeline=use_real_pipeline)
    runner.run_task(task_id)


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Task Runner")
    parser.add_argument("task_id", help="Task ID to run")
    parser.add_argument("--real-pipeline", action="store_true", help="Use real ModePipelineRunner (P1)")
    parser.add_argument("--repo-path", type=str, default=".", help="Repository path")
    parser.add_argument("--policy-path", type=str, help="Sandbox policy path")
    
    args = parser.parse_args()
    
    logger.info(f"Task runner args: {args}")
    
    run_task_subprocess(
        task_id=args.task_id,
        use_real_pipeline=args.real_pipeline
    )
