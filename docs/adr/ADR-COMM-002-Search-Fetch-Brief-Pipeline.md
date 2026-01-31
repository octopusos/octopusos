# ADR-COMM-002: SEARCH→FETCH→BRIEF Three-Stage Pipeline

**Status**: ACTIVE
**Date**: 2026-01-31
**Version**: 1.0.0
**Authors**: AgentOS Core Team
**Category**: Architecture Decision Record
**Scope**: CommunicationOS - Information Gathering Pipeline
**Supersedes**: None
**Related**: ADR-COMM-001 (CommunicationOS Boundary)

---

## Executive Summary

This ADR defines the **SEARCH→FETCH→BRIEF** three-stage pipeline for systematic external information gathering in AgentOS. This pipeline enforces a **strict separation of concerns** between candidate discovery (SEARCH), content retrieval (FETCH), and structured summarization (BRIEF), with mandatory phase gates and trust tier validation at each stage.

**Key Principles**:
- **Search ≠ Truth**: Search results are candidate sources, NOT verified facts
- **Phase isolation**: Each stage has strictly defined allowed and forbidden operations
- **Trust tier enforcement**: Information must progress through validation gates
- **Audit completeness**: Every stage generates evidence records
- **No shortcuts**: Brief stage CANNOT proceed without fetched documents

**Pipeline Flow**:
```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  SEARCH  │───▶│  FETCH   │───▶│  BRIEF   │
│ (Tier 0) │    │ (Tier 2) │    │ (Output) │
└──────────┘    └──────────┘    └──────────┘
 Discover        Retrieve        Summarize
 candidates      content         findings
```

---

## Context

### Problem Statement

AI agents gathering information from the web face critical challenges:

1. **Search engines optimize for relevance, not truth**
   - Snippets can be misleading, out-of-context, or outdated
   - SEO manipulation and disinformation campaigns affect rankings
   - Results change over time, creating unreproducible findings

2. **Trust confusion**
   - Agents may treat search results as verified facts
   - Skipping content fetching leads to unverified claims
   - Mixing trust levels creates ambiguous provenance

3. **Audit gaps**
   - If agents directly use search snippets, no evidence trail exists
   - Cannot reproduce decision rationale or verify information sources
   - Compliance requirements (GDPR, SOC 2) demand traceable evidence

4. **Policy violations**
   - Without phase separation, agents can generate summaries from unverified data
   - No gate to enforce "fetch before brief" rule
   - Difficult to detect when agents skip verification steps

### Why a Three-Stage Pipeline?

**Anti-pattern (Single-stage)**:
```python
# ❌ WRONG: Using search results directly as facts
results = await comm.search("capital of France")
answer = results[0]['snippet']  # NOT VERIFIED!
return f"The capital is {answer}"
```

**Correct Pattern (Three-stage)**:
```python
# ✅ CORRECT: Systematic verification pipeline

# Stage 1: SEARCH - Discover candidates
search_results = await comm.search("capital of France")
# trust_tier = SEARCH_RESULT (lowest)

# Stage 2: FETCH - Retrieve actual content
documents = []
for url in [r['url'] for r in search_results[:5]]:
    doc = await comm.fetch(url)
    documents.append(doc)
    # trust_tier = VERIFIED_SOURCE (medium-high)

# Stage 3: BRIEF - Structured summary
brief = await comm.brief(
    question="What is the capital of France?",
    documents=documents,
    min_sources=2
)
# brief includes provenance from verified sources
```

### Real-World Scenarios

**Scenario 1: Medical Information Gathering**
```
User: "What are the side effects of aspirin?"

Wrong approach:
- Search "aspirin side effects"
- Return snippet from first result (unverified blog post)
- RISK: Medical misinformation

Correct approach:
- SEARCH: Find candidate sources (NIH, Mayo Clinic, FDA)
- FETCH: Retrieve full content from authoritative sources
- BRIEF: Synthesize information with citations to verified sources
- OUTPUT: "According to NIH.gov (fetched 2026-01-31)..."
```

**Scenario 2: Technical Documentation Research**
```
User: "How do I configure Kubernetes ingress?"

Wrong approach:
- Search "kubernetes ingress config"
- Copy-paste snippet from search result
- RISK: Outdated or incorrect instructions

Correct approach:
- SEARCH: Find official Kubernetes docs, GitHub repos
- FETCH: Pull latest documentation pages
- BRIEF: Extract relevant sections with version information
- OUTPUT: "From kubernetes.io/docs/v1.28 (accessed today)..."
```

---

## Decision

### 1. Pipeline Architecture

#### Stage Definitions

```
┌─────────────────────────────────────────────────────────────┐
│                   Three-Stage Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐                                         │
│  │  SEARCH STAGE   │                                         │
│  │  (Discovery)    │                                         │
│  ├─────────────────┤                                         │
│  │ Input:  query   │                                         │
│  │ Output: URLs +  │                                         │
│  │         metadata│                                         │
│  │ Trust:  Tier 0  │ ← SEARCH_RESULT (candidates only)      │
│  └────────┬────────┘                                         │
│           │ Phase Gate 1: URL validation                     │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │  FETCH STAGE    │                                         │
│  │  (Retrieval)    │                                         │
│  ├─────────────────┤                                         │
│  │ Input:  URLs    │                                         │
│  │ Output: Raw     │                                         │
│  │         content │                                         │
│  │ Trust:  Tier 2+ │ ← VERIFIED_SOURCE                      │
│  └────────┬────────┘                                         │
│           │ Phase Gate 2: Minimum N documents               │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │  BRIEF STAGE    │                                         │
│  │  (Synthesis)    │                                         │
│  ├─────────────────┤                                         │
│  │ Input:  Docs    │                                         │
│  │ Output: Summary │                                         │
│  │ Trust:  Inherit │ ← From source documents                │
│  └─────────────────┘                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### Stage 1: SEARCH (Discovery)

**Purpose**: Discover candidate information sources.

**Allowed Operations**:
- Query search engines (DuckDuckGo, Google, Bing)
- Return search result metadata: `url`, `title`, `snippet`, `domain`, `rank`
- Extract domain and URL information
- Basic relevance filtering (deduplication, domain filtering)

**Forbidden Operations**:
- ❌ Summarization or content analysis
- ❌ Fact extraction or conclusion drawing
- ❌ Value judgments ("this source is authoritative")
- ❌ Rewriting or paraphrasing snippets
- ❌ Merging information from multiple snippets
- ❌ Inferring facts not explicitly in metadata

**Output Schema**:
```python
@dataclass
class SearchResult:
    """Single search result (candidate source)."""

    url: str                    # Source URL
    title: str                  # Page title
    snippet: str                # Short excerpt (as-is from search engine)
    domain: str                 # Extracted domain
    rank: int                   # Result position
    search_engine: str          # Source search engine
    trust_tier: TrustTier       # ALWAYS SEARCH_RESULT
    metadata: Dict[str, Any]    # Additional metadata
    timestamp: datetime         # When search was performed

