# InfoNeedClassifier Test Matrix - Quick Reference

## Files Created

| File | Purpose | Lines | Location |
|------|---------|-------|----------|
| `info_need_test_matrix.yaml` | Main test matrix (45 cases) | 412 | `tests/fixtures/` |
| `validate_info_need_matrix.py` | Validation script | 152 | Root |
| `info_need_test_matrix_demo.py` | Usage examples | 306 | `examples/` |
| `INFO_NEED_TEST_MATRIX_USAGE.md` | Usage documentation | - | `tests/fixtures/` |
| `INFO_NEED_TEST_MATRIX_COMPLETION.md` | Completion report | - | Root |

**Total**: 870+ lines of code

---

## Test Matrix Overview

```
Total Cases: 45 (28% above minimum requirement)
Chinese: 26 cases (57.8%)
English: 19 cases (42.2%)
```

### Distribution by Type

```
Type                        Count   Min   Excess
══════════════════════════════════════════════════
LOCAL_DETERMINISTIC           8      6    +33%
LOCAL_KNOWLEDGE               9      6    +50%
AMBIENT_STATE                 7      6    +17%
EXTERNAL_FACT_UNCERTAIN      13      8    +63%
OPINION                       8      6    +33%
BOUNDARY (edge cases)         7      5    +40%
══════════════════════════════════════════════════
```

---

## Quick Usage

### Load Test Matrix

```python
import yaml

with open('tests/fixtures/info_need_test_matrix.yaml') as f:
    data = yaml.safe_load(f)

test_cases = data['test_cases']
```

### Test Your Classifier

```python
for case in test_cases:
    result = classifier.classify(case['question'])
    assert result.info_type == case['expected_type']
    assert result.action == case['expected_action']
```

### Run Validation

```bash
python3 validate_info_need_matrix.py
```

### Run Demo

```bash
python3 examples/info_need_test_matrix_demo.py
```

---

## Test Case Structure

```yaml
- id: "TYPE_NUMBER"
  category: "CATEGORY"
  question: "The question text"
  expected_type: "info_need_type"
  expected_action: "action"
  expected_confidence: "high|medium|low"
  reasoning: "Why this classification"
```

---

## 5 Information Need Types

### 1. LOCAL_DETERMINISTIC
**Questions**: Based on provided context
**Examples**:
- "帮我总结这段话..."
- "这段代码在做什么？"
- "Review this design..."

**Action**: `direct_answer`

### 2. LOCAL_KNOWLEDGE
**Questions**: Stable technical knowledge
**Examples**:
- "什么是REST API？"
- "What's the difference between AI and ML?"
- "解释SOLID原则"

**Action**: `direct_answer`

### 3. AMBIENT_STATE
**Questions**: Runtime system state
**Examples**:
- "现在几点？"
- "What's the current phase?"
- "我的session ID是什么？"

**Action**: `check_ambient`

### 4. EXTERNAL_FACT_UNCERTAIN
**Questions**: Time-sensitive or verifiable facts
**Examples**:
- "What are the latest AI news?"
- "今天有什么AI政策？"
- "澳洲政府对AI的规定？"

**Action**: `recommend_external`

### 5. OPINION
**Questions**: Subjective judgments
**Examples**:
- "你怎么看AI监管？"
- "React vs Vue哪个好？"
- "Can you recommend a learning path?"

**Action**: `direct_answer`

---

## Boundary Cases (7 cases)

| ID | Scenario | Challenge |
|----|----------|-----------|
| `BOUNDARY_001` | Mixed type | "最新REST规范" (stable + time) |
| `BOUNDARY_002` | Implicit time | "Python 3.12 features" |
| `BOUNDARY_003` | Vague request | "讲讲AI" |
| `BOUNDARY_004` | Multi-intent | "时间？新闻？" |
| `BOUNDARY_005` | Negation | "不要联网，告诉我..." |
| `BOUNDARY_006` | Hypothetical | "如果有新语言..." |
| `BOUNDARY_007` | Context-dependent | "这个error怎么修？" |

---

## Expected Actions

| Action | Meaning | Use Case |
|--------|---------|----------|
| `direct_answer` | Answer from model knowledge | LOCAL_*, OPINION |
| `check_ambient` | Query system state | AMBIENT_STATE |
| `recommend_external` | Suggest external tools | EXTERNAL_FACT |
| `explain_limitation` | Explain why can't answer | Conflicting constraints |

---

## Pytest Integration

