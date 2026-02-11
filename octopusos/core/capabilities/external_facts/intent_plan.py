"""Intent plan contract for external facts capability execution."""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field

from .registry import get_capability


class IntentPlan(BaseModel):
    """Structured execution plan produced by LLM/rules and executed by backend."""

    intent: Literal["analysis", "query"]
    capability_id: str
    item_id: str
    params: Dict[str, Any] = Field(default_factory=dict)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    presentation: Dict[str, Any] = Field(default_factory=dict)


class PlanValidationError(ValueError):
    """Raised when an intent plan does not match capability registry contract."""



def parse_intent_plan_payload(payload: Dict[str, Any]) -> IntentPlan:
    """Parse raw payload into typed plan."""
    return IntentPlan.model_validate(payload)



def validate_intent_plan(plan: IntentPlan) -> list[str]:
    """Validate plan against capability/item schemas in registry."""
    errors: list[str] = []
    capability = get_capability(plan.capability_id)
    if capability is None:
        return [f"Unknown capability_id: {plan.capability_id}"]

    item = capability.item(plan.item_id)
    if item is None:
        return [f"Unknown item_id '{plan.item_id}' for capability '{plan.capability_id}'"]

    schema = item.input_schema or {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}

    for field_name in required:
        if plan.params.get(field_name) in (None, ""):
            errors.append(f"Missing required param: {field_name}")

    for param_name, param_value in plan.params.items():
        prop = properties.get(param_name) if isinstance(properties, dict) else None
        if not isinstance(prop, dict):
            continue
        expected_type = str(prop.get("type") or "")
        if expected_type == "integer":
            if not isinstance(param_value, int):
                errors.append(f"Param '{param_name}' must be integer")
                continue
            minimum = prop.get("minimum")
            maximum = prop.get("maximum")
            if isinstance(minimum, int) and param_value < minimum:
                errors.append(f"Param '{param_name}' must be >= {minimum}")
            if isinstance(maximum, int) and param_value > maximum:
                errors.append(f"Param '{param_name}' must be <= {maximum}")
        elif expected_type == "number":
            if not isinstance(param_value, (int, float)):
                errors.append(f"Param '{param_name}' must be number")
        elif expected_type == "string":
            if not isinstance(param_value, str):
                errors.append(f"Param '{param_name}' must be string")
                continue
            min_len = prop.get("minLength")
            max_len = prop.get("maxLength")
            if isinstance(min_len, int) and len(param_value) < min_len:
                errors.append(f"Param '{param_name}' must have length >= {min_len}")
            if isinstance(max_len, int) and len(param_value) > max_len:
                errors.append(f"Param '{param_name}' must have length <= {max_len}")

    return errors



def ensure_valid_intent_plan(plan: IntentPlan) -> None:
    """Raise validation error when plan is invalid."""
    errors = validate_intent_plan(plan)
    if errors:
        raise PlanValidationError("; ".join(errors))