@dataclass
class SearchResultList:
    """Collection of search results from SEARCH stage."""

    query: str                      # Original query
    results: List[SearchResult]     # Search results
    total_results: int              # Total available results
    search_engine: str              # Search engine used
    trust_tier: TrustTier           # ALWAYS SEARCH_RESULT
    evidence_id: str                # Audit trail reference
    timestamp: datetime             # When search was performed
```

**Trust Tier**: `SEARCH_RESULT` (Tier 0 - lowest trust)

**Evidence Record**:
```python
{
    "stage": "SEARCH",
    "operation": "search",
    "request": {
        "query": "user query string",
        "max_results": 10,
        "search_engine": "duckduckgo"
    },
    "response": {
        "result_count": 10,
        "top_domains": ["example.com", "docs.example.org"],
        "urls": ["url1", "url2", ...]  # Full list
    },
    "trust_tier": "SEARCH_RESULT",
    "phase_gate_passed": True,
    "timestamp": "2026-01-31T12:00:00Z"
}
```

#### Stage 2: FETCH (Retrieval)

**Purpose**: Retrieve actual content from candidate URLs.

**Allowed Operations**:
- Fetch full HTML/text content from URLs
- Parse document structure (headings, paragraphs, tables)
- Extract metadata (author, publish date, last modified)
- Content-type detection (HTML, PDF, JSON, XML)
- Character encoding detection and normalization
- Basic content cleaning (remove ads, navigation elements)

**Forbidden Operations**:
- ❌ Summarization or content analysis
- ❌ Fact verification or conclusion drawing
- ❌ Value judgments or quality assessment
- ❌ Sentiment analysis or opinion extraction
- ❌ Merging content from multiple documents
- ❌ Generating new text not present in source

**Output Schema**:
```python
@dataclass
class FetchedDocument:
    """Single fetched document from FETCH stage."""

    url: str                        # Source URL
    title: str                      # Document title
    content: str                    # Full text content (cleaned)
    html_content: Optional[str]     # Raw HTML (if applicable)
    author: Optional[str]           # Document author
    publish_date: Optional[datetime] # Publication date
    last_modified: Optional[datetime] # Last modified date
    content_type: str               # MIME type
    word_count: int                 # Content length
    domain: str                     # Source domain
    trust_tier: TrustTier           # Determined by domain/source
    metadata: Dict[str, Any]        # Additional metadata
    fetch_timestamp: datetime       # When fetch was performed
    evidence_id: str                # Audit trail reference

@dataclass
class FetchedDocumentList:
    """Collection of fetched documents from FETCH stage."""

    documents: List[FetchedDocument]    # Fetched documents
    source_query: Optional[str]         # Original query (if from SEARCH)
    fetch_count: int                    # Number of successful fetches
    failed_urls: List[str]              # URLs that failed to fetch
    timestamp: datetime                 # When fetch batch completed
```

**Trust Tier**: Determined by source domain
- `AUTHORITATIVE_SOURCE` (Tier 3): `.gov`, `.edu`, WHO, UN, scientific publishers
- `PRIMARY_SOURCE` (Tier 2): Official docs, original publishers, verified sources
- `EXTERNAL_SOURCE` (Tier 1): General websites (needs verification)

**Evidence Record**:
```python
{
    "stage": "FETCH",
    "operation": "fetch",
    "request": {
        "url": "https://example.com/article",
        "source": "search_result_123"  # Link to SEARCH stage
    },
    "response": {
        "title": "Article Title",
        "word_count": 1500,
        "content_type": "text/html",
        "author": "John Doe",
        "publish_date": "2026-01-15"
    },
    "trust_tier": "PRIMARY_SOURCE",
    "domain": "example.com",
    "phase_gate_passed": True,
    "timestamp": "2026-01-31T12:01:30Z"
}
```

#### Stage 3: BRIEF (Synthesis)

**Purpose**: Generate structured summary from verified documents.

**Allowed Operations**:
- Structured summarization of fetched documents
- Information extraction and categorization
- Cross-reference analysis (comparing multiple sources)
- Citation and provenance tracking
- Formatting output (markdown, JSON, structured text)
- Confidence scoring based on source agreement

**Forbidden Operations**:
- ❌ Introducing information NOT in fetched documents
- ❌ Using search snippets directly (must be from fetched content)
- ❌ Making claims without source attribution
- ❌ Inferring facts beyond source material
- ❌ Proceeding without minimum number of verified sources

**Input Requirements**:
- **Minimum sources**: At least N fetched documents (configurable, default N=2)
- **Trust tier requirement**: All documents must be `VERIFIED_SOURCE` or higher
  - `VERIFIED_SOURCE` = `EXTERNAL_SOURCE` | `PRIMARY_SOURCE` | `AUTHORITATIVE_SOURCE`
  - `SEARCH_RESULT` is NOT accepted
- **Evidence trail**: All input documents must have evidence records

**Output Schema**:
```python
@dataclass
class BriefSection:
    """Single section in a brief."""

    heading: str                    # Section title
    content: str                    # Summarized content
    sources: List[str]              # Source URLs for this section
    confidence: float               # Confidence score (0.0-1.0)

@dataclass
class BriefCitation:
    """Citation for a source document."""

    url: str                        # Source URL
    title: str                      # Document title
    author: Optional[str]           # Author name
    publish_date: Optional[datetime] # Publication date
    access_date: datetime           # When we fetched it
    trust_tier: TrustTier           # Trust level
    excerpt: Optional[str]          # Relevant excerpt

@dataclass
class Brief:
    """Structured summary from BRIEF stage."""

    query: str                      # Original question/query
    summary: str                    # Executive summary
    sections: List[BriefSection]    # Detailed sections
    citations: List[BriefCitation]  # Source citations
    total_sources: int              # Number of sources used
    trust_tier_distribution: Dict[str, int]  # Count by trust tier
    confidence_score: float         # Overall confidence (0.0-1.0)
    evidence_chain: List[str]       # Evidence IDs from SEARCH→FETCH→BRIEF
    timestamp: datetime             # When brief was generated
    evidence_id: str                # Audit trail reference
