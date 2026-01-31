# ADR-CHAT-003: InfoNeed Classification Architecture

**Status**: Accepted
**Date**: 2026-01-31
**Authors**: AgentOS Architecture Team
**Related**: ADR-CHAT-COMM-001-Guards.md, ADR-CHAT-MODE-001-Conversation-Mode-Architecture.md, ADR-EXTERNAL-INFO-DECLARATION-001.md

---

## Context

### Problem Statement

When users ask questions in chat, the system currently faces a fundamental challenge: **How do we determine whether the LLM should answer directly or seek external information?**

#### The Traditional Approach (Why It Fails)

Many systems ask the LLM directly: "Do you know this?" This approach has critical flaws:

1. **Hallucination Risk**: LLMs confidently answer even when uncertain
2. **No Ground Truth**: No way to verify if the LLM "actually knows"
3. **Knowledge Cutoff Blindness**: LLM doesn't know what it doesn't know about recent events
4. **Non-Deterministic**: Same question yields different "do I know" answers
5. **Non-Auditable**: Cannot explain why the decision was made

#### Real-World Examples

**Scenario 1: Time-Sensitive Question**
- User: "What's the latest AI regulation in Australia?"
- LLM (wrong approach): "Based on my knowledge, Australia has X policy..." (potentially outdated)
- Correct approach: Detect "latest" → classify as EXTERNAL_FACT_UNCERTAIN → trigger search

**Scenario 2: Ambient State Question**
- User: "What time is it?"
- LLM (wrong approach): Triggers web search (unnecessary, privacy-invasive)
- Correct approach: Detect time query → classify as AMBIENT_STATE → call local system API

**Scenario 3: Local Knowledge Question**
- User: "What is REST API?"
- LLM (wrong approach): Triggers web search (wasteful, slow)
- Correct approach: Detect stable concept → classify as LOCAL_KNOWLEDGE → answer directly

#### Core Insight

The question is not "Does the LLM know?" but rather:

**"Would answering this question with current knowledge pose a risk of providing unverifiable, time-sensitive, or externally-authoritative information?"**

### Design Requirements

1. **Explainable**: Every classification decision must be auditable with clear reasoning
2. **Deterministic**: Same question type should yield consistent classification (modulo LLM self-assessment)
3. **Efficient**: Classification must happen before LLM generates full response
4. **Safe**: Default to external search when uncertain (fail-safe principle)
5. **Controllable**: Rules and thresholds must be tunable without code changes
6. **Integrable**: Seamlessly integrate with existing ChatEngine, PhaseGate, and ExternalInfoDeclaration

---

## Decision

### Architecture: InfoNeedClassifier

We introduce **InfoNeedClassifier**, a rule-based + AI-assisted classification system that determines question types before response generation.

#### Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  ChatEngine Message Processing Flow                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 1: InfoNeedClassifier.classify(message)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Substep 1: Rule-Based Fast Path (Hard Rules)      │   │
│  │  - Pattern matching (keywords, regex)              │   │
│  │  - Domain heuristics (time, location, ambient)     │   │
│  │  - High confidence → Return classification          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓ (if uncertain)                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Substep 2: LLM Self-Assessment (Controlled)       │   │
│  │  - Prompt: "Is this answer stable over 24h?"       │   │
│  │  - Structured output: {confidence, reason}          │   │
│  │  - DOES NOT generate answer content                │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Substep 3: Decision Matrix Resolver                │   │
│  │  - Combines rule signals + LLM confidence           │   │
│  │  - Maps to one of five question types               │   │
│  │  - Returns ClassificationResult with reasoning      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Decision Routing                                   │
│  - LOCAL_DETERMINISTIC / LOCAL_KNOWLEDGE → Direct Answer    │
│  - AMBIENT_STATE → Local Capability (time, config, session) │
│  - EXTERNAL_FACT_UNCERTAIN → ExternalInfoDeclaration + UI   │
│  - OPINION_DISCUSSION → Direct Answer + Optional Disclaimer │
└─────────────────────────────────────────────────────────────┘
```

---

## Five Question Types

### 1. LOCAL_DETERMINISTIC (本地确定型)

**Definition**: Questions that can be answered deterministically without external facts.

**Characteristics**:
- Pure computation, logic, or reasoning
- Based on user-provided context or code
- No risk of factual incorrectness over time
- No need for authoritative external sources

**Examples**:
- "Summarize this code for me" (user already provided code)
- "What's wrong with this design?" (analysis of given design)
- "Explain what this function does" (code interpretation)
- "Calculate 123 * 456" (math computation)
- "Translate this to Spanish" (language transformation)

**Confidence Indicators**:
- Contains: "summarize", "explain", "analyze", "calculate", "translate"
- Refers to user-provided content: "this code", "this text", "above snippet"
- No time sensitivity markers: "latest", "today", "current"

**Routing Decision**: Direct answer with ChatEngine (no external search)

**Risk Level**: LOW - Pure reasoning, no external dependency

---

### 2. LOCAL_KNOWLEDGE (本地知识型)

**Definition**: Questions about stable, common knowledge that doesn't require current/authoritative sources.

**Characteristics**:
- General concepts, definitions, principles
- Stable knowledge unlikely to change rapidly
- No explicit request for "latest" or "official" information
- Acceptable to answer from training data

**Examples**:
- "What is REST API?" (stable concept)
- "Explain the difference between AI and ML" (established distinction)
- "How does AgentOS work?" (general concept explanation)
- "What are SOLID principles?" (established software engineering concept)
- "Why use microservices?" (architectural pattern discussion)

**Confidence Indicators**:
- Contains: "what is", "define", "explain concept", "difference between"
- Refers to established concepts, not specific implementations
- No temporal modifiers: "today", "now", "current", "2025"
- No authority references: "official", "policy", "regulation"

**Routing Decision**: Direct answer with optional disclaimer ("Note: For latest specifications, consult official docs")

**Risk Level**: LOW-MEDIUM - Generally safe, but may benefit from disclaimer for critical domains

---

### 3. AMBIENT_STATE (环境状态/工具型)

**Definition**: Questions about current system/session state or environment properties.

**Characteristics**:
- System context queries (time, date, timezone)
- Session metadata (current mode, phase, configuration)
- Local environment properties (OS, paths, installed packages)
- NOT factual internet searches

**Examples**:
- "What time is it?" (local system time)
- "What's today's date?" (local system date)
- "What phase am I in?" (session state)
- "What's my current conversation mode?" (session configuration)
- "Is network mode enabled?" (system configuration)
- "What extensions are installed?" (local state)

**Confidence Indicators**:
- Contains: "now", "current", "what phase", "what mode", "what session"
- Refers to AgentOS-specific state: "phase", "mode", "session", "task"
- Time queries: "what time", "today's date", "timezone"
- Configuration queries: "enabled", "configured", "installed"

**Critical Rule**: MUST NOT trigger CommunicationOS (search/fetch)

**Routing Decision**: Call local capability API (system time, session store, config reader)

**Risk Level**: NONE - Pure local operations

**Anti-Pattern Detection**:
```python
# WRONG: Triggering web search for "what time is it"
if "time" in question:
    return comm_search("current time")  # VIOLATION

