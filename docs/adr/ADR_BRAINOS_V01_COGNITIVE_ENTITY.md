# ADR-BRAIN-001: BrainOS v0.1 as Cognitive Entity

**Status**: Accepted
**Date**: 2026-01-30
**Version**: v0.1.0
**Authors**: BrainOS Core Team
**Supersedes**: None (Foundation Decision)
**Related**: ADR-V04 (Project-Aware Task OS), P1-A Acceptance Report

---

## Context and Problem Statement

AgentOS v0.6 established a robust execution system with task management, state machines, and governance. However, the system lacked a **cognitive layer** to answer fundamental questions about its own understanding:

- **"What does the system actually understand?"**
- **"How reliable is that understanding?"**
- **"Where are the knowledge gaps?"**

Without this layer, users must **trust** the system's outputs rather than **verify** them. This creates three critical problems:

### Problem 1: Black Box Understanding

Users cannot inspect the reasoning path behind system responses:
```
User: "Explain task state machine"
System: [Returns explanation]
User: "Is this reliable?" → ❌ No way to know
```

### Problem 2: Hidden Knowledge Gaps

The system cannot identify or communicate what it doesn't know:
```
User: "How does governance work?"
System: [Attempts to answer]
Reality: Governance is undocumented (Blind Spot) → ❌ Hallucination risk
```

### Problem 3: No Cognitive Baseline

There's no stable reference to measure the system's "intelligence growth":
- Coverage increases over time, but from what baseline?
- How to prove the system is "learning" vs "memorizing"?
- What's the difference between 70% coverage and 99% coverage?

---

## Decision

**We establish BrainOS as a "Local Cognitive Baseline" - a cognitive entity that can:**

1. **Quantify Understanding** (Coverage Metrics)
2. **Identify Knowledge Gaps** (Blind Spot Detection)
3. **Provide Evidence Trails** (Evidence Source Tracking)

This decision fundamentally changes BrainOS from a **tool** to a **cognitive entity**.

### Core Principles

#### Principle 1: Honest Over Comprehensive

```
❌ Wrong: "Answer all questions"
✅ Right: "Answer what can be proven, refuse what cannot"
```

BrainOS will **actively refuse** to answer questions in Blind Spot areas, rather than generate potentially hallucinated responses.

#### Principle 2: Verifiable Over Believable

```
❌ Wrong: "Trust the system"
✅ Right: "Verify the system"
```

Every response includes:
- **Coverage Badge**: Evidence density (0-100%)
- **Blind Spot Warning**: If entity is in a gap
- **Evidence Chain**: Git commits / Docs / Code traces

#### Principle 3: Cognitive Baseline Over Feature Count

```
❌ Wrong: "Add more capabilities"
✅ Right: "Maintain stable cognitive baseline"
```

Success is measured by:
- **Stable Coverage**: 71.9% code, 68.2% doc (as of v0.1)
- **Identified Blind Spots**: 17 high-value gaps
- **Evidence Quality**: 62,303 traceable evidence items

---

## Detailed Design

### 1. Coverage Calculation Engine

**File**: `agentos/core/brain/service.py`
**Function**: `compute_coverage()`

```python
def compute_coverage(store: BrainStore) -> CoverageMetrics:
    """
    Calculate cognitive coverage across three dimensions:
    - Code Coverage: Files with code entities
    - Doc Coverage: Files with documentation
    - Dependency Coverage: Files with dependency tracking

    Returns:
        CoverageMetrics with percentages and file lists
    """
```

**Performance**: 65.30ms (Excellent)

**Output**:
```json
{
  "total_files": 3140,
  "covered_files": 2258,
  "code_coverage": 0.719,
  "doc_coverage": 0.682,
  "dependency_coverage": 0.068,
  "uncovered_files": [...]
}
```

### 2. Blind Spot Detection Engine

**File**: `agentos/core/brain/blind_spot.py`
**Function**: `detect_blind_spots()`

```python
def detect_blind_spots(store: BrainStore) -> List[BlindSpot]:
    """
    Identify knowledge gaps using three detection strategies:
    1. High Fan-In Undocumented: Popular entities without docs
    2. Capability Without Implementation: Declared but not coded
    3. Trace Discontinuity: Broken reasoning paths

    Returns:
        List of BlindSpot sorted by severity (high → medium → low)
    """
```

**Performance**: 9.04ms (Excellent)

**Output**:
```json
{
  "total": 17,
  "by_severity": {"high": 14, "medium": 1, "low": 2},
  "by_type": {
    "high_fan_in_undocumented": 4,
    "capability_no_implementation": 13,
    "trace_discontinuity": 0
  },
  "blind_spots": [
    {
      "entity": "capability:governance",
      "severity": "high",
      "type": "capability_no_implementation",
      "reason": "Declared capability with no implementation"
    }
  ]
}
```

### 3. API Endpoints