```

**Trust Tier**: Inherits from input documents (lowest tier used)

**Evidence Record**:
```python
{
    "stage": "BRIEF",
    "operation": "brief",
    "request": {
        "query": "user query string",
        "document_ids": ["doc1", "doc2", "doc3"],
        "min_sources": 2
    },
    "response": {
        "summary_length": 500,
        "sections_count": 3,
        "sources_used": 3,
        "trust_tier_distribution": {
            "AUTHORITATIVE_SOURCE": 1,
            "PRIMARY_SOURCE": 2
        }
    },
    "trust_tier": "PRIMARY_SOURCE",  # Lowest tier from inputs
    "evidence_chain": [
        "search_evidence_123",
        "fetch_evidence_456",
        "fetch_evidence_457",
        "fetch_evidence_458"
    ],
    "phase_gate_passed": True,
    "timestamp": "2026-01-31T12:05:00Z"
}
```

---

### 2. Phase Gates

Phase gates are **mandatory validation checkpoints** between stages. Gates MUST pass before proceeding to the next stage.

#### Phase Gate 1: SEARCH → FETCH

**Validation Rules**:

```python
def validate_search_to_fetch(search_results: SearchResultList) -> GateResult:
    """Validate SEARCH output before FETCH stage.

    Returns:
        GateResult with pass/fail status and reason
    """
    errors = []

    # Rule 1: Trust tier must be SEARCH_RESULT
    if search_results.trust_tier != TrustTier.SEARCH_RESULT:
        errors.append(
            f"Invalid trust tier: {search_results.trust_tier}. "
            f"SEARCH stage must produce SEARCH_RESULT tier."
        )

    # Rule 2: Must have at least 1 result
    if len(search_results.results) == 0:
        errors.append("No search results found. Cannot proceed to FETCH.")

    # Rule 3: All URLs must be valid and safe
    for result in search_results.results:
        if not is_valid_url(result.url):
            errors.append(f"Invalid URL: {result.url}")

        if is_ssrf_risk(result.url):
            errors.append(f"SSRF risk detected: {result.url}")

    # Rule 4: Must have evidence record
    if not search_results.evidence_id:
        errors.append("Missing evidence record for SEARCH stage.")

    if errors:
        return GateResult(
            passed=False,
            stage_from="SEARCH",
            stage_to="FETCH",
            errors=errors,
            timestamp=datetime.now(timezone.utc)
        )

    return GateResult(
        passed=True,
        stage_from="SEARCH",
        stage_to="FETCH",
        errors=[],
        timestamp=datetime.now(timezone.utc)
    )
```

**Enforcement**:
- Gate check is MANDATORY before any FETCH operation
- Failed gate BLOCKS execution and logs error evidence
- Gate result is recorded in audit trail

#### Phase Gate 2: FETCH → BRIEF

**Validation Rules**:

```python
def validate_fetch_to_brief(
    documents: FetchedDocumentList,
    min_sources: int = 2
) -> GateResult:
    """Validate FETCH output before BRIEF stage.

    Args:
        documents: Fetched documents
        min_sources: Minimum required sources (default 2)

    Returns:
        GateResult with pass/fail status and reason
    """
    errors = []
    warnings = []

    # Rule 1: Minimum source requirement
    if len(documents.documents) < min_sources:
        errors.append(
            f"Insufficient sources: {len(documents.documents)} < {min_sources}. "
            f"Brief requires at least {min_sources} fetched documents."
        )

    # Rule 2: No SEARCH_RESULT tier documents
    search_tier_docs = [
        doc for doc in documents.documents
        if doc.trust_tier == TrustTier.SEARCH_RESULT
    ]
    if search_tier_docs:
        errors.append(
            f"Found {len(search_tier_docs)} SEARCH_RESULT tier documents. "
            f"BRIEF stage requires VERIFIED_SOURCE tier or higher. "
            f"URLs: {[d.url for d in search_tier_docs]}"
        )

    # Rule 3: All documents must have evidence records
    missing_evidence = [
        doc.url for doc in documents.documents
        if not doc.evidence_id
    ]
    if missing_evidence:
        errors.append(
            f"Missing evidence records for: {missing_evidence}"
        )

    # Rule 4: Content quality checks
    for doc in documents.documents:
        # Minimum content length (avoid empty or stub pages)
        if doc.word_count < 50:
            warnings.append(
                f"Low content quality: {doc.url} has only {doc.word_count} words"
            )

        # Fetch must be recent (not stale cached data)
        age_hours = (datetime.now(timezone.utc) - doc.fetch_timestamp).total_seconds() / 3600
        if age_hours > 24:
            warnings.append(
                f"Stale content: {doc.url} fetched {age_hours:.1f} hours ago"
            )

    # Rule 5: Trust tier diversity (warning only)
    tier_counts = {}
    for doc in documents.documents:
        tier = doc.trust_tier.value
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    if len(tier_counts) == 1 and TrustTier.EXTERNAL_SOURCE in [d.trust_tier for d in documents.documents]:
        warnings.append(
            "All sources are EXTERNAL_SOURCE tier. "
            "Consider including AUTHORITATIVE or PRIMARY sources for higher confidence."
        )

    if errors:
        return GateResult(
            passed=False,
            stage_from="FETCH",
            stage_to="BRIEF",
            errors=errors,
            warnings=warnings,
            timestamp=datetime.now(timezone.utc)
        )

    return GateResult(
        passed=True,
        stage_from="FETCH",
        stage_to="BRIEF",
        errors=[],
        warnings=warnings,
        timestamp=datetime.now(timezone.utc)
    )
```

**Enforcement**:
- Gate check is MANDATORY before any BRIEF operation
- Failed gate BLOCKS execution and returns error
- Warnings are logged but do not block execution
- Gate result is recorded in audit trail

---

### 3. Data Models

#### Core Pipeline Models

```python
# Located in: agentos/core/communication/pipeline/models.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from agentos.core.communication.models import TrustTier


class PipelineStage(str, Enum):
    """Pipeline stage identifier."""
    SEARCH = "search"
    FETCH = "fetch"
    BRIEF = "brief"


