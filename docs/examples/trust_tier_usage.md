# Trust Tier System Usage Examples

**Version**: 1.0.0
**Date**: 2026-01-30
**Category**: Developer Guide

---

## Overview

This guide demonstrates how to use CommunicationOS's Trust Tier system to ensure information reliability.

**Critical Principle**: **Search ≠ Truth**

Search engines are candidate source generators, NOT truth oracles.

---

## Quick Start

### Basic Usage

```python
from agentos.core.communication.service import CommunicationService
from agentos.core.communication.evidence import EvidenceLogger
from agentos.core.communication.models import TrustTier

# Initialize services
comm = CommunicationService()
evidence_logger = EvidenceLogger()

# Step 1: Search (generates candidates)
search_response = await comm.execute(
    connector_type=ConnectorType.WEB_SEARCH,
    operation="search",
    params={"query": "Python asyncio best practices"},
)

# Get evidence
search_evidence = await evidence_logger.get_evidence(search_response.evidence_id)
print(f"Search trust tier: {search_evidence.trust_tier}")
# Output: search_result (LOWEST - don't use as facts!)

# Step 2: Fetch from candidates (verify sources)
for result in search_response.data['results'][:3]:
    url = result['url']

    # Fetch actual content
    fetch_response = await comm.execute(
        connector_type=ConnectorType.WEB_FETCH,
        operation="fetch",
        params={"url": url},
    )

    # Check trust tier
    fetch_evidence = await evidence_logger.get_evidence(fetch_response.evidence_id)
    print(f"URL: {url}")
    print(f"Trust tier: {fetch_evidence.trust_tier}")

    # Use based on trust tier
    if fetch_evidence.trust_tier >= TrustTier.PRIMARY_SOURCE:
        print("✅ Can use for decision-making")
        # Process content...
    elif fetch_evidence.trust_tier == TrustTier.EXTERNAL_SOURCE:
        print("⚠️ Needs verification")
        # Require corroboration...
    else:
        print("❌ Do not use as facts")
```

---

## Example 1: Fact Verification

### Scenario: Verify a medical fact

```python
async def verify_medical_fact(fact: str) -> tuple[bool, list]:
    """Verify a medical fact using trust tier system.

    Returns:
        (is_verified, supporting_evidence)
    """
    # Step 1: Search for candidate sources
    search_results = await comm.execute(
        connector_type=ConnectorType.WEB_SEARCH,
        operation="search",
        params={"query": fact},
    )

    # Step 2: Fetch and categorize by trust tier
    evidence_by_tier = {
        TrustTier.AUTHORITATIVE_SOURCE: [],
        TrustTier.PRIMARY_SOURCE: [],
        TrustTier.EXTERNAL_SOURCE: [],
    }

    for result in search_results.data['results'][:10]:
        url = result['url']

        # Fetch content
        content = await comm.execute(
            connector_type=ConnectorType.WEB_FETCH,
            operation="fetch",
            params={"url": url},
        )

        # Get trust tier
        evidence = await evidence_logger.get_evidence(content.evidence_id)

        if evidence.trust_tier != TrustTier.SEARCH_RESULT:
            evidence_by_tier[evidence.trust_tier].append({
                'url': url,
                'content': content,
                'evidence': evidence,
            })

    # Step 3: Verify with high-trust sources
    authoritative = evidence_by_tier[TrustTier.AUTHORITATIVE_SOURCE]
    primary = evidence_by_tier[TrustTier.PRIMARY_SOURCE]

    # Rule 1: Two authoritative sources = verified
    if len(authoritative) >= 2:
        return True, authoritative

    # Rule 2: One authoritative + two primary = verified
    if len(authoritative) >= 1 and len(primary) >= 2:
        return True, authoritative + primary[:2]

    # Rule 3: Not enough high-trust sources
    return False, []

# Usage
is_verified, evidence = await verify_medical_fact(
    "Vitamin C prevents common cold"
)

if is_verified:
    print("✅ Fact verified by authoritative sources:")
    for item in evidence:
        print(f"  - {item['url']} (trust_tier={item['evidence'].trust_tier})")
else:
    print("❌ Insufficient authoritative evidence")
```