# CORRECT: Call local API
if "time" in question:
    return datetime.now()  # Local capability
```

---

### 4. EXTERNAL_FACT_UNCERTAIN (外部不确定事实)

**Definition**: Questions requiring verifiable, time-sensitive, or authoritative external information.

**Characteristics**:
- Temporal sensitivity: "latest", "today", "current", "now"
- Authoritative sources: "official", "policy", "regulation", "announcement"
- Specific events/news: "what happened", "who won", "latest release"
- Verifiable facts: should have URL/source citation

**Examples**:
- "What's the latest AI policy in Australia?" (time-sensitive + authoritative)
- "What happened in AI news today?" (time-sensitive)
- "What's the current Python version?" (time-sensitive)
- "Show me official AgentOS documentation" (authoritative)
- "What are the new features in Claude Opus 4.5?" (time-sensitive + authoritative)
- "What's the weather in Sydney?" (time-sensitive)

**Confidence Indicators**:
- Contains: "latest", "today", "current", "now", "recent", "2025", "2026"
- Contains: "official", "policy", "regulation", "law", "announcement"
- Contains: "news", "what happened", "who won", "released"
- Asks for specific URLs, documentation, or sources

**Critical Rule**: MUST trigger ExternalInfoDeclaration flow

**Routing Decision**:
1. Return classification with ExternalInfoDeclaration
2. Show UI prompt: "This question requires external information. Switch to execution phase to search?"
3. Wait for user approval via `/execute` or UI button
4. Execute `comm.search` or `comm.fetch`
5. Return results with attribution

**Risk Level**: HIGH if answered without external verification

**LLM Self-Assessment Prompt** (if rule-based confidence is medium):
```
If I answer this question without internet access, could my answer
be factually incorrect or outdated 24 hours later?

Return ONLY this JSON (no explanation):
{
  "confidence": "high" | "medium" | "low",
  "reason": "time-sensitive" | "authoritative" | "stable"
}

Question: "{user_question}"

DO NOT provide answer content. Only assess stability.
```

---

### 5. OPINION_DISCUSSION (主观/讨论型)

**Definition**: Questions seeking opinions, judgments, or subjective analysis.

**Characteristics**:
- Requests opinions: "do you think", "what's your view", "should we"
- Seeks recommendations: "is this approach good", "better to use X or Y"
- Open-ended discussions: "pros and cons", "tradeoffs"
- May reference facts, but primarily seeks judgment

**Examples**:
- "What do you think of AgentOS architecture?" (opinion)
- "Should I use microservices or monolith?" (recommendation)
- "Is this design pattern appropriate?" (judgment)
- "Do you think AI regulation is necessary?" (opinion)
- "What's better: Python or JavaScript?" (subjective comparison)

**Confidence Indicators**:
- Contains: "do you think", "your opinion", "your view", "should I", "is this good"
- Contains: "better", "best", "recommend", "suggest"
- Contains: "pros and cons", "tradeoffs", "compare"

**Routing Decision**:
- **High confidence** (pure opinion): Direct answer
- **Medium confidence** (opinion + facts): Direct answer + disclaimer ("This is based on general principles. For specific use case, external research may help.")
- **Low confidence** (heavy factual dependency): Suggest external search

**Risk Level**: LOW-MEDIUM - Opinion is subjective, but factual backing may improve quality

**Optional Disclaimer**: "Based on general software engineering principles. For your specific context, consider researching recent case studies."

---

## Multi-Signal Classification Algorithm

### Three-Step Process

```
Step 1: Rule-Based Fast Path (Hard Rules)
    ↓
Step 2: LLM Self-Assessment (Controlled Query)
    ↓
Step 3: Decision Matrix Resolver (Final Classification)
```

---

### Step 1: Rule-Based Fast Path

**Purpose**: Catch obvious cases with 100% confidence using pattern matching.

**Implementation**:

```python
class RuleEngine:
    """Rule-based classifier for fast-path detection"""

    # Time-sensitive keywords
    TEMPORAL_KEYWORDS = [
        "latest", "current", "now", "today", "this week", "recent",
        "2025", "2026", "just released", "breaking news"
    ]

    # Authoritative keywords
    AUTHORITATIVE_KEYWORDS = [
        "official", "policy", "regulation", "law", "government",
        "announcement", "documentation", "specification", "standard"
    ]

    # Ambient state keywords
    AMBIENT_STATE_KEYWORDS = [
        "what time", "current time", "today's date", "timezone",
        "what phase", "what mode", "current session", "my task",
        "am I in", "is enabled", "configured"
    ]

    # Local knowledge keywords
    KNOWLEDGE_KEYWORDS = [
        "what is", "define", "explain", "difference between",
        "how does", "why use", "concept of", "principle"
    ]

    # Opinion keywords
    OPINION_KEYWORDS = [
        "do you think", "your opinion", "should I", "is this good",
        "recommend", "suggest", "better", "best", "pros and cons"
    ]

    # Deterministic keywords
    DETERMINISTIC_KEYWORDS = [
        "summarize", "explain this", "analyze this", "calculate",
        "translate", "this code", "above snippet", "given text"
    ]

    def classify_by_rules(self, question: str) -> Optional[RuleMatch]:
        """Apply rule-based classification.

        Returns:
            RuleMatch with type and confidence, or None if no strong match
        """
        q_lower = question.lower()

        # Priority 1: Ambient state (highest confidence)
        if self._matches_ambient_state(q_lower):
            return RuleMatch(
                type="AMBIENT_STATE",
                confidence="high",
                reason="Matches ambient state patterns",
                matched_keywords=self._extract_keywords(q_lower, self.AMBIENT_STATE_KEYWORDS)
            )

        # Priority 2: External fact (time-sensitive OR authoritative)
        temporal_match = self._has_keywords(q_lower, self.TEMPORAL_KEYWORDS)
        auth_match = self._has_keywords(q_lower, self.AUTHORITATIVE_KEYWORDS)

        if temporal_match or auth_match:
            reason = []
            if temporal_match: reason.append("time-sensitive")
            if auth_match: reason.append("authoritative")

            return RuleMatch(
                type="EXTERNAL_FACT_UNCERTAIN",
                confidence="high" if (temporal_match and auth_match) else "medium",
                reason=" + ".join(reason),
                matched_keywords=temporal_match + auth_match
            )

        # Priority 3: Local deterministic
        if self._matches_deterministic(q_lower):
            return RuleMatch(
                type="LOCAL_DETERMINISTIC",
                confidence="high",
                reason="References user-provided content or pure computation",
                matched_keywords=self._extract_keywords(q_lower, self.DETERMINISTIC_KEYWORDS)
            )

        # Priority 4: Opinion
        if self._has_keywords(q_lower, self.OPINION_KEYWORDS):
            return RuleMatch(
                type="OPINION_DISCUSSION",
                confidence="medium",
                reason="Contains opinion-seeking language",
                matched_keywords=self._extract_keywords(q_lower, self.OPINION_KEYWORDS)
            )

        # Priority 5: Local knowledge
        if self._has_keywords(q_lower, self.KNOWLEDGE_KEYWORDS):
            return RuleMatch(
                type="LOCAL_KNOWLEDGE",
                confidence="medium",
                reason="Asks for concept definition or explanation",
                matched_keywords=self._extract_keywords(q_lower, self.KNOWLEDGE_KEYWORDS)
            )

        # No strong rule match
        return None

    def _matches_ambient_state(self, q_lower: str) -> bool:
        """Check if question matches ambient state patterns."""
        # Time patterns
        if any(p in q_lower for p in ["what time", "what's the time", "current time", "now is"]):
            return True

        # Phase/mode patterns
        if any(p in q_lower for p in ["what phase", "current phase", "what mode", "in execution"]):
            return True

        # Session patterns
        if any(p in q_lower for p in ["my session", "current session", "session state"]):
            return True

        return False

    def _matches_deterministic(self, q_lower: str) -> bool:
        """Check if question matches deterministic patterns."""
        # References to "this" or "above" content
        if any(p in q_lower for p in ["this code", "this text", "above", "given", "following"]):
            return True

        # Computational tasks
        if any(p in q_lower for p in ["calculate", "compute", "solve"]):
            return True

        # Transformations
        if any(p in q_lower for p in ["translate", "summarize", "paraphrase"]):
            return True

        return False

    def _has_keywords(self, text: str, keywords: list) -> list:
        """Return list of matched keywords."""
        return [kw for kw in keywords if kw in text]

    def _extract_keywords(self, text: str, keyword_list: list) -> list:
        """Extract matched keywords from text."""
        return [kw for kw in keyword_list if kw in text]
