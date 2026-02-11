"""Gates module for OctopusOS

This module provides gate execution and validation mechanisms.
"""

from octopusos.core.gates.pause_gate import (
    PauseState,
    PauseCheckpoint,
    PauseMetadata,
    PauseGateViolation,
    enforce_pause_checkpoint,
    can_pause_at,
    create_pause_metadata,
)

from octopusos.core.gates.done_gate import (
    DoneGateRunner,
    GateResult,
    GateRunResult,
)

__all__ = [
    # Pause gates
    "PauseState",
    "PauseCheckpoint",
    "PauseMetadata",
    "PauseGateViolation",
    "enforce_pause_checkpoint",
    "can_pause_at",
    "create_pause_metadata",
    # DONE gates
    "DoneGateRunner",
    "GateResult",
    "GateRunResult",
]