**File**: `agentos/webui/api/brain.py`

**New Endpoints**:
```python
GET /api/brain/coverage
# Returns: CoverageMetrics

GET /api/brain/blind-spots
# Returns: List[BlindSpot]
```

**Enhanced Endpoints** (4 query types):
```python
GET /api/brain/query/concept/{name}
GET /api/brain/query/capability/{name}
GET /api/brain/query/trace/{file_path}
GET /api/brain/query/relations/{entity_id}

# All responses now include:
{
  "result": {...},
  "coverage_info": {
    "coverage_percent": 0.719,
    "in_blind_spot": false,
    "evidence_count": 42
  }
}
```

### 4. Dashboard UI Components

**File**: `agentos/webui/static/js/views/BrainView.js`

**Cognitive Coverage Card**:
```javascript
// Display:
// - Code Coverage: 71.9%
// - Doc Coverage: 68.2%
// - Dependency Coverage: 6.8%
// - Trend sparklines
```

**Top Blind Spots Card**:
```javascript
// Display:
// - Top 5 blind spots by severity
// - Severity badges (High/Medium/Low)
// - Impact description
```

**Explain Drawer Enhancements**:
```javascript
// All query results now show:
// 1. Coverage Badge (0-100%)
// 2. Blind Spot Warning (if applicable)
// 3. Evidence Source Links (Git/Doc/Code)
```

### 5. Knowledge Graph Structure

**Database**: `.brainos/v0.1_mvp.db`

**Statistics** (Production, as of 2026-01-30):
```yaml
Entities: 12,729
Edges: 62,255
Evidence Items: 62,303
Graph Version: 20260130-190239-6aa4aaa
Build Duration: 5.18 seconds
```

**Entity Types**:
- **File Entities**: 3,140 (source files)
- **Concept Entities**: ~2,500 (classes, functions, modules)
- **Capability Entities**: ~200 (declared capabilities)
- **Trace Entities**: ~7,000 (execution traces)

**Relationship Types**:
- `IMPORTS`: Module dependencies
- `DEFINES`: File → Concept
- `DOCUMENTS`: Concept → Documentation
- `IMPLEMENTS`: Concept → Capability
- `CALLS`: Function → Function
- `TRACES_TO`: Execution → File

---

## Implementation Evidence

### Acceptance Test Results

**Report**: `P1_A_FINAL_ACCEPTANCE_REPORT.md`

```
Total Tests: 34
Passed: 34 ✅
Failed: 0 ❌
Pass Rate: 100.0%
Grade: A
```

### Performance Benchmarks

| Operation | Duration | Target | Status |
|-----------|----------|--------|--------|
| Coverage Calculation | 65.30ms | <100ms | ✅ Excellent |
| Blind Spot Detection | 9.04ms | <50ms | ✅ Excellent |
| Knowledge Graph Build | 5,182ms | <10s | ✅ Good |

### Data Consistency Validation

- ✅ Coverage metrics sum correctly
- ✅ Blind spot distributions match totals
- ✅ No data integrity issues detected
- ✅ Evidence chains are complete and traceable

---

## Consequences

### Positive

#### 1. Trust Through Verification

Users can now **verify** system understanding rather than **trust** it:
```
Before: "The system says X" → Must trust
After: "The system says X with 89% coverage and 12 evidence items" → Can verify
```

#### 2. Honest Failure Modes

System explicitly refuses to answer in Blind Spot areas:
```
Before: [Attempts to answer] → Potential hallucination
After: "⚠️ This concept is in a Blind Spot (high fan-in, undocumented)"
```

#### 3. Measurable Intelligence Growth

Coverage provides a stable baseline to measure learning:
```
Week 1: 47% coverage
Week 4: 71.9% coverage → Provable growth
```

#### 4. Strategic Knowledge Building

Blind Spots guide documentation and implementation priorities:
```
High Severity Blind Spot: "capability:governance"
→ Action: Prioritize governance documentation
```

### Negative

#### 1. User Expectation Management

Users may expect 99% coverage, but system maintains 70% honestly:
- **Mitigation**: Clear communication that honesty > completeness
- **Trade-off**: Trust through verification, not blind faith

#### 2. Increased System Complexity

Coverage and Blind Spot engines add 2 new components:
- **Mitigation**: Excellent performance (65ms + 9ms)
- **Trade-off**: Complexity for trustworthiness

#### 3. Potential Over-Rejection

System may refuse to answer questions it could partially address:
- **Mitigation**: Coverage Badge shows partial evidence (e.g., 45%)
- **Trade-off**: Conservative over hallucination

---

## Alternatives Considered

### Alternative 1: RAG-Only System (No Cognitive Layer)

**Approach**: Use vector similarity without coverage tracking.

**Rejected Reason**:
- Cannot quantify understanding
- Cannot identify knowledge gaps
- Cannot prove reliability

