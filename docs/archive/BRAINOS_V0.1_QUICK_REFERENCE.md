# BrainOS v0.1 Quick Reference Card

**Version**: v0.1.0 | **Date**: 2026-01-30 | **Status**: Production Ready

---

## Core Concept (30 seconds)

> **BrainOS 是一个"本地认知层"**：它不追求回答所有问题，而是诚实标记理解边界。

**核心能力**：
1. 量化理解程度（Coverage: 71.9%）
2. 标记认知盲区（Blind Spots: 17 个）
3. 提供证据链条（Evidence: 62,303 条）

---

## What Is It? (3 Key Points)

### 1. Cognitive Entity, Not Tool
- **Tool**: Answers questions
- **Cognitive Entity**: Answers + Evaluates reliability

### 2. Honest Over Comprehensive
- **Wrong**: "Answer all questions"
- **Right**: "Answer what can be proven, refuse what cannot"

### 3. Verifiable Over Believable
- **Before**: "Trust the system"
- **After**: "Verify the system"

---

## What It Does (The Three Questions)

| Question | Answer | Example |
|----------|--------|---------|
| **我知道多少？** | Coverage Metrics | 71.9% code, 68.2% doc, 6.8% dep |
| **我哪里不知道？** | Blind Spot Detection | 17 high-value gaps identified |
| **这个解释可靠吗？** | Evidence Source Tracking | 62,303 traceable evidence items |

---

## What It Doesn't Do (Deliberate Non-Goals)

- ❌ 不填补覆盖率空白（不隐藏盲区）
- ❌ 不生成幻觉性答案（在盲区明确拒绝）
- ❌ 不以覆盖率作为成功指标（诚实 > 完整）
- ❌ 不隐藏"我不知道"（主动标记盲区）

---

## Key Metrics (Production)

```
Knowledge Graph:
  12,729 entities | 62,255 edges | 62,303 evidence items

Coverage:
  Code: 71.9% | Doc: 68.2% | Dep: 6.8%

Blind Spots:
  Total: 17 | High: 14 | Medium: 1 | Low: 2

Performance:
  Coverage: 65ms | Blind Spots: 9ms | Graph Build: 5.2s
```

---

## How to Use (3 Steps)

### Step 1: Ask a Question
```
Query: "Explain task state machine"
```

### Step 2: Check Coverage Badge
```
✅ 89% Coverage (42 evidence items)
⚠️ 45% Coverage (12 evidence items)
❌ 0% Coverage (Blind Spot)
```

### Step 3: Verify Evidence
```
Evidence Sources:
  - Git: 3 commits
  - Doc: 12 references
  - Code: 27 traces
```

---

## User Experience Changes

### Before P1-A:
```
User: "How does governance work?"
System: [Returns explanation]
User: ❓ "How reliable is this?"
```

### After P1-A:
```
User: "How does governance work?"
System: ⚠️ "This concept is in a Blind Spot (high severity)"
        Type: capability_no_implementation
        Reason: Declared but not implemented
User: ✅ "I trust this honesty!"
```

---

## Technical Stack (1 Minute)

```
┌─────────────────────┐
│   Dashboard UI      │  BrainView.js
│  (Coverage Cards)   │
└──────────┬──────────┘
           │ REST API
┌──────────▼──────────┐
│   API Endpoints     │  GET /api/brain/coverage
│  (brain.py)         │  GET /api/brain/blind-spots
└──────────┬──────────┘
           │ Function Calls
┌──────────▼──────────┐
│  Coverage Engine    │  compute_coverage() (65ms)
│  Blind Spot Engine  │  detect_blind_spots() (9ms)
└──────────┬──────────┘
           │ Query
┌──────────▼──────────┐
│  Knowledge Graph    │  12,729 entities
│  (.brainos/v0.1)    │  62,255 edges
└─────────────────────┘
```

---

## Core Philosophy (One Sentence Each)

1. **诚实 > 全面**: 71% 有证据覆盖 > 99% 无证据幻觉
2. **验证 > 信任**: 用户可以验证，而非相信
3. **认知实体 > 工具**: 能评估自己的理解

---

## Next Steps (v0.2 Roadmap)

| Feature | Purpose | Status |
|---------|---------|--------|
| Query Autocomplete | 避免用户进入盲区 | Planned |
| Subgraph Visualization | 可视化认知结构 | Planned |
| Historical Tracking | 追踪智力成长 | Planned |

---

## Quick Facts

- **Release Date**: 2026-01-30
- **Grade**: A (34/34 tests pass)
- **Performance**: <100ms (Coverage + Blind Spots)
- **Coverage**: 71.9% code, 68.2% doc
- **Blind Spots**: 17 identified
- **Evidence**: 62,303 traceable items

---

## One-Liner Summary

> **BrainOS v0.1: 系统第一次学会了说"我不知道"。**
> *"The system learned, for the first time, to say: I don't know."*

---

## Where to Learn More

| Resource | Location |
|----------|----------|
| **Manifesto** | `BRAINOS_V0.1_MANIFESTO.md` |
| **ADR** | `docs/adr/ADR_BRAINOS_V01_COGNITIVE_ENTITY.md` |
| **Milestone** | `docs/milestones/MILESTONE_V0.1_P1A_COMPLETE.md` |
| **Acceptance Report** | `P1_A_FINAL_ACCEPTANCE_REPORT.md` |

---

## Contact

**Team**: BrainOS Core Team
**Status**: Production Ready
**License**: Proprietary (Curated Public Snapshot)

---

*Print this card for quick reference during presentations or reviews.*