---

## Example 2: Knowledge Base Storage

### Scenario: Store information in BrainOS knowledge base

```python
async def store_in_knowledge_base(topic: str):
    """Store verified knowledge about a topic.

    Only stores information from PRIMARY_SOURCE or higher trust tier.
    """
    # Search for information
    search_results = await comm.execute(
        connector_type=ConnectorType.WEB_SEARCH,
        operation="search",
        params={"query": topic},
    )

    stored_count = 0
    rejected_count = 0

    for result in search_results.data['results']:
        url = result['url']

        # Fetch content
        content = await comm.execute(
            connector_type=ConnectorType.WEB_FETCH,
            operation="fetch",
            params={"url": url},
        )

        # Get trust tier
        evidence = await evidence_logger.get_evidence(content.evidence_id)

        # Decision: Can we store this?
        if evidence.trust_tier == TrustTier.SEARCH_RESULT:
            print(f"❌ Rejected: Search results cannot be stored as knowledge")
            print(f"   URL: {url}")
            rejected_count += 1
            continue

        if evidence.trust_tier == TrustTier.EXTERNAL_SOURCE:
            print(f"⚠️ Skipped: External source needs verification")
            print(f"   URL: {url}")
            rejected_count += 1
            continue

        # PRIMARY_SOURCE or AUTHORITATIVE_SOURCE - can store
        await brain_os.store_knowledge(
            topic=topic,
            content=content.data,
            source_url=url,
            trust_tier=evidence.trust_tier,
            evidence_id=evidence.id,
            timestamp=datetime.now(),
        )

        print(f"✅ Stored: {url} (trust_tier={evidence.trust_tier.value})")
        stored_count += 1

    print(f"\nSummary: {stored_count} stored, {rejected_count} rejected")

# Usage
await store_in_knowledge_base("Python asyncio patterns")
```

---

## Example 3: Decision-Making Framework

### Scenario: Make a decision based on external information

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Decision:
    """A decision with provenance tracking."""
    decision: str
    confidence: float
    supporting_evidence: List[str]
    trust_tiers: List[TrustTier]
    timestamp: datetime

async def make_informed_decision(question: str) -> Decision:
    """Make a decision with proper source verification.

    Confidence levels:
    - 0.9-1.0: Multiple authoritative sources
    - 0.7-0.9: Mix of authoritative and primary sources
    - 0.5-0.7: Primary sources only
    - 0.0-0.5: External sources (low confidence)
    """
    # Step 1: Gather candidate sources
    search_results = await comm.execute(
        connector_type=ConnectorType.WEB_SEARCH,
        operation="search",
        params={"query": question},
    )

    # Step 2: Fetch and verify sources
    evidence_list = []

    for result in search_results.data['results'][:5]:
        url = result['url']
        content = await comm.execute(
            connector_type=ConnectorType.WEB_FETCH,
            operation="fetch",
            params={"url": url},
        )

        evidence = await evidence_logger.get_evidence(content.evidence_id)
        evidence_list.append({
            'url': url,
            'content': content.data,
            'trust_tier': evidence.trust_tier,
        })

    # Step 3: Calculate confidence based on trust tiers
    trust_tiers = [e['trust_tier'] for e in evidence_list]

    authoritative_count = sum(
        1 for t in trust_tiers if t == TrustTier.AUTHORITATIVE_SOURCE
    )
    primary_count = sum(
        1 for t in trust_tiers if t == TrustTier.PRIMARY_SOURCE
    )

    if authoritative_count >= 2:
        confidence = 0.95
    elif authoritative_count >= 1 and primary_count >= 2:
        confidence = 0.85
    elif primary_count >= 3:
        confidence = 0.75
    elif primary_count >= 1:
        confidence = 0.60
    else:
        confidence = 0.30
        print("⚠️ WARNING: Low confidence - insufficient high-trust sources")

    # Step 4: Make decision
    # (In real implementation, use LLM to synthesize answer from sources)
    decision_text = "Decision based on verified sources..."

    return Decision(
        decision=decision_text,
        confidence=confidence,
        supporting_evidence=[e['url'] for e in evidence_list],
        trust_tiers=trust_tiers,
        timestamp=datetime.now(),
    )