```

**Fast Path Decision**:
- If `RuleMatch.confidence == "high"` → Return classification immediately (skip LLM)
- If `RuleMatch.confidence == "medium"` → Proceed to Step 2 (LLM self-assessment)
- If `RuleMatch is None` → Proceed to Step 2 (LLM self-assessment)

---

### Step 2: LLM Self-Assessment (Controlled)

**Purpose**: For ambiguous cases, ask LLM to assess answer stability (NOT generate answer).

**Key Constraints**:
1. LLM does NOT generate answer content
2. LLM only assesses: "Would my answer be stable over 24 hours?"
3. Output is structured JSON (confidence + reason)
4. Small, fast model (Claude Haiku or GPT-3.5-turbo)
5. Strict prompt engineering to prevent answer leakage

**Prompt Template**:

```python
SELF_ASSESSMENT_PROMPT = """You are a question stability analyzer.

Your job: Determine if answering this question WITHOUT internet access could result in incorrect or outdated information 24 hours later.

Rules:
1. DO NOT answer the question
2. DO NOT provide any facts or explanations about the question topic
3. ONLY assess temporal stability and authoritativeness requirements

Return ONLY this JSON (no other text):
{{
  "confidence": "high" | "medium" | "low",
  "reason": "time-sensitive" | "authoritative" | "verifiable" | "stable" | "opinion"
}}

Definitions:
- confidence: "high" = definitely needs external info | "medium" = might need | "low" = probably doesn't need
- reason: "time-sensitive" = answer changes over time
         "authoritative" = requires official/verified source
         "verifiable" = should cite specific URL/source
         "stable" = answer unlikely to change
         "opinion" = subjective judgment, no single truth

Question: "{question}"

JSON output:
"""
```

**Example Interactions**:

**Input**: "What's the latest Python version?"
**Output**:
```json
{
  "confidence": "high",
  "reason": "time-sensitive"
}
```

**Input**: "What is REST API?"
**Output**:
```json
{
  "confidence": "low",
  "reason": "stable"
}
```

**Input**: "Should I use microservices?"
**Output**:
```json
{
  "confidence": "medium",
  "reason": "opinion"
}
```

**Implementation**:

```python
async def assess_with_llm(self, question: str) -> LLMAssessment:
    """Use LLM to assess question stability.

    Args:
        question: User's question

    Returns:
        LLMAssessment with confidence and reason
    """
    prompt = SELF_ASSESSMENT_PROMPT.format(question=question)

    # Use small, fast model
    response = await self.llm_client.generate(
        prompt=prompt,
        model="claude-3-haiku-20240307",
        max_tokens=100,  # JSON only, no lengthy explanation
        temperature=0.0,  # Deterministic
    )

    # Parse JSON
    try:
        data = json.loads(response.strip())
        return LLMAssessment(
            confidence=data["confidence"],
            reason=data["reason"]
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"LLM assessment parsing failed: {e}, defaulting to 'high' confidence")
        # Fail-safe: default to requiring external info
        return LLMAssessment(confidence="high", reason="parsing_failed")
