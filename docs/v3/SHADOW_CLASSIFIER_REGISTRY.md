# Shadow Classifier Registry

## Overview

The Shadow Classifier Registry is a centralized system for managing and evaluating alternative classifier versions in parallel with the production (active) classifier. Shadow classifiers run alongside the active classifier but **never affect user-facing behavior** - they are used purely for evaluation and comparison.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│              Shadow Classifier System               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐         ┌──────────────┐        │
│  │   Active     │         │   Shadow     │        │
│  │ Classifier   │         │ Classifiers  │        │
│  │   (v1)       │         │  (v2.a, v2.b)│        │
│  └──────┬───────┘         └──────┬───────┘        │
│         │                        │                 │
│         ├────────────────────────┤                 │
│         │    Parallel Evaluation │                 │
│         ▼                        ▼                 │
│  ┌──────────────┐         ┌──────────────┐        │
│  │   Active     │         │   Shadow     │        │
│  │  Decision    │         │  Decisions   │        │
│  │ (executed)   │         │ (observed)   │        │
│  └──────┬───────┘         └──────┬───────┘        │
│         │                        │                 │
│         │                        │                 │
│         ▼                        ▼                 │
│  ┌─────────────────────────────────────┐          │
│  │     Decision Comparison System      │          │
│  │  (Task #30-35: Audit, Scoring, UI)  │          │
│  └─────────────────────────────────────┘          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Key Abstractions

#### 1. `BaseShadowClassifier`

Base class for all shadow classifiers with enforced constraints:

```python
class BaseShadowClassifier(ABC):
    """
    Shadow classifier base class.

    Constraints:
    - Must be read-only (no side effects)
    - Cannot call external services
    - Must use same input/output format as active
    - Returns DecisionCandidate with role=SHADOW
    """

    async def classify_shadow(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> DecisionCandidate:
        """Perform shadow classification (computation only)."""
        pass
```

#### 2. `ShadowClassifierRegistry`

Centralized registry for managing shadow classifier versions:

```python
class ShadowClassifierRegistry:
    """
    Registry for shadow classifier versions.

    Responsibilities:
    - Register/unregister shadow classifiers
    - Activate/deactivate for parallel evaluation
    - Version validation and metadata tracking
    - Thread-safe concurrent access
    """

    def register(self, classifier: BaseShadowClassifier) -> None:
        """Register a shadow classifier."""

    def activate(self, version_id: str) -> None:
        """Activate for parallel evaluation."""

    def get_active_shadows(self) -> List[BaseShadowClassifier]:
        """Get all active shadow classifiers."""
```

#### 3. `DecisionCandidate`

Represents a single classification decision (active or shadow):

```python
class DecisionCandidate(BaseModel):
    """
    Decision candidate from active or shadow classifier.

    Attributes:
        message_id: Message this decision applies to
        decision_id: Unique decision identifier
        role: ACTIVE or SHADOW
        classifier_version: Version metadata
        classification: The classification result
        latency_ms: Computation time
    """
```

## Current Shadow Classifier Versions

### Shadow v2.a: Expanded Keywords

**Version ID**: `v2-shadow-expand-keywords`

**Changes**:
- Expanded EXTERNAL_FACT_UNCERTAIN keyword list
- Expanded AMBIENT_STATE time keyword list
- No changes to decision matrix or logic

**Risk Level**: LOW

**Expected Impact**: Higher recall for time-sensitive and ambient state questions

**Example Additions**:
```python
additional_external_keywords = [
    "最新", "latest update", "current status",
    "政策", "policy", "regulation", "法规",
    "趋势", "trend", "动态", "dynamics",
]

additional_ambient_keywords = [
    "现在", "当前", "目前", "此刻",
    "now", "currently", "present",
]
```

### Shadow v2.b: Adjusted Thresholds

**Version ID**: `v2-shadow-adjust-threshold`

**Changes**:
- Lowered EXTERNAL_FACT confidence threshold from 0.6 to 0.5
- More aggressive triggering of external info requirements

**Risk Level**: MEDIUM

**Expected Impact**: Higher recall but possible increase in false positives

**Threshold Changes**:
```python
external_fact_threshold = 0.5  # was 0.6 in v1
ambient_state_threshold = 0.7  # unchanged
```

## How to Add New Shadow Versions

### Step 1: Implement Shadow Classifier

Create a new class extending `BaseShadowClassifier`:

```python
from agentos.core.chat.shadow_classifier import BaseShadowClassifier
from agentos.core.chat.models.decision_candidate import ClassifierVersion

class ShadowClassifierV3NewApproach(BaseShadowClassifier):
    """Shadow v3: Your new approach."""

    def __init__(self):
        version = ClassifierVersion(
            version_id="v3-shadow-new-approach",
            version_type="shadow",
            change_description="Brief description of changes",
        )
        super().__init__(version)

    async def classify_shadow(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> DecisionCandidate:
        """Implement your classification logic."""
        # Your implementation here
        pass

    def get_change_description(self) -> str:
        """Return detailed change description."""
        return """
        Shadow v3: New Approach
        =======================

        Changes:
        - Change 1
        - Change 2

        Impact: ...
        Risk Level: ...
        """
```

### Step 2: Register in Initialization

Add to `agentos/core/chat/shadow_init.py`:

```python
def initialize_shadow_classifiers(config: Optional[Dict[str, Any]] = None):
    """Initialize all shadow classifiers."""
    registry = get_shadow_registry()

    # Register existing shadows
    # ...

    # Register your new shadow
    try:
        shadow_v3 = ShadowClassifierV3NewApproach()
        registry.register(shadow_v3)
        logger.info(f"Registered shadow classifier: {shadow_v3.version.version_id}")
    except Exception as e:
        logger.error(f"Failed to register shadow v3: {e}")
```

### Step 3: Update Configuration

Add to `agentos/config/shadow_classifiers.yaml`:

```yaml
shadow_classifiers:
  active_versions:
    - v2-shadow-expand-keywords
    - v3-shadow-new-approach  # Add your version

  versions:
    v3-shadow-new-approach:
      enabled: true
      priority: 3
      description: "Your description"
      risk_level: "low|medium|high"
```

### Step 4: Write Tests

Create tests in `tests/unit/core/chat/test_shadow_v3.py`:

```python
@pytest.mark.asyncio
async def test_shadow_v3_classification():
    """Test v3 shadow classifier."""
    shadow = ShadowClassifierV3NewApproach()

    question = "Test question"
    context = {"message_id": "test-001"}

    decision = await shadow.classify_shadow(question, context)

    assert decision.role == DecisionRole.SHADOW
    assert decision.classifier_version.version_id == "v3-shadow-new-approach"
```

## Configuration

### Configuration File

Location: `agentos/config/shadow_classifiers.yaml`

```yaml
shadow_classifiers:
  # Global enable/disable
  enabled: true

  # Active versions (will run in parallel)
  active_versions:
    - v2-shadow-expand-keywords

  # Max concurrent shadows per question
  max_concurrent_shadows: 2

  # Evaluation timeout (ms)
  evaluation_timeout_ms: 500

  # Per-version configuration
  versions:
    v2-shadow-expand-keywords:
      enabled: true
      priority: 1
      description: "Expanded keyword coverage"
      risk_level: "low"
```

### Runtime Configuration

Reconfigure shadows without restarting:

```python
from agentos.core.chat.shadow_init import reconfigure_shadows

new_config = {
    "active_versions": ["v2-shadow-adjust-threshold"],
}

reconfigure_shadows(new_config)
```

## Security Constraints

Shadow classifiers must comply with strict security constraints:

### Red Lines (NEVER Cross)

1. **No External Calls**: Shadow classifiers MUST NOT call external APIs, databases, or services
2. **No Side Effects**: Shadow classifiers MUST NOT modify any state (files, databases, memory)
3. **No Execution**: Shadow decisions MUST NOT trigger any operations
4. **No User Impact**: Shadow decisions MUST NOT affect user-facing behavior

### Enforcement

Constraints are enforced at multiple levels:

#### 1. Type System

```python
class BaseShadowClassifier(ABC):
    def _validate_shadow_constraints(self):
        """Validate shadow constraints."""
        if self.version.version_type != "shadow":
            raise ValueError("Must be shadow version_type")
```

#### 2. Decision Role

```python
class DecisionCandidate(BaseModel):
    role: DecisionRole  # ACTIVE or SHADOW

    @model_validator(mode='after')
    def validate_shadow_constraints(self):
        """Ensure shadow decisions don't have execution results."""
        if self.role == DecisionRole.SHADOW:
            if self.shadow_metadata and "execution_result" in self.shadow_metadata:
                raise ValueError("Shadow decisions MUST NOT have execution results")
```

#### 3. Registry Validation

```python
def register(self, classifier: BaseShadowClassifier):
    """Register shadow classifier with validation."""
    if classifier.version.version_type != "shadow":
        raise ValueError("Only shadow classifiers can be registered")
```

## Usage Examples

### Basic Usage

```python
from agentos.core.chat.shadow_registry import get_shadow_registry
from agentos.core.chat.shadow_init import initialize_shadow_classifiers

# Initialize shadow system
initialize_shadow_classifiers()

# Get active shadows
registry = get_shadow_registry()
active_shadows = registry.get_active_shadows()

# Run all shadows in parallel
question = "What's the latest Python version?"
context = {"message_id": "msg-123", "session_id": "sess-456"}

tasks = [
    shadow.classify_shadow(question, context)
    for shadow in active_shadows
]
shadow_decisions = await asyncio.gather(*tasks)

# Compare with active decision
for shadow_decision in shadow_decisions:
    print(f"Shadow {shadow_decision.classifier_version.version_id}:")
    print(f"  Action: {shadow_decision.get_decision_action()}")
    print(f"  Latency: {shadow_decision.latency_ms}ms")
```

### Query Version Info

```python
registry = get_shadow_registry()

# List all versions
versions = registry.list_all_versions()
print(f"Registered versions: {versions}")

# Get detailed info
info = registry.get_version_info("v2-shadow-expand-keywords")
print(f"Version: {info['version_id']}")
print(f"Active: {info['is_active']}")
print(f"Changes: {info['detailed_changes']}")
```

### Activate/Deactivate

```python
registry = get_shadow_registry()

# Activate a shadow
registry.activate("v2-shadow-adjust-threshold")

# Deactivate a shadow
registry.deactivate("v2-shadow-expand-keywords")

# Batch operations
await registry.activate_batch([
    "v2-shadow-expand-keywords",
    "v2-shadow-adjust-threshold",
])

# Deactivate all
await registry.deactivate_all()
```

## Integration with Decision Comparison System

Shadow decisions are automatically logged and compared with active decisions through the v3 decision comparison system (Tasks #30-35):

```
1. Shadow Registry (Task #29) ───┐
2. Audit Log (Task #30)          │
3. Shadow Score (Task #31)       ├──> Decision Comparison System
4. Comparison UI (Task #32)      │
5. Metrics Generator (Task #33)  │
6. Improvement Proposal (Task #34)
7. Review Queue (Task #35)       ┘
```

## Best Practices

### 1. Start Conservative

Begin with low-risk shadows:
- Expand keyword coverage (like v2.a)
- Add more signals, don't change logic
- Keep thresholds unchanged initially

### 2. Gradual Rollout

1. Register new shadow (disabled)
2. Enable for small sample of traffic
3. Monitor divergence metrics
4. Gradually increase activation
5. Consider promotion to active if successful

### 3. Monitor Performance

- Shadow evaluation should complete in < 100ms
- Use timeouts to prevent blocking
- Run shadows in parallel, not serial
- Monitor divergence rates

### 4. Document Changes

Always provide:
- Clear version ID
- Change description
- Expected impact
- Risk level assessment

### 5. Test Thoroughly

Required tests:
- Unit tests for classification logic
- Integration tests for parallel execution
- Isolation tests (no side effects)
- Performance tests (latency)

## Troubleshooting

### Shadow Not Running

Check:
1. Is shadow registered? `registry.list_all_versions()`
2. Is shadow activated? `registry.is_active(version_id)`
3. Is global enable flag on? Check `shadow_classifiers.yaml`

### High Latency

Causes:
1. Too many shadows running in parallel
2. Shadow logic too complex
3. Not using async/await properly

Solutions:
- Reduce `max_concurrent_shadows`
- Optimize shadow classification logic
- Use `evaluation_timeout_ms`

### Divergence Not Detected

Check:
1. Are shadow decisions being stored? (Task #30: Audit Log)
2. Is comparison system running? (Task #32: Comparison UI)
3. Are metrics being generated? (Task #33: Metrics Generator)

## Related Tasks

- **Task #28**: DecisionCandidate data model (dependency)
- **Task #29**: Shadow Classifier Registry (this document)
- **Task #30**: Audit Log extension for shadow decisions
- **Task #31**: Shadow Score calculation engine
- **Task #32**: Decision Comparison WebUI
- **Task #33**: Comparison metrics generator
- **Task #34**: Improvement Proposal generation
- **Task #35**: Review Queue API and database

## References

- [ADR-V3-001: Shadow Classifier Architecture](../adr/ADR-V3-001-Shadow-Classifier.md) (to be created)
- [InfoNeedClassifier Implementation](../../agentos/core/chat/info_need_classifier.py)
- [Decision Candidate Models](../../agentos/core/chat/models/decision_candidate.py)
- [Shadow Classifier Base](../../agentos/core/chat/shadow_classifier.py)
- [Shadow Registry Implementation](../../agentos/core/chat/shadow_registry.py)