# Usage
decision = await make_informed_decision("Is Python 3.14 released?")

print(f"Decision: {decision.decision}")
print(f"Confidence: {decision.confidence:.2%}")
print(f"\nSupporting evidence:")
for url, tier in zip(decision.supporting_evidence, decision.trust_tiers):
    print(f"  - {url} (trust_tier={tier.value})")

# Only act on high-confidence decisions
if decision.confidence >= 0.7:
    print("\n✅ Confidence sufficient for action")
else:
    print("\n❌ Confidence too low - manual review required")
```

---

## Example 4: Custom Domain Configuration

### Scenario: Add enterprise domains to trust lists

```python
from agentos.core.communication.evidence import EvidenceLogger

# Initialize with custom configuration
evidence_logger = EvidenceLogger()

# Add internal authoritative sources
evidence_logger.authoritative_domains.add("legal.company.com")
evidence_logger.authoritative_domains.add("compliance.company.com")
evidence_logger.authoritative_domains.add("security.company.com")

# Add internal primary sources
evidence_logger.primary_source_domains.add("docs.company.com")
evidence_logger.primary_source_domains.add("wiki.company.com")
evidence_logger.primary_source_domains.add("api.company.com")

# Now internal sources will have proper trust tiers
url = "https://legal.company.com/policies/data-protection"
trust_tier = evidence_logger.determine_trust_tier(
    url=url,
    connector_type=ConnectorType.WEB_FETCH,
)

print(f"Internal legal site trust tier: {trust_tier}")
# Output: AUTHORITATIVE_SOURCE

# Document configuration
config_doc = {
    "authoritative_domains": {
        "legal.company.com": "Legal and compliance team verified content",
        "compliance.company.com": "Regulatory compliance documentation",
        "security.company.com": "Security policies and procedures",
    },
    "primary_source_domains": {
        "docs.company.com": "Internal technical documentation",
        "wiki.company.com": "Internal knowledge base",
        "api.company.com": "API documentation and specs",
    },
    "review_frequency": "Quarterly",
    "last_updated": "2026-01-30",
}

# Save configuration for audit trail
with open("trust_tier_config.json", "w") as f:
    json.dump(config_doc, f, indent=2)
```

---

## Anti-Patterns to Avoid

### ❌ DON'T: Use search results as facts

```python
# WRONG - Using search snippet as fact
search_results = await comm.search("capital of France")
answer = search_results.data['results'][0]['snippet']
print(f"The answer is: {answer}")  # NEVER DO THIS!
```

### ✅ DO: Verify with high-trust sources

```python
# CORRECT - Fetch and verify sources
search_results = await comm.search("capital of France")

for result in search_results.data['results']:
    content = await comm.fetch(result['url'])
    evidence = await evidence_logger.get_evidence(content.evidence_id)

    if evidence.trust_tier >= TrustTier.PRIMARY_SOURCE:
        # Now can use the content
        answer = extract_answer(content.data)
        print(f"Verified answer: {answer}")
        print(f"Source: {result['url']} (trust_tier={evidence.trust_tier.value})")
        break
```

---

### ❌ DON'T: Store external sources without verification

```python
# WRONG - Storing without trust tier check
content = await comm.fetch("https://random-blog.com/article")
await brain_os.store_knowledge(content.data)  # DANGEROUS!
```

### ✅ DO: Check trust tier before storing

```python
# CORRECT - Verify trust tier first
content = await comm.fetch("https://random-blog.com/article")
evidence = await evidence_logger.get_evidence(content.evidence_id)