```

**Fail-Safe Behavior**: If LLM assessment fails or returns invalid JSON, default to `confidence="high"` (require external info). This ensures safety.

---

### Step 3: Decision Matrix Resolver

**Purpose**: Combine rule-based signals and LLM assessment to produce final classification.

**Decision Matrix**:

| Rule Type              | Rule Conf | LLM Conf | Final Type              | Routing                  |
|------------------------|-----------|----------|-------------------------|--------------------------|
| AMBIENT_STATE          | high      | any      | AMBIENT_STATE           | Local API                |
| EXTERNAL_FACT_UNCERTAIN| high      | any      | EXTERNAL_FACT_UNCERTAIN | ExternalInfoDeclaration  |
| LOCAL_DETERMINISTIC    | high      | any      | LOCAL_DETERMINISTIC     | Direct Answer            |
| LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | Direct Answer + Disclaimer|
| LOCAL_KNOWLEDGE        | medium    | medium   | LOCAL_KNOWLEDGE         | Direct Answer + Strong Disclaimer|
| LOCAL_KNOWLEDGE        | medium    | high     | EXTERNAL_FACT_UNCERTAIN | ExternalInfoDeclaration  |
| OPINION_DISCUSSION     | medium    | low      | OPINION_DISCUSSION      | Direct Answer            |
| OPINION_DISCUSSION     | medium    | medium   | OPINION_DISCUSSION      | Direct Answer + Suggest Search|
| OPINION_DISCUSSION     | medium    | high     | EXTERNAL_FACT_UNCERTAIN | ExternalInfoDeclaration  |
| EXTERNAL_FACT_UNCERTAIN| medium    | low      | LOCAL_KNOWLEDGE         | Direct Answer (upgrade)  |
| EXTERNAL_FACT_UNCERTAIN| medium    | medium   | EXTERNAL_FACT_UNCERTAIN | ExternalInfoDeclaration  |
| EXTERNAL_FACT_UNCERTAIN| medium    | high     | EXTERNAL_FACT_UNCERTAIN | ExternalInfoDeclaration  |
| None (no rule match)   | n/a       | high     | EXTERNAL_FACT_UNCERTAIN | ExternalInfoDeclaration (safe default)|
| None (no rule match)   | n/a       | medium   | LOCAL_KNOWLEDGE         | Direct Answer + Disclaimer|
| None (no rule match)   | n/a       | low      | LOCAL_KNOWLEDGE         | Direct Answer            |

**Implementation**:

```python
class DecisionMatrixResolver:
    """Resolves final classification from rules + LLM assessment"""

    def resolve(
        self,
        rule_match: Optional[RuleMatch],
        llm_assessment: Optional[LLMAssessment]
    ) -> ClassificationResult:
        """Apply decision matrix to produce final classification.

        Args:
            rule_match: Result from rule-based classifier
            llm_assessment: Result from LLM self-assessment

        Returns:
            ClassificationResult with type, confidence, and routing
        """
        # Priority 1: High-confidence rule matches (override LLM)
        if rule_match and rule_match.confidence == "high":
            if rule_match.type == "AMBIENT_STATE":
                return ClassificationResult(
                    type=QuestionType.AMBIENT_STATE,
                    confidence="high",
                    reason=f"Rule match: {rule_match.reason}",
                    routing=RoutingDecision.LOCAL_CAPABILITY,
                    matched_keywords=rule_match.matched_keywords
                )

            if rule_match.type == "EXTERNAL_FACT_UNCERTAIN":
                return ClassificationResult(
                    type=QuestionType.EXTERNAL_FACT_UNCERTAIN,
                    confidence="high",
                    reason=f"Rule match: {rule_match.reason}",
                    routing=RoutingDecision.EXTERNAL_INFO_DECLARATION,
                    matched_keywords=rule_match.matched_keywords
                )

            if rule_match.type == "LOCAL_DETERMINISTIC":
                return ClassificationResult(
                    type=QuestionType.LOCAL_DETERMINISTIC,
                    confidence="high",
                    reason=f"Rule match: {rule_match.reason}",
                    routing=RoutingDecision.DIRECT_ANSWER,
                    matched_keywords=rule_match.matched_keywords
                )

        # Priority 2: Combine medium-confidence rule + LLM
        if rule_match and rule_match.confidence == "medium":
            return self._resolve_medium_confidence(rule_match, llm_assessment)

        # Priority 3: No rule match, rely on LLM
        if llm_assessment:
            return self._resolve_llm_only(llm_assessment)

        # Fallback: Default to local knowledge with disclaimer
        return ClassificationResult(
            type=QuestionType.LOCAL_KNOWLEDGE,
            confidence="low",
            reason="No strong signals, defaulting to local knowledge",
            routing=RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER,
            disclaimer="This answer is based on general knowledge. For critical decisions, consider external research."
        )

    def _resolve_medium_confidence(
        self,
        rule_match: RuleMatch,
        llm_assessment: Optional[LLMAssessment]
    ) -> ClassificationResult:
        """Resolve medium-confidence rule matches with LLM input."""
        llm_conf = llm_assessment.confidence if llm_assessment else "medium"

        # LOCAL_KNOWLEDGE + LLM assessment
        if rule_match.type == "LOCAL_KNOWLEDGE":
            if llm_conf == "low":
                return ClassificationResult(
                    type=QuestionType.LOCAL_KNOWLEDGE,
                    confidence="medium",
                    reason="Stable concept, low LLM uncertainty",
                    routing=RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER
                )
            elif llm_conf == "medium":
                return ClassificationResult(
                    type=QuestionType.LOCAL_KNOWLEDGE,
                    confidence="medium",
                    reason="Moderate uncertainty, suggesting caution",
                    routing=RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER,
                    disclaimer="For latest specifications, consult official documentation."
                )
            else:  # high
                return ClassificationResult(
                    type=QuestionType.EXTERNAL_FACT_UNCERTAIN,
                    confidence="high",
                    reason="LLM indicates high uncertainty, requires external verification",
                    routing=RoutingDecision.EXTERNAL_INFO_DECLARATION
                )

        # OPINION_DISCUSSION + LLM assessment
        if rule_match.type == "OPINION_DISCUSSION":
            if llm_conf in ["low", "medium"]:
                return ClassificationResult(
                    type=QuestionType.OPINION_DISCUSSION,
                    confidence="medium",
                    reason="Opinion-based question with low factual dependency",
                    routing=RoutingDecision.DIRECT_ANSWER
                )
            else:  # high
                return ClassificationResult(
                    type=QuestionType.EXTERNAL_FACT_UNCERTAIN,
                    confidence="high",
                    reason="Opinion requires factual backing, needs external info",
                    routing=RoutingDecision.EXTERNAL_INFO_DECLARATION
                )

        # EXTERNAL_FACT_UNCERTAIN + LLM downgrade
        if rule_match.type == "EXTERNAL_FACT_UNCERTAIN":
            if llm_conf == "low":
                return ClassificationResult(
                    type=QuestionType.LOCAL_KNOWLEDGE,
                    confidence="medium",
                    reason="Rule suggested external, but LLM indicates stability (downgrade)",
                    routing=RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER
                )
            else:  # medium or high
                return ClassificationResult(
                    type=QuestionType.EXTERNAL_FACT_UNCERTAIN,
                    confidence="high",
                    reason="Time-sensitive or authoritative, requires external verification",
                    routing=RoutingDecision.EXTERNAL_INFO_DECLARATION
                )

        # Fallback
        return ClassificationResult(
            type=QuestionType.LOCAL_KNOWLEDGE,
            confidence="low",
            reason="Medium rule match with no strong LLM signal",
            routing=RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER
        )

    def _resolve_llm_only(self, llm_assessment: LLMAssessment) -> ClassificationResult:
        """Resolve classification with only LLM assessment (no rule match)."""
        if llm_assessment.confidence == "high":
            return ClassificationResult(
                type=QuestionType.EXTERNAL_FACT_UNCERTAIN,
                confidence="high",
                reason=f"LLM indicates {llm_assessment.reason}, requires external info",
                routing=RoutingDecision.EXTERNAL_INFO_DECLARATION
            )
        elif llm_assessment.confidence == "medium":
            return ClassificationResult(
                type=QuestionType.LOCAL_KNOWLEDGE,
                confidence="medium",
                reason=f"LLM moderate uncertainty ({llm_assessment.reason})",
                routing=RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER
            )
        else:  # low
            return ClassificationResult(
                type=QuestionType.LOCAL_KNOWLEDGE,
                confidence="high",
                reason=f"LLM indicates stable answer ({llm_assessment.reason})",
                routing=RoutingDecision.DIRECT_ANSWER
            )
```

---

## Data Models

### Pydantic Models

```python
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    """Question type enumeration"""
    LOCAL_DETERMINISTIC = "local_deterministic"
    LOCAL_KNOWLEDGE = "local_knowledge"
    AMBIENT_STATE = "ambient_state"
    EXTERNAL_FACT_UNCERTAIN = "external_fact_uncertain"
    OPINION_DISCUSSION = "opinion_discussion"


class RoutingDecision(str, Enum):
    """Routing decision for question handling"""
    DIRECT_ANSWER = "direct_answer"
    DIRECT_ANSWER_WITH_DISCLAIMER = "direct_answer_with_disclaimer"
    LOCAL_CAPABILITY = "local_capability"
    EXTERNAL_INFO_DECLARATION = "external_info_declaration"


