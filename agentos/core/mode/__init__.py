"""Mode System - 最小可签版本

Mode = 运行约束集合（不是 if/else）
"""

from .mode import Mode, ModeViolationError, get_mode
from .mode_selector import ModeSelector, ModeSelection
from .mode_proposer import ModeProposer, propose_mode
from .pipeline_runner import ModePipelineRunner, PipelineResult, StageResult

__all__ = [
    "Mode",
    "ModeViolationError",
    "get_mode",
    "ModeSelector",
    "ModeSelection",
    "ModeProposer",
    "propose_mode",
    "ModePipelineRunner",
    "PipelineResult",
    "StageResult",
]