if evidence.trust_tier >= TrustTier.PRIMARY_SOURCE:
    await brain_os.store_knowledge(content.data)
elif evidence.trust_tier == TrustTier.EXTERNAL_SOURCE:
    print("⚠️ External source - needs corroboration")
    # Require 2+ sources before storing
else:
    print("❌ Cannot store search results")
```

---

### ❌ DON'T: Ignore trust tier in decision-making

```python
# WRONG - Making decisions without checking source reliability
content = await comm.fetch(url)
decision = make_decision(content.data)  # What's the source reliability?
```

### ✅ DO: Factor trust tier into decision confidence

```python
# CORRECT - Consider source reliability
content = await comm.fetch(url)
evidence = await evidence_logger.get_evidence(content.evidence_id)

if evidence.trust_tier >= TrustTier.PRIMARY_SOURCE:
    decision = make_decision(content.data, confidence=0.9)
elif evidence.trust_tier == TrustTier.EXTERNAL_SOURCE:
    decision = make_decision(content.data, confidence=0.5)
    print("⚠️ Low confidence - external source only")
else:
    raise ValueError("Cannot make decision based on search results")
```

---

## Testing Your Trust Tier Usage

```python
import pytest
from agentos.core.communication.models import TrustTier

def test_never_use_search_results_as_facts():
    """Test that code never treats search results as facts."""
    # Your code here should fetch and verify sources
    evidence = await evidence_logger.get_evidence(evidence_id)

    # Assert: Never use SEARCH_RESULT for decisions
    assert evidence.trust_tier != TrustTier.SEARCH_RESULT, (
        "Search results used as facts! This violates 'Search ≠ Truth' principle."
    )

def test_require_high_trust_for_knowledge_storage():
    """Test that only high-trust sources are stored in knowledge base."""
    evidence = await evidence_logger.get_evidence(evidence_id)

    # Assert: Only store PRIMARY_SOURCE or higher
    assert evidence.trust_tier >= TrustTier.PRIMARY_SOURCE, (
        "Attempted to store low-trust source in knowledge base"
    )

def test_decision_confidence_matches_trust_tier():
    """Test that decision confidence reflects source trust tier."""
    decision = await make_informed_decision(question)

    # High confidence requires high-trust sources
    if decision.confidence >= 0.9:
        assert any(
            t == TrustTier.AUTHORITATIVE_SOURCE
            for t in decision.trust_tiers
        ), "High confidence requires authoritative sources"
```

---

## Summary

### Key Principles

1. **Search ≠ Truth**: Search engines provide candidates, not verified facts
2. **Verify Before Use**: Always check trust tier before using information
3. **High Stakes, High Trust**: Critical decisions require PRIMARY_SOURCE or higher
4. **Document Provenance**: Always track source URLs and trust tiers
5. **Configuration Matters**: Maintain and review domain lists regularly

### Trust Tier Decision Matrix

| Use Case | Minimum Trust Tier | Notes |
|----------|-------------------|-------|
| Search/Discovery | SEARCH_RESULT | Starting point only |
| Casual Information | EXTERNAL_SOURCE | With 2+ source corroboration |
| Knowledge Base | PRIMARY_SOURCE | Can be cited with attribution |
| Decision-Making | PRIMARY_SOURCE | Requires source provenance |
| Critical Operations | AUTHORITATIVE_SOURCE | Government, academia, certified orgs |

---

## References

- ADR-COMM-001: CommunicationOS Boundary and Security Architecture
- CommunicationOS Security Guide: Trust Tier Decision Framework
- Test Suite: `agentos/core/communication/tests/test_trust_tier.py`

---

**Last Updated**: 2026-01-30
**Review Frequency**: Quarterly