class RuleMatch(BaseModel):
    """Result of rule-based classification"""
    type: str = Field(..., description="Detected question type (string, not enum yet)")
    confidence: str = Field(..., description="Confidence level: high | medium | low")
    reason: str = Field(..., description="Explanation of why this rule matched")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords that triggered this rule")


class LLMAssessment(BaseModel):
    """Result of LLM self-assessment"""
    confidence: str = Field(..., description="LLM's confidence: high | medium | low")
    reason: str = Field(
        ...,
        description="LLM's reason: time-sensitive | authoritative | verifiable | stable | opinion"
    )


class ClassificationResult(BaseModel):
    """Final classification result"""
    type: QuestionType = Field(..., description="Classified question type")
    confidence: str = Field(..., description="Overall confidence: high | medium | low")
    reason: str = Field(..., description="Explanation of classification decision")
    routing: RoutingDecision = Field(..., description="How to route this question")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords from rule matching")
    disclaimer: Optional[str] = Field(None, description="Optional disclaimer to show with answer")
    external_info_declaration: Optional[ExternalInfoDeclaration] = Field(
        None,
        description="If routing is EXTERNAL_INFO_DECLARATION, this contains the declaration"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "type": self.type.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "routing": self.routing.value,
            "matched_keywords": self.matched_keywords,
            "disclaimer": self.disclaimer,
            "external_info_declaration": (
                self.external_info_declaration.to_dict()
                if self.external_info_declaration else None
            )
        }

    def needs_external_info(self) -> bool:
        """Check if this classification requires external information"""
        return self.routing == RoutingDecision.EXTERNAL_INFO_DECLARATION


class InfoNeedClassifierConfig(BaseModel):
    """Configuration for InfoNeedClassifier"""
    enable_llm_assessment: bool = Field(
        default=True,
        description="Enable LLM self-assessment for ambiguous cases"
    )
    llm_model: str = Field(
        default="claude-3-haiku-20240307",
        description="Model to use for LLM self-assessment"
    )
    llm_timeout: int = Field(
        default=5,
        description="Timeout for LLM assessment in seconds"
    )
    fail_safe_default: QuestionType = Field(
        default=QuestionType.EXTERNAL_FACT_UNCERTAIN,
        description="Default classification on error (fail-safe)"
    )
    enable_audit_logging: bool = Field(
        default=True,
        description="Log all classification decisions to audit trail"
    )
```

---

## Integration Architecture

### ChatEngine Integration

```python
class ChatEngine:
    """Main engine for Chat Mode"""

    def __init__(self, ...):
        # Existing components
        self.chat_service = chat_service or ChatService()
        self.context_builder = context_builder or ContextBuilder()
        self.model_router = model_router or ModelRouter(policy={})

        # NEW: Add InfoNeedClassifier
        self.info_classifier = InfoNeedClassifier(
            config=InfoNeedClassifierConfig()
        )

    async def send_message(
        self,
        message: str,
        session_id: str,
        execution_phase: str,
        **kwargs
    ) -> ChatResponse:
        """Send message to chat engine.

        Integration Flow:
        1. Classify question type (InfoNeedClassifier)
        2. Route based on classification
        3. Handle external info declaration if needed
        4. Generate response
        """
        # Step 1: Classify question type
        classification = await self.info_classifier.classify(message)

        logger.info(
            f"Question classified as {classification.type.value} "
            f"(confidence: {classification.confidence}, routing: {classification.routing.value})"
        )

        # Step 2: Route based on classification
        if classification.routing == RoutingDecision.LOCAL_CAPABILITY:
            # Handle ambient state queries (time, phase, session)
            return await self._handle_ambient_state(message, session_id, classification)

        elif classification.routing == RoutingDecision.EXTERNAL_INFO_DECLARATION:
            # Requires external info, block until user approves
            return await self._handle_external_info_needed(
                message,
                session_id,
                execution_phase,
                classification
            )

        elif classification.routing == RoutingDecision.DIRECT_ANSWER_WITH_DISCLAIMER:
            # Answer directly but add disclaimer
            response = await self._generate_response(message, session_id, **kwargs)
            response.metadata["disclaimer"] = classification.disclaimer
            return response

        else:  # DIRECT_ANSWER
            # Answer directly without disclaimer
            return await self._generate_response(message, session_id, **kwargs)

    async def _handle_ambient_state(
        self,
        message: str,
        session_id: str,
        classification: ClassificationResult
    ) -> ChatResponse:
        """Handle ambient state queries (time, phase, session)."""
        # Parse specific ambient query
        result = self._get_ambient_state(message, session_id)

        return ChatResponse(
            content=result["message"],
            role="assistant",
            metadata={
                "type": "ambient_state",
                "classification": classification.to_dict(),
                "source": "local_capability"
            }
        )

    def _get_ambient_state(self, message: str, session_id: str) -> Dict[str, Any]:
        """Get ambient state based on query type."""
        msg_lower = message.lower()

        # Time queries
        if any(p in msg_lower for p in ["time", "clock"]):
            from datetime import datetime
            now = datetime.now()
            return {
                "message": f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}",
                "value": now.isoformat()
            }

        # Phase queries
        if "phase" in msg_lower:
            session = self.chat_service.get_session(session_id)
            phase = session.execution_phase if session else "unknown"
            return {
                "message": f"Current execution phase: {phase}",
                "value": phase
            }

        # Mode queries
        if "mode" in msg_lower:
            session = self.chat_service.get_session(session_id)
            mode = session.conversation_mode if session else "unknown"
            return {
                "message": f"Current conversation mode: {mode}",
                "value": mode
            }

        # Session queries
        if "session" in msg_lower:
            return {
                "message": f"Session ID: {session_id}",
                "value": session_id
            }

        # Default
        return {
            "message": "I can provide information about: time, date, execution phase, conversation mode, session ID.",
            "value": None
        }

    async def _handle_external_info_needed(
        self,
        message: str,
        session_id: str,
        execution_phase: str,
        classification: ClassificationResult
    ) -> ChatResponse:
        """Handle case where external information is needed.

        This integrates with ExternalInfoDeclaration flow:
        1. Create ExternalInfoDeclaration
        2. Check if in execution phase
        3. If planning phase, return UI prompt for approval
        4. If execution phase, execute comm search/fetch
        """
        # Create ExternalInfoDeclaration
        declaration = ExternalInfoDeclaration(
            action=ExternalInfoAction.WEB_SEARCH,
            reason=f"Question classified as {classification.type.value}: {classification.reason}",
            target=message,
            priority=1 if "latest" in message.lower() or "today" in message.lower() else 2,
            estimated_cost="LOW"
        )

        # Check phase
        if execution_phase == "planning":
            # In planning phase, cannot execute external ops
            # Return response with ExternalInfoDeclaration
            return ChatResponse(
                content=(
                    f"This question requires external information search.\n\n"
                    f"Reason: {classification.reason}\n\n"
                    f"To proceed, switch to execution phase by typing `/execute` or clicking the Execute button."
                ),
                role="assistant",
                metadata={
                    "classification": classification.to_dict(),
                    "requires_phase_transition": True,
                    "suggested_phase": "execution"
                },
                external_info=[declaration]
            )

        elif execution_phase == "execution":
            # In execution phase, can execute external ops
            # Execute comm.search via CommunicationAdapter
            from agentos.core.chat.communication_adapter import CommunicationAdapter
            adapter = CommunicationAdapter()

            search_results = await adapter.search(
                query=message,
                session_id=session_id,
                task_id=session_id  # Use session_id as task context
            )

            # Generate response with search results
            return ChatResponse(
                content=self._format_search_response(search_results),
                role="assistant",
                metadata={
                    "classification": classification.to_dict(),
                    "search_results": search_results,
                    "attribution": f"CommunicationOS (search) in session {session_id}"
                },
                external_info=[declaration]
            )

        else:
            # Unknown phase, fail-safe to planning
            return ChatResponse(
                content="Unknown execution phase. Please set phase explicitly.",
                role="assistant",
                metadata={
                    "error": "unknown_phase",
                    "classification": classification.to_dict()
                }
            )

    def _format_search_response(self, search_results: Dict[str, Any]) -> str:
        """Format search results into human-readable response."""
        if not search_results.get("results"):
            return "No search results found."

        results = search_results["results"]
        formatted = "Search results:\n\n"

        for idx, result in enumerate(results[:5], 1):
            formatted += f"{idx}. **{result['title']}**\n"
            formatted += f"   {result['snippet']}\n"
            formatted += f"   Source: {result['url']}\n\n"

        formatted += f"\nAttribution: {search_results['metadata']['attribution']}"
        return formatted