@dataclass
class GateResult:
    """Result of a phase gate validation."""

    passed: bool                    # Did validation pass?
    stage_from: str                 # Source stage
    stage_to: str                   # Target stage
    errors: List[str]               # Blocking errors
    warnings: List[str] = field(default_factory=list)  # Non-blocking warnings
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "stage_from": self.stage_from,
            "stage_to": self.stage_to,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SearchResult:
    """Single search result from SEARCH stage."""

    url: str
    title: str
    snippet: str
    domain: str
    rank: int
    search_engine: str
    trust_tier: TrustTier = TrustTier.SEARCH_RESULT  # Always SEARCH_RESULT
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "domain": self.domain,
            "rank": self.rank,
            "search_engine": self.search_engine,
            "trust_tier": self.trust_tier.value,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SearchResultList:
    """Collection of search results from SEARCH stage."""

    query: str
    results: List[SearchResult]
    total_results: int
    search_engine: str
    trust_tier: TrustTier = TrustTier.SEARCH_RESULT  # Always SEARCH_RESULT
    evidence_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "search_engine": self.search_engine,
            "trust_tier": self.trust_tier.value,
            "evidence_id": self.evidence_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class FetchedDocument:
    """Single fetched document from FETCH stage."""

    url: str
    title: str
    content: str
    html_content: Optional[str] = None
    author: Optional[str] = None
    publish_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    content_type: str = "text/html"
    word_count: int = 0
    domain: str = ""
    trust_tier: TrustTier = TrustTier.EXTERNAL_SOURCE
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetch_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_id: Optional[str] = None

    def __post_init__(self):
        """Calculate derived fields."""
        if not self.word_count:
            self.word_count = len(self.content.split())
        if not self.domain:
            from urllib.parse import urlparse
            self.domain = urlparse(self.url).netloc

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "html_content": self.html_content,
            "author": self.author,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "last_modified": self.last_modified.isoformat() if self.last_modified else None,
            "content_type": self.content_type,
            "word_count": self.word_count,
            "domain": self.domain,
            "trust_tier": self.trust_tier.value,
            "metadata": self.metadata,
            "fetch_timestamp": self.fetch_timestamp.isoformat(),
            "evidence_id": self.evidence_id
        }


