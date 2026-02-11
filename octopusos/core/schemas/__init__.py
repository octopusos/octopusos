"""Schema definitions for OctopusOS Open Plan system."""

from .open_plan import (
    OpenPlan,
    ModeSelection,
    PlanStep,
    ProposedAction,
    Artifact,
    validate_open_plan,
    ValidationError,
    OPEN_PLAN_JSON_SCHEMA
)
from .action_validators import (
    ACTION_SCHEMAS,
    ValidationResult,
    validate_action,
    validate_actions,
    get_action_schema,
    get_available_kinds,
    get_schema_documentation
)
from .structural_validator import (
    StructuralValidator,
    StructuralValidationReport,
    validate_open_plan_structure
)
from .output_parser import (
    SchemaOutputParser,
    ParseResult,
    ParseError,
)

__all__ = [
    # OpenPlan classes
    "OpenPlan",
    "ModeSelection",
    "PlanStep",
    "ProposedAction",
    "Artifact",
    "validate_open_plan",
    "ValidationError",
    "OPEN_PLAN_JSON_SCHEMA",
    # Action validators
    "ACTION_SCHEMAS",
    "ValidationResult",
    "validate_action",
    "validate_actions",
    "get_action_schema",
    "get_available_kinds",
    "get_schema_documentation",
    # Structural validator
    "StructuralValidator",
    "StructuralValidationReport",
    "validate_open_plan_structure",
    # Output parser
    "SchemaOutputParser",
    "ParseResult",
    "ParseError",
]