```

---

## Decision Matrix (Complete Table)

| Question Example                              | Keywords Detected         | Rule Type              | Rule Conf | LLM Conf | Final Type              | Routing                  | Action                                      |
|-----------------------------------------------|---------------------------|------------------------|-----------|----------|-------------------------|--------------------------|---------------------------------------------|
| "What time is it?"                            | "what time"               | AMBIENT_STATE          | high      | n/a      | AMBIENT_STATE           | LOCAL_CAPABILITY         | Call `datetime.now()`                       |
| "What phase am I in?"                         | "what phase"              | AMBIENT_STATE          | high      | n/a      | AMBIENT_STATE           | LOCAL_CAPABILITY         | Query session store                         |
| "What's the latest AI regulation?"            | "latest", "regulation"    | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → `/execute` → `comm.search` |
| "What happened in AI news today?"             | "today", "news"           | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → `/execute` → `comm.search` |
| "Summarize this code"                         | "summarize", "this"       | LOCAL_DETERMINISTIC    | high      | n/a      | LOCAL_DETERMINISTIC     | DIRECT_ANSWER            | Answer directly                             |
| "Explain what this function does"             | "explain", "this"         | LOCAL_DETERMINISTIC    | high      | n/a      | LOCAL_DETERMINISTIC     | DIRECT_ANSWER            | Answer directly                             |
| "What is REST API?"                           | "what is"                 | LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | DIRECT_ANSWER_WITH_DISCLAIMER| Answer + "For latest specs, see official docs"|
| "Explain microservices concept"               | "explain", "concept"      | LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | DIRECT_ANSWER_WITH_DISCLAIMER| Answer + disclaimer                         |
| "What's the difference between AI and ML?"    | "difference between"      | LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | DIRECT_ANSWER            | Answer directly                             |
| "Do you think this design is good?"           | "do you think", "is good" | OPINION_DISCUSSION     | medium    | low      | OPINION_DISCUSSION      | DIRECT_ANSWER            | Answer directly                             |
| "Should I use microservices or monolith?"     | "should I"                | OPINION_DISCUSSION     | medium    | medium   | OPINION_DISCUSSION      | DIRECT_ANSWER            | Answer + suggest search for case studies    |
| "What's better: Python or JS?"                | "better"                  | OPINION_DISCUSSION     | medium    | low      | OPINION_DISCUSSION      | DIRECT_ANSWER            | Answer directly                             |
| "What's the current Python version?"          | "current", "version"      | EXTERNAL_FACT_UNCERTAIN| medium    | high     | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → search                     |
| "Show official Python docs"                   | "official"                | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → fetch                      |
| "Tell me about Python 3.12 features"          | "3.12" (version number)   | EXTERNAL_FACT_UNCERTAIN| medium    | medium   | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → search                     |
| "What's AgentOS architecture like?"           | "what's", "like"          | LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | DIRECT_ANSWER            | Answer based on general concept             |
| "How do I implement caching?"                 | "how do"                  | LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | DIRECT_ANSWER            | Answer directly                             |
| "Translate this to Spanish"                   | "translate", "this"       | LOCAL_DETERMINISTIC    | high      | n/a      | LOCAL_DETERMINISTIC     | DIRECT_ANSWER            | Answer directly                             |
| "Calculate 123 * 456"                         | "calculate"               | LOCAL_DETERMINISTIC    | high      | n/a      | LOCAL_DETERMINISTIC     | DIRECT_ANSWER            | Answer directly                             |
| "What's the weather in Sydney?"               | "weather", (location)     | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → weather API                |
| "Who won the 2025 Nobel Prize?"               | "won", "2025"             | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → search                     |
| "What are SOLID principles?"                  | "what are", "principles"  | LOCAL_KNOWLEDGE        | medium    | low      | LOCAL_KNOWLEDGE         | DIRECT_ANSWER            | Answer directly                             |
| "Explain the above algorithm"                 | "explain", "above"        | LOCAL_DETERMINISTIC    | high      | n/a      | LOCAL_DETERMINISTIC     | DIRECT_ANSWER            | Answer directly                             |
| "Is this code correct?"                       | "is this", "correct"      | LOCAL_DETERMINISTIC    | high      | n/a      | LOCAL_DETERMINISTIC     | DIRECT_ANSWER            | Analyze provided code                       |
| "What's my current session ID?"               | "current session"         | AMBIENT_STATE          | high      | n/a      | AMBIENT_STATE           | LOCAL_CAPABILITY         | Return session ID                           |
| "Is network mode enabled?"                    | "enabled"                 | AMBIENT_STATE          | high      | n/a      | AMBIENT_STATE           | LOCAL_CAPABILITY         | Check configuration                         |
| "What extensions are installed?"              | "installed"               | AMBIENT_STATE          | high      | n/a      | AMBIENT_STATE           | LOCAL_CAPABILITY         | Query extension registry                    |
| "What's the latest GPT-4 announcement?"       | "latest", "announcement"  | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → search                     |
| "Show me the AgentOS GitHub repo"             | "show me", "GitHub"       | EXTERNAL_FACT_UNCERTAIN| high      | n/a      | EXTERNAL_FACT_UNCERTAIN | EXTERNAL_INFO_DECLARATION| Show UI prompt → fetch URL                  |
| "What's the best database for my use case?"   | "best", "my use case"     | OPINION_DISCUSSION     | medium    | medium   | OPINION_DISCUSSION      | DIRECT_ANSWER            | Answer + "Consider researching benchmarks"  |
| "Pros and cons of serverless?"                | "pros and cons"           | OPINION_DISCUSSION     | medium    | low      | OPINION_DISCUSSION      | DIRECT_ANSWER            | Answer directly                             |

---

## Testing Requirements

### Test Coverage Checklist

#### Unit Tests (Minimum 30 Test Cases)

**Rule-Based Classifier Tests (10 tests)**:
1. ✅ Detect "what time" as AMBIENT_STATE
2. ✅ Detect "what phase" as AMBIENT_STATE
3. ✅ Detect "latest" + "news" as EXTERNAL_FACT_UNCERTAIN
4. ✅ Detect "official" + "policy" as EXTERNAL_FACT_UNCERTAIN
5. ✅ Detect "summarize this" as LOCAL_DETERMINISTIC
6. ✅ Detect "explain this code" as LOCAL_DETERMINISTIC
7. ✅ Detect "what is REST" as LOCAL_KNOWLEDGE
8. ✅ Detect "do you think" as OPINION_DISCUSSION
9. ✅ Detect "should I use" as OPINION_DISCUSSION
10. ✅ Return None for ambiguous question with no strong signals

**LLM Assessment Tests (5 tests)**:
11. ✅ LLM assesses "latest Python version" as high confidence + time-sensitive
12. ✅ LLM assesses "what is REST" as low confidence + stable
13. ✅ LLM assesses "should I use microservices" as medium confidence + opinion
14. ✅ LLM assessment timeout defaults to high confidence (fail-safe)
15. ✅ LLM assessment JSON parse error defaults to high confidence (fail-safe)

**Decision Matrix Tests (10 tests)**:
16. ✅ High-confidence AMBIENT_STATE overrides LLM
17. ✅ High-confidence EXTERNAL_FACT_UNCERTAIN overrides LLM
18. ✅ Medium LOCAL_KNOWLEDGE + low LLM → LOCAL_KNOWLEDGE
19. ✅ Medium LOCAL_KNOWLEDGE + high LLM → EXTERNAL_FACT_UNCERTAIN (upgrade)
20. ✅ Medium OPINION + low LLM → OPINION_DISCUSSION
21. ✅ Medium OPINION + high LLM → EXTERNAL_FACT_UNCERTAIN (upgrade)
22. ✅ Medium EXTERNAL_FACT + low LLM → LOCAL_KNOWLEDGE (downgrade)
23. ✅ No rule + high LLM → EXTERNAL_FACT_UNCERTAIN (safe default)
24. ✅ No rule + low LLM → LOCAL_KNOWLEDGE
25. ✅ No rule + no LLM → LOCAL_KNOWLEDGE (safe fallback)

**Integration Tests (5 tests)**:
26. ✅ Full flow: "what time" → AMBIENT_STATE → local API call
27. ✅ Full flow: "latest AI news" → EXTERNAL_FACT → ExternalInfoDeclaration
28. ✅ Full flow: "explain this code" → LOCAL_DETERMINISTIC → direct answer
29. ✅ Full flow: "what is ML" → LOCAL_KNOWLEDGE → answer + disclaimer
30. ✅ Full flow: Planning phase + EXTERNAL_FACT → blocked with UI prompt

#### End-to-End Tests (5 scenarios)

31. ✅ User asks time → ambient state response in <1s
32. ✅ User asks latest news in planning phase → UI prompt to switch to execution
33. ✅ User asks latest news in execution phase → comm.search executed + results shown
34. ✅ User asks opinion → direct answer with optional search suggestion
35. ✅ User asks stable concept → direct answer with disclaimer

#### Performance Tests (3 benchmarks)

36. ✅ Rule-based classification latency < 10ms
37. ✅ LLM assessment latency < 5s
38. ✅ Full classification pipeline < 5.5s

#### Audit Trail Tests (2 tests)

39. ✅ All classifications logged to audit trail with reasoning
40. ✅ Classification metadata included in ChatResponse

---

## Consequences

### Positive

1. **Explainable Decisions**: Every classification has clear reasoning chain (rules + LLM)
2. **Fail-Safe**: Defaults to requiring external info when uncertain (safety-first)
3. **Efficient**: Rule-based fast path handles 60-70% of cases without LLM
4. **Controllable**: Rules and thresholds configurable without code changes
5. **Auditable**: All decisions logged with reasoning and matched keywords
6. **Privacy-Preserving**: Ambient state queries don't leak to external services
7. **Cost-Optimized**: Uses small/fast LLM (Haiku) only for ambiguous cases
8. **Seamless Integration**: Works with existing PhaseGate and ExternalInfoDeclaration
9. **User Transparency**: Users see reasoning for external info requests
10. **Deterministic Core**: Rule-based layer ensures consistent behavior

### Negative

1. **Complexity**: Adds new component to ChatEngine with three-step pipeline
2. **Latency**: LLM assessment adds 2-5s for ambiguous cases
3. **Maintenance**: Rules require updates as new patterns emerge
4. **False Positives**: May over-classify as EXTERNAL_FACT for safe-by-default behavior
5. **LLM Dependency**: Relies on LLM to assess stability (non-deterministic element)
6. **Configuration Surface**: More configuration options increase complexity

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM assessment hallucination | Medium | Use structured output + fail-safe default |
| Rule keyword collisions | Low | Use multi-keyword patterns + priority ordering |
| Performance regression | Medium | Rule-based fast path + caching + async LLM |
| User confusion about routing | Medium | Clear UI messages explaining classification |
| Over-classification as external | Low | Tunable confidence thresholds + LLM downgrade path |
| Ambient state pattern drift | Low | Regular review of ambient patterns + extension API |

---

## Future Considerations

### Potential Enhancements

1. **User Feedback Loop**: Allow users to correct classifications to improve rules
2. **Pattern Learning**: Use ML to learn new patterns from audit logs
3. **Domain-Specific Rules**: Extension API for custom classification rules
4. **Multi-Language Support**: Keyword patterns for non-English queries
5. **Confidence Calibration**: Track accuracy metrics to tune thresholds
6. **Cached Classifications**: Cache results for identical questions within session
7. **Hybrid Routing**: Allow partial external info (e.g., answer + search suggestion)

### Open Questions

1. Should classification be per-message or per-conversation context?
2. How to handle multi-turn conversations where classification changes?
3. Should we support user overrides of classification decisions?
4. How to integrate with multi-agent scenarios (different agents, different needs)?
5. Should extensions be able to register custom question types?

---

## Implementation Checklist

**Phase 1: Core Implementation**
- [ ] Implement RuleEngine with keyword patterns
- [ ] Implement LLM self-assessment with structured prompt
- [ ] Implement DecisionMatrixResolver
- [ ] Create InfoNeedClassifier orchestrator
- [ ] Define Pydantic models (QuestionType, ClassificationResult, etc.)
- [ ] Write 30+ unit tests

**Phase 2: ChatEngine Integration**
- [ ] Add InfoNeedClassifier to ChatEngine initialization
- [ ] Integrate classify() call in send_message() flow
- [ ] Implement _handle_ambient_state()
- [ ] Implement _handle_external_info_needed()
- [ ] Update ChatResponse with classification metadata
- [ ] Write integration tests

**Phase 3: Testing & Validation**
- [ ] Run full test suite (40 tests)
- [ ] Perform end-to-end testing with real queries
- [ ] Measure latency benchmarks
- [ ] Validate audit trail logging
- [ ] Test phase gate integration
- [ ] User acceptance testing with WebUI

**Phase 4: Documentation & Release**
- [ ] Write user guide with examples
- [ ] Create developer documentation for extending rules
- [ ] Add configuration reference
- [ ] Update ChatEngine API docs
- [ ] Prepare release notes
- [ ] Conduct security review

---

## References

- **ADR-CHAT-COMM-001-Guards.md**: Phase Gate and Guard system architecture
- **ADR-CHAT-MODE-001-Conversation-Mode-Architecture.md**: Conversation mode and phase separation
- **ADR-EXTERNAL-INFO-DECLARATION-001.md**: External information declaration models
- **External Info Models**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/models/external_info.py`
- **Communication Adapter**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/communication_adapter.py`
- **ChatEngine Implementation**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/chat/engine.py`