### Alternative 2: 100% Coverage Goal

**Approach**: Fill all Blind Spots to achieve complete coverage.

**Rejected Reason**:
- Unsustainable (documentation debt grows faster than coverage)
- Sacrifices honesty (forced to document everything, even uncertainties)
- Misses the point: Value is in **identifying** gaps, not hiding them

### Alternative 3: Silent Failure (Hide Blind Spots)

**Approach**: Don't show Blind Spot warnings to users.

**Rejected Reason**:
- Violates core principle: Honest over comprehensive
- Destroys trust when users discover hidden gaps
- Contradicts cognitive entity philosophy

---

## Success Criteria

v0.1 is considered successful when:

### 1. Functional Requirements
- [x] Coverage calculation works (3 dimensions: code/doc/dep)
- [x] Blind Spot detection works (3 types: fan-in/capability/trace)
- [x] API endpoints return correct data
- [x] Dashboard UI displays metrics correctly
- [x] Explain drawer shows coverage badges

### 2. Performance Requirements
- [x] Coverage calculation <100ms (achieved: 65ms)
- [x] Blind Spot detection <50ms (achieved: 9ms)
- [x] Knowledge graph build <10s (achieved: 5.2s)

### 3. Quality Requirements
- [x] 34/34 acceptance tests pass
- [x] Data consistency validated
- [x] No integrity issues in production DB
- [x] Evidence chains complete and traceable

### 4. User Experience Requirements
- [x] Coverage badges visible on all query results
- [x] Blind Spot warnings shown proactively
- [x] Evidence sources linked and accessible
- [x] Dashboard provides actionable insights

---

## Roadmap to v0.2

v0.2 will focus on **navigability**, not **coverage increase**:

### P1-B: Query Autocomplete with Coverage Hints

**Goal**: Help users avoid Blind Spots before asking questions.

**Approach**:
```
User types: "governa..."
Autocomplete suggests:
  - "governance (⚠️ Blind Spot: high)"
  - "governance dashboard (✅ 89% coverage)"
```

### P2: Knowledge Subgraph Visualization

**Goal**: Make cognitive structure and gaps visible.

**Approach**:
- Visual graph of entities and relationships
- Color-code by coverage (green: high, yellow: medium, red: blind spot)
- Interactive navigation of reasoning paths

### Constraints for v0.2

**No new features that sacrifice the three pillars**:
1. ❌ Auto-fill Blind Spots (sacrifices honesty)
2. ❌ Fuzzy inference without evidence (sacrifices auditability)
3. ❌ Hide low coverage warnings (sacrifices explainable failure)

---

## Related Decisions

- **ADR-V04**: Project-Aware Task OS - Establishes execution baseline
- **ADR-007**: Database Write Serialization - Ensures data integrity
- **ADR-008**: Evidence Types Semantics - Defines evidence model
- **ADR-009**: Narrative Positioning - Frames BrainOS in product context

---

## References

### Technical Documentation
- [P1-A Final Acceptance Report](../../P1_A_FINAL_ACCEPTANCE_REPORT.md)
- [Coverage Engine](../../agentos/core/brain/service.py)
- [Blind Spot Engine](../../agentos/core/brain/blind_spot.py)
- [BrainOS API](../../agentos/webui/api/brain.py)

### Philosophical Foundation
- [BrainOS v0.1 Manifesto](../../BRAINOS_V0.1_MANIFESTO.md)
- [Cognitive Entity Definition](../../docs/architecture/COGNITIVE_ENTITY_DEFINITION.md)

### Production Evidence
- Knowledge Graph: `.brainos/v0.1_mvp.db`
- Graph Version: 20260130-190239-6aa4aaa
- Build Commit: 6aa4aaa

---

## Notes

### Design Rationale

#### Why "Cognitive Entity" vs "Tool"?

A **tool** responds to commands.
A **cognitive entity** can evaluate its own understanding.

BrainOS v0.1 crosses this threshold by:
1. Quantifying its own knowledge (Coverage)
2. Identifying its own gaps (Blind Spots)
3. Providing evidence for its claims (Evidence Chains)

#### Why 71.9% Coverage is Acceptable?

**71.9% with evidence** is more valuable than **99% without proof**.

The goal is not comprehensive coverage, but:
- **Honest assessment** of understanding
- **Clear identification** of gaps
- **Verifiable evidence** for claims

#### Why Refuse to Answer in Blind Spots?

**Refusing to answer is a cognitive act.**

It demonstrates:
- Self-awareness of limitations
- Respect for user trust
- Commitment to verifiable claims

This is the foundation of **trustworthy AI**.

---

**Status**: Accepted
**Decision Date**: 2026-01-30
**Review Status**: Approved by Architecture Team
**Implementation Status**: Complete (v0.1)
**Last Updated**: 2026-01-30

---

*"The first time a system learned to say: I don't know."*