```python
import pytest
import yaml

def load_test_cases():
    with open("tests/fixtures/info_need_test_matrix.yaml") as f:
        return yaml.safe_load(f)['test_cases']

@pytest.mark.parametrize("test_case", load_test_cases())
def test_classification(test_case, classifier):
    result = classifier.classify(test_case['question'])
    assert result.info_type == test_case['expected_type']
```

---

## Filtering Examples

### By Type
```python
external_cases = [
    c for c in test_cases
    if c['expected_type'] == 'external_fact_uncertain'
]
```

### By Language
```python
chinese_cases = [
    c for c in test_cases
    if any('\u4e00' <= ch <= '\u9fff' for ch in c['question'])
]
```

### Boundary Cases Only
```python
boundary_cases = [
    c for c in test_cases
    if c['category'].startswith('BOUNDARY_')
]
```

---

## Success Metrics

| Type | Target Accuracy |
|------|----------------|
| LOCAL_DETERMINISTIC | ≥ 95% |
| LOCAL_KNOWLEDGE | ≥ 90% |
| AMBIENT_STATE | ≥ 95% |
| EXTERNAL_FACT_UNCERTAIN | ≥ 85% |
| OPINION | ≥ 80% |
| BOUNDARY | ≥ 70% |

---

## Validation Checklist

Run `python3 validate_info_need_matrix.py`:

- ✅ Total cases ≥ 35 (actual: 45)
- ✅ Per-type minimums met
- ✅ Chinese content ≥ 30% (actual: 57.8%)
- ✅ All required fields present
- ✅ Unique IDs
- ✅ Valid actions

---

## Demo Output Sample

```
📊 Test Case Statistics
   Total test cases: 45
   ✅ Meets minimum requirement (>= 35)

🌐 Language Distribution:
   Chinese cases: 26 (57.8%)
   English cases: 19
   ✅ Meets minimum 30% Chinese requirement

✓ Minimum Requirements Check:
   ✅ local_deterministic           :  8 /  6 (required)
   ✅ local_knowledge               :  9 /  6 (required)
   ✅ ambient_state                 :  7 /  6 (required)
   ✅ external_fact_uncertain       : 13 /  8 (required)
   ✅ opinion                       :  8 /  6 (required)

✅ VALIDATION PASSED - Test matrix is ready for use!
```

---

## Integration Points

### Unit Tests (Task #14)
```python
# tests/unit/core/chat/test_info_need_classifier.py
from info_need_classifier import InfoNeedClassifier

@pytest.mark.parametrize("case", load_test_matrix())
def test_classification(case):
    # Test implementation
```

### Regression Tests (Task #16)
```python
# Automated regression testing with CI/CD
def test_classification_regression():
    accuracy = run_all_test_cases()
    assert accuracy >= 0.85
```

### Documentation (Task #17)
- API documentation
- Usage guides
- Classification guidelines

---

## Next Steps

1. **Task #14**: Implement unit tests using this matrix
2. **Task #16**: Set up regression testing framework
3. **Task #17**: Complete user documentation
4. **Task #18**: Run acceptance tests and generate report

---

## Quick Commands

```bash
# Validate test matrix
python3 validate_info_need_matrix.py

# Run demo
python3 examples/info_need_test_matrix_demo.py

# Run tests (once implemented)
pytest tests/unit/core/chat/test_info_need_classifier.py -v

# Generate coverage report
pytest --cov=agentos.core.chat.guards tests/ --cov-report=html
```

---

## File Locations

```
AgentOS/
├── tests/
│   └── fixtures/
│       ├── info_need_test_matrix.yaml          # Main test matrix
│       └── INFO_NEED_TEST_MATRIX_USAGE.md      # Usage guide
├── examples/
│   └── info_need_test_matrix_demo.py           # Demo script
├── validate_info_need_matrix.py                # Validation script
├── INFO_NEED_TEST_MATRIX_COMPLETION.md         # Completion report
└── INFO_NEED_TEST_MATRIX_QUICK_REF.md          # This file
```

---

## Key Statistics

- **Total Cases**: 45
- **Code Lines**: 870+
- **Coverage**: 5 types + 7 boundary cases
- **Languages**: Chinese (57.8%) + English (42.2%)
- **Validation**: ✅ All checks passed
- **Status**: ✅ Ready for integration

---

**Task**: #15 - ✅ COMPLETED
**Created**: 2026-01-31
**Version**: 1.0