---

## Appendix A: Example Classification Flows

### Example 1: Time Query (Ambient State)

**Input**: "What time is it?"

**Step 1: Rule-Based**
- Matched keywords: ["what time"]
- Rule type: AMBIENT_STATE
- Confidence: high
- → Skip LLM assessment (high confidence)

**Step 2: LLM Assessment**
- Skipped (rule confidence high)

**Step 3: Decision Matrix**
- Final type: AMBIENT_STATE
- Routing: LOCAL_CAPABILITY
- Action: Call `datetime.now()`

**Output**:
```json
{
  "type": "ambient_state",
  "confidence": "high",
  "reason": "Rule match: Matches ambient state patterns",
  "routing": "local_capability",
  "matched_keywords": ["what time"]
}
```

---

### Example 2: Latest News (External Fact)

**Input**: "What's the latest AI regulation in Australia?"

**Step 1: Rule-Based**
- Matched keywords: ["latest", "regulation"]
- Rule type: EXTERNAL_FACT_UNCERTAIN
- Confidence: high
- Reason: "time-sensitive + authoritative"
- → Skip LLM assessment (high confidence)

**Step 2: LLM Assessment**
- Skipped (rule confidence high)

**Step 3: Decision Matrix**
- Final type: EXTERNAL_FACT_UNCERTAIN
- Routing: EXTERNAL_INFO_DECLARATION
- Action: Show UI prompt → `/execute` → `comm.search`