@dataclass
class FetchedDocumentList:
    """Collection of fetched documents from FETCH stage."""

    documents: List[FetchedDocument]
    source_query: Optional[str] = None
    fetch_count: int = 0
    failed_urls: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Calculate derived fields."""
        if not self.fetch_count:
            self.fetch_count = len(self.documents)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documents": [d.to_dict() for d in self.documents],
            "source_query": self.source_query,
            "fetch_count": self.fetch_count,
            "failed_urls": self.failed_urls,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class BriefSection:
    """Single section in a brief."""

    heading: str
    content: str
    sources: List[str]  # URLs
    confidence: float = 1.0  # 0.0-1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heading": self.heading,
            "content": self.content,
            "sources": self.sources,
            "confidence": self.confidence
        }


@dataclass
class BriefCitation:
    """Citation for a source document."""

    url: str
    title: str
    author: Optional[str] = None
    publish_date: Optional[datetime] = None
    access_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trust_tier: TrustTier = TrustTier.EXTERNAL_SOURCE
    excerpt: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "access_date": self.access_date.isoformat(),
            "trust_tier": self.trust_tier.value,
            "excerpt": self.excerpt
        }


@dataclass
class Brief:
    """Structured summary from BRIEF stage."""

    query: str
    summary: str
    sections: List[BriefSection] = field(default_factory=list)
    citations: List[BriefCitation] = field(default_factory=list)
    total_sources: int = 0
    trust_tier_distribution: Dict[str, int] = field(default_factory=dict)
    confidence_score: float = 0.0
    evidence_chain: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_id: Optional[str] = None

    def __post_init__(self):
        """Calculate derived fields."""
        if not self.total_sources:
            self.total_sources = len(self.citations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "summary": self.summary,
            "sections": [s.to_dict() for s in self.sections],
            "citations": [c.to_dict() for c in self.citations],
            "total_sources": self.total_sources,
            "trust_tier_distribution": self.trust_tier_distribution,
            "confidence_score": self.confidence_score,
            "evidence_chain": self.evidence_chain,
            "timestamp": self.timestamp.isoformat(),
            "evidence_id": self.evidence_id
        }
```

---

### 4. Trust Tier Definitions

Trust tiers are used throughout the pipeline to track information provenance and enforce verification requirements.

#### Trust Tier Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                    Trust Tier Pyramid                       │
├─────────────────────────────────────────────────────────────┤
│  Tier 3: AUTHORITATIVE_SOURCE                               │
│  ├─ Government (.gov, .gov.cn), Academia (.edu, .ac.uk)     │
│  ├─ International orgs (WHO, UN, UNESCO)                    │
│  ├─ Standards bodies (W3C, IETF, IEEE, ISO)                 │
│  └─ Scientific publishers (Nature, Science)                 │
│  Usage: High-confidence facts, knowledge base storage       │
│  Decision-making: Approved with audit trail                 │
├─────────────────────────────────────────────────────────────┤
│  Tier 2: PRIMARY_SOURCE                                     │
│  ├─ Official documentation (docs.python.org, kubernetes.io) │
│  ├─ Original publishers (Reuters, AP, BBC)                  │
│  ├─ Verified repositories (GitHub official repos)           │
│  └─ Company official sites (for own products)               │
│  Usage: Can be cited with attribution                       │
│  Decision-making: Verify critical facts                     │
├─────────────────────────────────────────────────────────────┤
│  Tier 1: EXTERNAL_SOURCE                                    │
│  ├─ General websites, blogs, forums                         │
│  ├─ News aggregators, social media                          │
│  ├─ Company websites (general content)                      │
│  └─ Wikipedia, Wikis (needs verification)                   │
│  Usage: Candidate information, needs cross-referencing      │
│  Decision-making: Verify before use                         │
├─────────────────────────────────────────────────────────────┤
│  Tier 0: SEARCH_RESULT                                      │
│  ├─ Search engine results (DuckDuckGo, Google, Bing)        │
│  ├─ Snippets, descriptions, metadata only                   │
│  └─ NO ACTUAL CONTENT FETCHED                               │
│  Usage: Starting point for investigation only               │
│  Decision-making: NEVER use as facts                        │
└─────────────────────────────────────────────────────────────┘
```

#### Trust Tier Usage in Pipeline

| Stage | Input Trust Tier | Output Trust Tier | Gate Requirement |
|-------|------------------|-------------------|------------------|
| SEARCH | N/A | SEARCH_RESULT | N/A |
| FETCH | SEARCH_RESULT (URLs) | EXTERNAL/PRIMARY/AUTHORITATIVE | URLs must be valid |
| BRIEF | VERIFIED_SOURCE (≥Tier 1) | Inherited from lowest input | Min N documents, no Tier 0 |

**VERIFIED_SOURCE Definition**:
```python
VERIFIED_SOURCE = {
    TrustTier.EXTERNAL_SOURCE,      # Tier 1
    TrustTier.PRIMARY_SOURCE,       # Tier 2
    TrustTier.AUTHORITATIVE_SOURCE  # Tier 3
}
# SEARCH_RESULT (Tier 0) is NOT in VERIFIED_SOURCE
```

#### Trust Tier Determination Algorithm

Trust tier is determined automatically in the FETCH stage based on source domain:

```python
def determine_trust_tier(url: str) -> TrustTier:
    """Determine trust tier based on URL domain.

    Algorithm:
    1. Extract domain from URL
    2. Check government TLDs (.gov, .gov.cn)
    3. Check academic TLDs (.edu, .ac.uk)
    4. Check authoritative domain list
    5. Check primary source domain list
    6. Default to EXTERNAL_SOURCE

    Args:
        url: The URL to evaluate

    Returns:
        TrustTier: The determined trust tier
    """
    from urllib.parse import urlparse

    domain = urlparse(url).netloc.lower()

    # Remove port and www prefix
    domain = domain.split(':')[0]
    if domain.startswith('www.'):
        domain = domain[4:]

    # Tier 3: Government
    if domain.endswith('.gov') or domain.endswith('.gov.cn'):
        return TrustTier.AUTHORITATIVE_SOURCE

    # Tier 3: Academia
    if domain.endswith('.edu') or domain.endswith('.ac.uk'):
        return TrustTier.AUTHORITATIVE_SOURCE

    # Tier 3: Authoritative domain list
    if domain in AUTHORITATIVE_DOMAINS:
        return TrustTier.AUTHORITATIVE_SOURCE

    # Tier 2: Primary source domain list
    if domain in PRIMARY_SOURCE_DOMAINS:
        return TrustTier.PRIMARY_SOURCE

    # Tier 1: Default (external source)
    return TrustTier.EXTERNAL_SOURCE
```

**Domain Lists** (maintained in `agentos/core/communication/evidence.py`):

```python
AUTHORITATIVE_DOMAINS = {
    # Government
    "whitehouse.gov", "state.gov", "defense.gov", "nih.gov", "cdc.gov",
    "fda.gov", "sec.gov", "ftc.gov", "dhs.gov", "justice.gov",
    # International
    "europa.eu", "who.int", "un.org", "unesco.org", "unicef.org",
    # Academia (non-TLD)
    "mit.edu", "stanford.edu", "harvard.edu", "berkeley.edu",
    "oxford.ac.uk", "cambridge.ac.uk",
    # Standards bodies
    "w3.org", "ietf.org", "ieee.org", "iso.org",
    # Scientific publishers
    "nature.com", "science.org", "sciencedirect.com", "plos.org",
}

PRIMARY_SOURCE_DOMAINS = {
    # Tech documentation
    "docs.python.org", "docs.microsoft.com", "developer.apple.com",
    "developer.mozilla.org", "docs.github.com", "cloud.google.com",
    "docs.aws.amazon.com", "kubernetes.io", "docker.com", "nodejs.org",
    # News organizations
    "reuters.com", "apnews.com", "bbc.com", "npr.org", "pbs.org",
    # Open source projects
    "github.com", "gitlab.com", "apache.org", "gnu.org",
}
```

---

### 5. Implementation Architecture

#### Service Interface

```python
# Located in: agentos/core/communication/pipeline/service.py

from typing import List, Optional
from agentos.core.communication.pipeline.models import (
    SearchResultList, FetchedDocumentList, Brief, GateResult
)


class PipelineService:
    """Service for executing the three-stage information gathering pipeline."""

    def __init__(
        self,
        communication_service: CommunicationService,
        min_sources: int = 2,
        enforce_gates: bool = True
    ):
        """Initialize pipeline service.

        Args:
            communication_service: Underlying communication service
            min_sources: Minimum sources required for BRIEF stage
            enforce_gates: Whether to enforce phase gates (default True)
        """
        self.comm = communication_service
        self.min_sources = min_sources
        self.enforce_gates = enforce_gates

    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_engine: str = "duckduckgo"
    ) -> SearchResultList:
        """Execute SEARCH stage.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            search_engine: Search engine to use

        Returns:
            SearchResultList: Search results with trust_tier=SEARCH_RESULT

        Raises:
            PipelineError: If search fails
        """
        pass

    async def fetch(
        self,
        urls: List[str],
        source_query: Optional[str] = None
    ) -> FetchedDocumentList:
        """Execute FETCH stage.

        Args:
            urls: List of URLs to fetch
            source_query: Original query (for evidence linking)

        Returns:
            FetchedDocumentList: Fetched documents with appropriate trust tiers

        Raises:
            PipelineError: If fetch fails
        """
        pass

    async def brief(
        self,
        query: str,
        documents: FetchedDocumentList,
        format: str = "structured"
    ) -> Brief:
        """Execute BRIEF stage.

        Args:
            query: Original question/query
            documents: Fetched documents to summarize
            format: Output format (structured, markdown, json)

        Returns:
            Brief: Structured summary with citations

        Raises:
            PipelineError: If brief fails
            PhaseGateError: If phase gate validation fails
        """
        pass

    async def execute_full_pipeline(
        self,
        query: str,
        max_search_results: int = 10,
        max_fetch_urls: int = 5
    ) -> Brief:
        """Execute full SEARCH→FETCH→BRIEF pipeline.

        Args:
            query: User query
            max_search_results: Max results from SEARCH stage
            max_fetch_urls: Max URLs to fetch from search results

        Returns:
            Brief: Final brief with full evidence chain

        Raises:
            PipelineError: If any stage fails
            PhaseGateError: If phase gate validation fails
        """
        # Stage 1: SEARCH
        search_results = await self.search(query, max_results=max_search_results)

        # Phase Gate 1: Validate SEARCH → FETCH
        gate1 = validate_search_to_fetch(search_results)
        if self.enforce_gates and not gate1.passed:
            raise PhaseGateError(gate1)

        # Stage 2: FETCH
        urls = [r.url for r in search_results.results[:max_fetch_urls]]
        documents = await self.fetch(urls, source_query=query)

        # Phase Gate 2: Validate FETCH → BRIEF
        gate2 = validate_fetch_to_brief(documents, min_sources=self.min_sources)
        if self.enforce_gates and not gate2.passed:
            raise PhaseGateError(gate2)

        # Stage 3: BRIEF
        brief = await self.brief(query, documents)

        return brief
```

#### Phase Gate Implementation

```python
# Located in: agentos/core/communication/pipeline/gates.py

from typing import List
from urllib.parse import urlparse
import re
from agentos.core.communication.pipeline.models import (
    SearchResultList, FetchedDocumentList, GateResult
)
from agentos.core.communication.models import TrustTier


def is_valid_url(url: str) -> bool:
    """Check if URL is valid and well-formed."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def is_ssrf_risk(url: str) -> bool:
    """Check if URL poses SSRF risk."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return True

        # Block localhost
        if hostname in ['localhost', '127.0.0.1', '::1']:
            return True

        # Block private IP ranges
        if hostname.startswith('10.') or hostname.startswith('192.168.'):
            return True

        if hostname.startswith('172.'):
            octets = hostname.split('.')
            if len(octets) >= 2 and 16 <= int(octets[1]) <= 31:
                return True

        # Block link-local
        if hostname.startswith('169.254.'):
            return True

        return False
    except:
        return True


def validate_search_to_fetch(search_results: SearchResultList) -> GateResult:
    """Validate SEARCH output before FETCH stage."""
    errors = []

    # Rule 1: Trust tier must be SEARCH_RESULT
    if search_results.trust_tier != TrustTier.SEARCH_RESULT:
        errors.append(
            f"Invalid trust tier: {search_results.trust_tier}. "
            f"SEARCH stage must produce SEARCH_RESULT tier."
        )

    # Rule 2: Must have at least 1 result
    if len(search_results.results) == 0:
        errors.append("No search results found. Cannot proceed to FETCH.")

    # Rule 3: All URLs must be valid and safe
    for result in search_results.results:
        if not is_valid_url(result.url):
            errors.append(f"Invalid URL: {result.url}")

        if is_ssrf_risk(result.url):
            errors.append(f"SSRF risk detected: {result.url}")

    # Rule 4: Must have evidence record
    if not search_results.evidence_id:
        errors.append("Missing evidence record for SEARCH stage.")

    if errors:
        return GateResult(
            passed=False,
            stage_from="SEARCH",
            stage_to="FETCH",
            errors=errors
        )

    return GateResult(
        passed=True,
        stage_from="SEARCH",
        stage_to="FETCH",
        errors=[]
    )


def validate_fetch_to_brief(
    documents: FetchedDocumentList,
    min_sources: int = 2
) -> GateResult:
    """Validate FETCH output before BRIEF stage."""
    errors = []
    warnings = []

    # Rule 1: Minimum source requirement
    if len(documents.documents) < min_sources:
        errors.append(
            f"Insufficient sources: {len(documents.documents)} < {min_sources}. "
            f"Brief requires at least {min_sources} fetched documents."
        )

    # Rule 2: No SEARCH_RESULT tier documents
    search_tier_docs = [
        doc for doc in documents.documents
        if doc.trust_tier == TrustTier.SEARCH_RESULT
    ]
    if search_tier_docs:
        errors.append(
            f"Found {len(search_tier_docs)} SEARCH_RESULT tier documents. "
            f"BRIEF stage requires VERIFIED_SOURCE tier or higher. "
            f"URLs: {[d.url for d in search_tier_docs]}"
        )

    # Rule 3: All documents must have evidence records
    missing_evidence = [
        doc.url for doc in documents.documents
        if not doc.evidence_id
    ]
    if missing_evidence:
        errors.append(
            f"Missing evidence records for: {missing_evidence}"
        )

    # Rule 4: Content quality checks
    for doc in documents.documents:
        if doc.word_count < 50:
            warnings.append(
                f"Low content quality: {doc.url} has only {doc.word_count} words"
            )

    # Rule 5: Trust tier diversity (warning only)
    tier_counts = {}
    for doc in documents.documents:
        tier = doc.trust_tier.value
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    if len(tier_counts) == 1 and TrustTier.EXTERNAL_SOURCE in [d.trust_tier for d in documents.documents]:
        warnings.append(
            "All sources are EXTERNAL_SOURCE tier. "
            "Consider including AUTHORITATIVE or PRIMARY sources."
        )

    if errors:
        return GateResult(
            passed=False,
            stage_from="FETCH",
            stage_to="BRIEF",
            errors=errors,
            warnings=warnings
        )

    return GateResult(
        passed=True,
        stage_from="FETCH",
        stage_to="BRIEF",
        errors=[],
        warnings=warnings
    )


class PhaseGateError(Exception):
    """Raised when a phase gate validation fails."""

    def __init__(self, gate_result: GateResult):
        self.gate_result = gate_result
        message = (
            f"Phase gate {gate_result.stage_from}→{gate_result.stage_to} failed:\n"
            + "\n".join(f"  - {err}" for err in gate_result.errors)
        )
        super().__init__(message)
```

---

### 6. Configuration

Pipeline behavior can be configured through policies and parameters:

```python
# Configuration example

pipeline_config = {
    # SEARCH stage configuration
    "search": {
        "default_engine": "duckduckgo",
        "max_results": 10,
        "timeout_seconds": 30,
        "cache_ttl_hours": 24
    },

    # FETCH stage configuration
    "fetch": {
        "max_parallel_fetches": 5,
        "timeout_seconds": 60,
        "max_content_size_mb": 10,
        "retry_on_failure": True,
        "max_retries": 3
    },

    # BRIEF stage configuration
    "brief": {
        "min_sources": 2,
        "format": "structured",  # structured | markdown | json
        "include_citations": True,
        "max_summary_length": 500
    },

    # Phase gate configuration
    "gates": {
        "enforce_gates": True,
        "min_content_words": 50,
        "max_stale_hours": 24
    },

    # Trust tier configuration
    "trust": {
        "authoritative_domains_file": "/path/to/authoritative_domains.txt",
        "primary_source_domains_file": "/path/to/primary_domains.txt",
        "auto_update_domain_lists": False
    }
}
```

---

## Consequences

### Positive Consequences

1. **Information Quality Assurance**
   - Eliminates reliance on unverified search snippets
   - Enforces content fetching before summarization
   - Provides clear trust tier tracking for all information

2. **Audit Trail Completeness**
   - Full evidence chain from query to final brief
   - Reproducible information gathering process
   - Compliance with regulatory requirements (GDPR, SOC 2)

3. **Security Enforcement**
   - Phase gates prevent shortcuts and policy violations
   - SSRF protection at URL validation stage
   - Trust tier validation prevents low-quality information propagation

4. **Operational Clarity**
   - Clear separation of concerns (discover, retrieve, synthesize)
   - Explicit phase boundaries with validation rules
   - Standardized data models across stages

5. **Extensibility**
   - Easy to add new search engines (plug into SEARCH stage)
   - Custom content parsers (plug into FETCH stage)
   - Alternative brief formats (extend BRIEF stage)

6. **Developer Experience**
   - Type-safe data models with clear schemas
   - Clear error messages from phase gate failures
   - Programmatic access to evidence chain

### Negative Consequences

1. **Increased Latency**
   - Three-stage pipeline takes longer than single-stage
   - SEARCH: ~1-3 seconds
   - FETCH: ~2-10 seconds (depending on document count)
   - BRIEF: ~5-20 seconds (LLM processing)
   - **Total**: 8-33 seconds vs. ~3 seconds for direct search

   **Mitigation**: Acceptable trade-off for information quality. Can optimize with parallel fetching and caching.

2. **Higher Cost**
   - Multiple API calls (search + fetch + LLM)
   - Storage costs for full document content
   - LLM costs for brief generation

   **Mitigation**: Configurable pipeline depth. Can skip BRIEF stage if only raw content needed.

3. **Complexity**
   - More moving parts (three stages + two gates)
   - Developers must understand phase boundaries
   - Error handling across multiple stages

   **Mitigation**: Comprehensive documentation and error messages. Helper method `execute_full_pipeline()` for simple cases.

4. **Rigidity**
   - Cannot skip stages (by design)
   - Minimum source requirements may be too strict for some queries
   - Phase gates may block legitimate edge cases

   **Mitigation**: Configurable gate enforcement. Can disable gates in development/testing environments.

5. **Storage Requirements**
   - Must store full document content (not just snippets)
   - Evidence records for all three stages
   - Potentially large HTML content

   **Mitigation**: Configurable content size limits. Option to store content hashes instead of full content.

---

## Testing Gates

All pipeline stages and gates must pass comprehensive tests before production deployment.

### Test Categories

#### 1. SEARCH Stage Tests (15 tests)

**Critical Tests**:
- `test_search_returns_search_result_trust_tier` - Trust tier is always SEARCH_RESULT
- `test_search_generates_evidence_record` - Evidence is logged
- `test_search_extracts_domain_correctly` - Domain extraction works
- `test_search_no_ssrf_urls_returned` - No internal URLs
- `test_search_handles_no_results` - Graceful empty result handling

**Acceptance Criteria**: 15/15 must pass (100%)

#### 2. FETCH Stage Tests (20 tests)

**Critical Tests**:
- `test_fetch_determines_trust_tier_correctly` - Trust tier determination algorithm
- `test_fetch_authoritative_domain` - .gov/.edu → AUTHORITATIVE_SOURCE
- `test_fetch_primary_source_domain` - Official docs → PRIMARY_SOURCE
- `test_fetch_external_domain` - General sites → EXTERNAL_SOURCE
- `test_fetch_extracts_metadata` - Author, publish date extraction
- `test_fetch_content_quality` - Word count, content validation
- `test_fetch_generates_evidence_record` - Evidence is logged

**Acceptance Criteria**: 20/20 must pass (100%)

#### 3. BRIEF Stage Tests (18 tests)

**Critical Tests**:
- `test_brief_requires_minimum_sources` - Minimum source enforcement
- `test_brief_rejects_search_result_tier` - No Tier 0 documents accepted
- `test_brief_includes_citations` - Citations are present
- `test_brief_tracks_evidence_chain` - Full evidence chain linked
- `test_brief_inherits_lowest_trust_tier` - Trust tier inheritance
- `test_brief_generates_evidence_record` - Evidence is logged

**Acceptance Criteria**: 18/18 must pass (100%)

#### 4. Phase Gate Tests (25 tests)

**Critical Tests**:
- `test_gate1_passes_valid_search_results` - Valid results pass
- `test_gate1_fails_wrong_trust_tier` - Wrong tier blocked
- `test_gate1_fails_ssrf_urls` - SSRF URLs blocked
- `test_gate1_fails_missing_evidence` - Missing evidence blocked
- `test_gate2_passes_valid_documents` - Valid documents pass
- `test_gate2_fails_insufficient_sources` - Too few sources blocked
- `test_gate2_fails_search_result_tier` - Tier 0 documents blocked
- `test_gate2_warns_low_quality` - Quality warnings generated
- `test_gate_error_includes_details` - Error messages are clear

**Acceptance Criteria**: 25/25 must pass (100%)

#### 5. Full Pipeline Integration Tests (12 tests)

**Critical Tests**:
- `test_full_pipeline_success` - Complete pipeline executes
- `test_full_pipeline_evidence_chain` - Evidence chain is complete
- `test_full_pipeline_gate_enforcement` - Gates block invalid data
- `test_full_pipeline_handles_fetch_failures` - Partial failures handled
- `test_pipeline_reproducibility` - Same query → same evidence chain

**Acceptance Criteria**: 12/12 must pass (100%)

### Total Gate Tests: 90 tests

**Production Deployment Criteria**:
- Pipeline Gate Tests: **90/90 passing (100%)** ← MANDATORY
- Integration with CommunicationOS: **270/270 passing (100%)** (from ADR-COMM-001)
- Combined Coverage: **> 95%**
- Zero critical security failures
- All phase gates verified

### Running Tests

```bash
# Run all pipeline tests
pytest agentos/core/communication/pipeline/tests/ -v

# Run specific test categories
pytest agentos/core/communication/pipeline/tests/test_search.py -v
pytest agentos/core/communication/pipeline/tests/test_fetch.py -v
pytest agentos/core/communication/pipeline/tests/test_brief.py -v
pytest agentos/core/communication/pipeline/tests/test_gates.py -v
pytest agentos/core/communication/pipeline/tests/test_integration.py -v

# Check pass rate
pytest agentos/core/communication/pipeline/tests/ --tb=no | grep "passed"
# Must show: "90 passed" (minimum)
```

---

## Usage Examples

### Example 1: Basic Pipeline Usage

```python
from agentos.core.communication.pipeline import PipelineService
from agentos.core.communication import CommunicationService

# Initialize services
comm_service = CommunicationService()
pipeline = PipelineService(comm_service, min_sources=2)

# Execute full pipeline
brief = await pipeline.execute_full_pipeline(
    query="What are the health benefits of green tea?",
    max_search_results=10,
    max_fetch_urls=5
)

# Access results
print(f"Summary: {brief.summary}")
print(f"Sources used: {brief.total_sources}")
print(f"Trust tier distribution: {brief.trust_tier_distribution}")

for citation in brief.citations:
    print(f"- {citation.title} ({citation.url}) [{citation.trust_tier.value}]")
```

### Example 2: Stage-by-Stage Execution

```python
# Stage 1: SEARCH
search_results = await pipeline.search(
    query="Python asyncio best practices",
    max_results=10
)

print(f"Found {len(search_results.results)} results")
print(f"Trust tier: {search_results.trust_tier.value}")  # Always SEARCH_RESULT

# Stage 2: FETCH (select top 3 results)
urls = [r.url for r in search_results.results[:3]]
documents = await pipeline.fetch(urls, source_query=search_results.query)

print(f"Fetched {documents.fetch_count} documents")
for doc in documents.documents:
    print(f"- {doc.title} [{doc.trust_tier.value}] ({doc.word_count} words)")

# Stage 3: BRIEF
brief = await pipeline.brief(
    query="What are Python asyncio best practices?",
    documents=documents
)

print(f"Brief summary: {brief.summary}")
print(f"Evidence chain: {brief.evidence_chain}")
```

### Example 3: Error Handling

```python
from agentos.core.communication.pipeline import PhaseGateError

try:
    # This will fail if insufficient sources
    brief = await pipeline.brief(
        query="example query",
        documents=documents  # Only 1 document, but min_sources=2
    )
except PhaseGateError as e:
    print(f"Phase gate failed: {e.gate_result.stage_from} → {e.gate_result.stage_to}")
    for error in e.gate_result.errors:
        print(f"  Error: {error}")
    for warning in e.gate_result.warnings:
        print(f"  Warning: {warning}")
```

### Example 4: Custom Configuration

```python
# Configure pipeline with custom settings
pipeline = PipelineService(
    communication_service=comm_service,
    min_sources=3,           # Require 3+ sources
    enforce_gates=True       # Enforce phase gates
)

# Execute with custom parameters
brief = await pipeline.execute_full_pipeline(
    query="Kubernetes security best practices",
    max_search_results=15,   # More search results
    max_fetch_urls=8         # Fetch more documents
)
```

### Example 5: Accessing Evidence Chain

```python
# Execute pipeline
brief = await pipeline.execute_full_pipeline(query="...")

# Retrieve evidence records
from agentos.core.communication import EvidenceLogger

evidence_logger = EvidenceLogger()

for evidence_id in brief.evidence_chain:
    record = await evidence_logger.get_evidence(evidence_id)
    print(f"Stage: {record.metadata.get('stage', 'unknown')}")
    print(f"Operation: {record.operation}")
    print(f"Trust tier: {record.trust_tier.value}")
    print(f"Timestamp: {record.created_at}")
    print("---")
```

---

## Implementation Checklist

Before deploying the pipeline:

- [ ] **Data Models** (`pipeline/models.py`)
  - [ ] SearchResult, SearchResultList
  - [ ] FetchedDocument, FetchedDocumentList
  - [ ] BriefSection, BriefCitation, Brief
  - [ ] GateResult, PipelineStage

- [ ] **Phase Gates** (`pipeline/gates.py`)
  - [ ] validate_search_to_fetch()
  - [ ] validate_fetch_to_brief()
  - [ ] PhaseGateError exception
  - [ ] SSRF validation helpers

- [ ] **Pipeline Service** (`pipeline/service.py`)
  - [ ] PipelineService class
  - [ ] search() method
  - [ ] fetch() method
  - [ ] brief() method
  - [ ] execute_full_pipeline() method

- [ ] **Trust Tier Integration**
  - [ ] Update evidence.py with domain lists
  - [ ] Trust tier determination in FETCH stage
  - [ ] Trust tier inheritance in BRIEF stage

- [ ] **Evidence Logging**
  - [ ] Evidence records for SEARCH stage
  - [ ] Evidence records for FETCH stage
  - [ ] Evidence records for BRIEF stage
  - [ ] Evidence chain linking

- [ ] **Testing**
  - [ ] SEARCH stage tests (15 tests)
  - [ ] FETCH stage tests (20 tests)
  - [ ] BRIEF stage tests (18 tests)
  - [ ] Phase gate tests (25 tests)
  - [ ] Integration tests (12 tests)

- [ ] **Documentation**
  - [ ] API documentation
  - [ ] Usage examples
  - [ ] Error handling guide
  - [ ] Configuration guide

- [ ] **Production Readiness**
  - [ ] All 90 gate tests passing
  - [ ] Performance benchmarks completed
  - [ ] Security review completed
  - [ ] Monitoring and alerting configured

---

## Future Enhancements

1. **Parallel Fetching**
   - Fetch multiple URLs concurrently
   - Reduce overall pipeline latency
   - Configurable concurrency limits

2. **Caching**
   - Cache search results (TTL: 24 hours)
   - Cache fetched content (TTL: configurable)
   - Distributed cache support (Redis)

3. **Incremental Brief Updates**
   - Update brief as new sources become available
   - Real-time brief refinement
   - Support for streaming responses

4. **Advanced Trust Scoring**
   - Multi-factor trust scoring (not just domain)
   - Historical accuracy tracking
   - Cross-reference validation

5. **Custom Brief Formats**
   - JSON-LD with structured data
   - Academic citation formats (APA, MLA, Chicago)
   - Export to Markdown, PDF, DOCX

6. **Quality Metrics**
   - Source diversity score
   - Information freshness score
   - Citation density analysis
   - Fact verification confidence

---

## References

- **ADR-COMM-001**: CommunicationOS Boundary and Security Architecture
- **Trust Tier Model**: `agentos/core/communication/models.py` (TrustTier enum)
- **Evidence Logging**: `agentos/core/communication/evidence.py`
- **CommunicationOS API**: `docs/communication_api.md`
- **Security Guide**: `docs/security/CommunicationOS-Security-Guide.md`

---

## Approval

**Decision**: APPROVED
**Effective Date**: 2026-01-31
**Review Date**: 2026-04-30 (quarterly review)
**Version**: 1.0.0

This ADR defines the architectural foundation for the SEARCH→FETCH→BRIEF pipeline. All implementations must comply with these stage definitions, phase gates, and trust tier requirements.

**Mandatory Requirements**:
1. Three stages must be executed in order (no shortcuts)
2. Phase gates MUST be enforced in production
3. Trust tier SEARCH_RESULT cannot be used in BRIEF stage
4. Minimum N sources required for BRIEF stage
5. Complete evidence chain must be maintained
6. All 90 gate tests must pass before production deployment

**Non-Negotiable Rules**:
- SEARCH results are candidates, NOT facts
- BRIEF cannot proceed without fetched documents
- Trust tier must progress through validation gates
- Evidence records must be generated at each stage

---

**Last Updated**: 2026-01-31
**Maintained By**: AgentOS Core Team
**Status**: ACTIVE - FROZEN (requires architectural review for changes)