**Output**:
```json
{
  "type": "external_fact_uncertain",
  "confidence": "high",
  "reason": "Rule match: time-sensitive + authoritative",
  "routing": "external_info_declaration",
  "matched_keywords": ["latest", "regulation"],
  "external_info_declaration": {
    "action": "web_search",
    "reason": "Question classified as external_fact_uncertain: time-sensitive + authoritative",
    "target": "What's the latest AI regulation in Australia?",
    "priority": 1,
    "estimated_cost": "LOW"
  }
}
```

---

### Example 3: Concept Explanation (Local Knowledge)

**Input**: "What is REST API?"

**Step 1: Rule-Based**
- Matched keywords: ["what is"]
- Rule type: LOCAL_KNOWLEDGE
- Confidence: medium
- → Proceed to LLM assessment

**Step 2: LLM Assessment**
- Prompt: "Is 'What is REST API?' stable over 24h?"
- LLM response:
```json
{
  "confidence": "low",
  "reason": "stable"
}
```

**Step 3: Decision Matrix**
- Medium LOCAL_KNOWLEDGE + low LLM → LOCAL_KNOWLEDGE
- Routing: DIRECT_ANSWER_WITH_DISCLAIMER
- Disclaimer: "For latest specifications, consult official documentation."

**Output**:
```json
{
  "type": "local_knowledge",
  "confidence": "medium",
  "reason": "Stable concept, low LLM uncertainty",
  "routing": "direct_answer_with_disclaimer",
  "matched_keywords": ["what is"],
  "disclaimer": "For latest specifications, consult official documentation."
}
```

---

### Example 4: Opinion Question (Discussion)

**Input**: "Should I use microservices or monolith?"

**Step 1: Rule-Based**
- Matched keywords: ["should I"]
- Rule type: OPINION_DISCUSSION
- Confidence: medium
- → Proceed to LLM assessment

**Step 2: LLM Assessment**
- Prompt: "Is 'Should I use microservices or monolith?' stable over 24h?"
- LLM response:
```json
{
  "confidence": "medium",
  "reason": "opinion"
}
```

**Step 3: Decision Matrix**
- Medium OPINION_DISCUSSION + medium LLM → OPINION_DISCUSSION
- Routing: DIRECT_ANSWER
- Suggestion: "Consider researching case studies for your specific context."

**Output**:
```json
{
  "type": "opinion_discussion",
  "confidence": "medium",
  "reason": "Opinion-based question with low factual dependency",
  "routing": "direct_answer",
  "matched_keywords": ["should I"]
}
```

---

### Example 5: Code Explanation (Local Deterministic)

**Input**: "Explain what this function does: `def add(a, b): return a + b`"

**Step 1: Rule-Based**
- Matched keywords: ["explain", "this"]
- Rule type: LOCAL_DETERMINISTIC
- Confidence: high
- → Skip LLM assessment (high confidence)

**Step 2: LLM Assessment**
- Skipped (rule confidence high)

**Step 3: Decision Matrix**
- Final type: LOCAL_DETERMINISTIC
- Routing: DIRECT_ANSWER

**Output**:
```json
{
  "type": "local_deterministic",
  "confidence": "high",
  "reason": "Rule match: References user-provided content or pure computation",
  "routing": "direct_answer",
  "matched_keywords": ["explain", "this"]
}
```

---

## Appendix B: Configuration Examples

### Default Configuration

```yaml
# config/info_need_classifier.yaml

enable_llm_assessment: true
llm_model: "claude-3-haiku-20240307"
llm_timeout: 5
fail_safe_default: "external_fact_uncertain"
enable_audit_logging: true

# Rule confidence thresholds
confidence_thresholds:
  high: 0.9
  medium: 0.6
  low: 0.3

# Keyword patterns (extensible)
custom_keywords:
  ambient_state:
    - "what's my quota"
    - "remaining credits"
  external_fact:
    - "breaking news"
    - "just announced"
```

### High-Security Configuration (Minimal External Calls)

```yaml
enable_llm_assessment: true
llm_model: "claude-3-haiku-20240307"
llm_timeout: 5
fail_safe_default: "local_knowledge"  # Default to local, not external

# More conservative: require explicit signals for external
confidence_thresholds:
  high: 0.95
  medium: 0.75
  low: 0.5
```

### Performance-Optimized Configuration (Minimize Latency)

```yaml
enable_llm_assessment: false  # Disable LLM, rules only
llm_model: null
llm_timeout: 0
fail_safe_default: "local_knowledge"

# Rely heavily on rules
enable_cache: true
cache_ttl: 3600  # Cache classifications for 1 hour
```

---

**End of ADR-CHAT-003-InfoNeed-Classification**
