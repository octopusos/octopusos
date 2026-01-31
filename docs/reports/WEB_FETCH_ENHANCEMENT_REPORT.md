# Web Fetch Connector Enhancement Report

**Task**: 增强 web_fetch connector，输出更结构化的 fetched_document 模型  
**Date**: 2026-01-31  
**Status**: ✅ COMPLETED

---

## Overview

Enhanced the `WebFetchConnector` to output structured `fetched_document` format that complies with:
- **ADR-COMM-002**: SEARCH→FETCH→BRIEF Pipeline requirements
- **ADR-EXTERNAL-INFO-DECLARATION-001**: External information declaration architecture

---

## Changes Made

### 1. Enhanced Content Extraction

**File**: `/Users/pangge/PycharmProjects/AgentOS/agentos/core/communication/connectors/web_fetch.py`

#### New Extraction Capabilities

- **Author Extraction**: 
  - Meta tags (`name="author"`, `property="article:author"`)
  - Schema.org markup (`itemprop="author"`)
  - Common class patterns (`.author-name`, etc.)

- **Publication Date Extraction**:
  - Meta tags (`property="article:published_time"`, `name="date"`)
  - Schema.org markup (`itemprop="datePublished"`)
  - `<time>` tags with `datetime` attribute
  - Normalized to ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)

- **Sections Extraction**:
  - Identifies headings (h1-h6) and associated content
  - Groups paragraphs under each heading
  - Returns structured list of `{heading, content}` pairs
  - Limits to 20 sections to prevent data overflow

- **References Extraction**:
  - Finds reference/citation/source sections
  - Extracts links from these sections
  - Returns structured list of `{url, text}` pairs
  - Limits to 30 references

#### New Helper Methods

```python
def _extract_author(self, soup: BeautifulSoup) -> Optional[str]
def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]
def _normalize_date(self, date_str: str) -> str
def _extract_sections(self, content_elem) -> List[Dict[str, str]]
def _extract_references(self, soup: BeautifulSoup) -> List[Dict[str, str]]
```

---

### 2. Added Content Hash Calculation

```python
import hashlib
content_hash = hashlib.sha256(body_text.encode()).hexdigest()
```

- Uses SHA256 algorithm (64-character hex string)
- Calculated from `body_text` content
- Included in metadata for content integrity verification
- Enables detection of content changes over time

---

### 3. Structured fetched_document Output

#### New Method: `_build_fetched_document()`

Generates ADR-compliant structured output:

```python
{
    "type": "fetched_document",
    "trust_tier": "verified_source" | "primary_source" | "authoritative_source",
    "url": "https://example.com/page",
    "source_domain": "example.com",
    "content": {
        "title": "Page Title",
        "publish_date": "2026-01-15T10:00:00",  # ISO format, optional
        "author": "Author Name",  # optional
        "body_text": "Full text content...",
        "sections": [
            {"heading": "Section 1", "content": "Section content..."},
            ...
        ],
        "references": [
            {"url": "https://ref.com", "text": "Reference title"},
            ...
        ]
    },
    "metadata": {
        "fetched_at": "2026-01-31T12:00:00Z",  # ISO 8601 with Z suffix
        "content_hash": "abc123...",  # SHA256 hash (64 chars)
        "status_code": 200,
        "content_type": "text/html",
        "content_length": 12345
    }
}
```

#### Key Characteristics

✅ **Contains**: Factual data only (title, text, structure)  
❌ **Excludes**: Analytical fields (summary, importance, why_it_matters, analysis, impact)

This separation ensures compliance with ADR-COMM-002 Phase 2 (FETCH) requirements:
- FETCH stage retrieves content only
- BRIEF stage performs analysis/summarization

---

### 4. Trust Tier Determination

#### New Method: `_determine_trust_tier()`

Automatically assigns trust tier based on domain:

**Authoritative Sources (Tier 3)**:
- Government: `.gov`, `.mil`
- Education: `.edu`
- International organizations: `who.int`, `un.org`, `unesco.org`
- Scientific publishers: `nature.com`, `science.org`, `springer.com`, `ieee.org`, `nih.gov`

**Primary Sources (Tier 2)**:
- Official documentation: `docs.*`, `documentation.*`, `developer.*`
- Package ecosystems: `github.io`, `readthedocs.io`
- Language official sites: `python.org`, `nodejs.org`, `rust-lang.org`
- Standards bodies: `w3.org`, `ietf.org`, `rfc-editor.org`

**Verified Sources (Tier 1)**:
- General websites (default for fetch stage)

---

### 5. Timestamp Enhancement

Fixed deprecation warning by using timezone-aware datetime:

```python
# Before (deprecated):
datetime.utcnow().isoformat() + "Z"

# After (timezone-aware):
from datetime import datetime, UTC
datetime.now(UTC).isoformat().replace("+00:00", "Z")
```

---

## Testing

### Unit Tests Added

**File**: `/Users/pangge/PycharmProjects/AgentOS/tests/test_web_fetch_connector.py`

1. **test_html_extraction**: Enhanced to verify author, publish_date, sections
2. **test_fetched_document_structure**: Comprehensive structure validation
3. **test_trust_tier_determination**: Verify tier assignment logic
4. **test_content_hash_calculation**: Verify SHA256 hash generation

### Test Results

```
============================= test session starts ==============================
tests/test_web_fetch_connector.py::test_html_extraction PASSED
tests/test_web_fetch_connector.py::test_fetched_document_structure PASSED
tests/test_web_fetch_connector.py::test_trust_tier_determination PASSED
tests/test_web_fetch_connector.py::test_content_hash_calculation PASSED
============================== 13 passed in 1.50s ===============================
```

All 13 tests pass, including:
- 4 new tests for enhanced functionality
- 9 existing tests (no regressions)

**Additional Unit Tests**: 25 tests in `agentos/core/communication/tests/test_web_fetch.py` all pass

---

## Verification Checklist

✅ **Enhanced content extraction**:
- ✅ Title extraction
- ✅ Publish date extraction (from meta tags, schema.org, time elements)
- ✅ Author extraction (from meta tags, schema.org, class patterns)
- ✅ Body text extraction
- ✅ Sections extraction (headings + content)
- ✅ References extraction (from reference/citation sections)

✅ **Content hash calculation**:
- ✅ SHA256 algorithm
- ✅ 64-character hex string
- ✅ Calculated from body_text

✅ **Structured fetched_document output**:
- ✅ `type`: "fetched_document"
- ✅ `trust_tier`: Determined by domain
- ✅ `url`: Source URL
- ✅ `source_domain`: Extracted domain
- ✅ `content`: Structured content object
  - ✅ title, publish_date, author, body_text
  - ✅ sections (list of heading+content)
  - ✅ references (list of url+text)
- ✅ `metadata`: Technical metadata
  - ✅ fetched_at (ISO 8601 with Z)
  - ✅ content_hash (SHA256)
  - ✅ status_code, content_type, content_length

✅ **NO analytical fields**:
- ✅ No `summary` field
- ✅ No `importance` field
- ✅ No `why_it_matters` field
- ✅ No `analysis` field
- ✅ No `impact` field

✅ **Testing**:
- ✅ 4 new unit tests
- ✅ All 13 tests pass (no regressions)
- ✅ 25 additional unit tests pass
- ✅ No deprecation warnings
- ✅ Comprehensive example test

---

## ADR Compliance

### ADR-COMM-002: SEARCH→FETCH→BRIEF Pipeline

**Stage 2 (FETCH) Requirements**:

✅ **Allowed Operations**:
- ✅ Fetch full HTML/text content from URLs
- ✅ Parse document structure (headings, paragraphs)
- ✅ Extract metadata (author, publish date)
- ✅ Content-type detection
- ✅ Basic content cleaning (remove ads, navigation)

✅ **Forbidden Operations** (NOT implemented):
- ✅ NO summarization or content analysis
- ✅ NO fact verification or conclusion drawing
- ✅ NO value judgments or quality assessment
- ✅ NO sentiment analysis or opinion extraction
- ✅ NO merging content from multiple documents
- ✅ NO generating new text not present in source

✅ **Output Schema Compliance**:
```python
@dataclass
class FetchedDocument:  # Matches ADR specification
    url: str                        # ✅ Implemented
    title: str                      # ✅ Implemented
    content: str                    # ✅ Implemented as body_text
    author: Optional[str]           # ✅ Implemented
    publish_date: Optional[datetime] # ✅ Implemented
    content_type: str               # ✅ Implemented
    domain: str                     # ✅ Implemented as source_domain
    trust_tier: TrustTier           # ✅ Implemented
    metadata: Dict[str, Any]        # ✅ Implemented
    fetch_timestamp: datetime       # ✅ Implemented as fetched_at
```

---

### ADR-EXTERNAL-INFO-DECLARATION-001

**Core Principle 3 Compliance**:

✅ **Attribution Enforcement**:
- ✅ All returned data includes attribution metadata
- ✅ Source URL preserved
- ✅ Timestamp recorded (fetched_at)
- ✅ Trust level assigned (trust_tier)

✅ **Evidence Trail**:
- ✅ Fetch timestamp recorded
- ✅ Content hash enables integrity verification
- ✅ Source domain extracted
- ✅ HTTP status and content metadata preserved

---

## Example Output

### Input
```html
<html>
  <head>
    <title>Python 3.12 Release Notes</title>
    <meta name="author" content="Python Software Foundation">
    <meta property="article:published_time" content="2023-10-02T10:00:00Z">
  </head>
  <body>
    <h1>Python 3.12 Release Highlights</h1>
    <p>Python 3.12 is the latest stable release...</p>
    <h2>New Features</h2>
    <p>Major improvements include...</p>
  </body>
</html>
```

### Output
```json
{
  "type": "fetched_document",
  "trust_tier": "primary_source",
  "url": "https://docs.python.org/3.12/whatsnew/",
  "source_domain": "docs.python.org",
  "content": {
    "title": "Python 3.12 Release Notes",
    "publish_date": "2023-10-02T10:00:00",
    "author": "Python Software Foundation",
    "body_text": "Python 3.12 Release Highlights\nPython 3.12 is the latest stable release...",
    "sections": [
      {
        "heading": "Python 3.12 Release Highlights",
        "content": "Python 3.12 is the latest stable release..."
      },
      {
        "heading": "New Features",
        "content": "Major improvements include..."
      }
    ],
    "references": []
  },
  "metadata": {
    "fetched_at": "2026-01-31T12:00:00Z",
    "content_hash": "f1947e7db3153f10185c2bbb5442bfb8386aa6764a56884404a30c41bc0642f6",
    "status_code": 200,
    "content_type": "text/html",
    "content_length": 1583
  }
}
```

---

## Usage Example

```python
from agentos.core.communication.connectors.web_fetch import WebFetchConnector

# Initialize connector
connector = WebFetchConnector()

# Fetch URL with structured output
result = await connector.execute("fetch", {
    "url": "https://docs.python.org/3.12/whatsnew/",
    "extract_content": True
})

# Access structured fetched_document
if "fetched_document" in result:
    doc = result["fetched_document"]
    
    print(f"Title: {doc['content']['title']}")
    print(f"Author: {doc['content']['author']}")
    print(f"Trust Tier: {doc['trust_tier']}")
    print(f"Content Hash: {doc['metadata']['content_hash']}")
    
    # Process sections
    for section in doc['content']['sections']:
        print(f"Section: {section['heading']}")
        print(f"Content: {section['content']}")
```

---

## Integration Points

### Current Integration
- ✅ Returns `fetched_document` in result dictionary
- ✅ Backward compatible (keeps `extracted` field)
- ✅ No breaking changes to existing code

### Future Integration
Ready for integration with:
1. **SEARCH stage**: Provides URLs for fetching
2. **BRIEF stage**: Consumes fetched_document for summarization
3. **Communication adapter**: Routes fetched_document to chat engine
4. **Evidence system**: Stores fetched_document for audit trail

---

## Performance Considerations

- **Content Limits**: 
  - Body text: 10,000 characters
  - Sections: 20 sections max
  - References: 30 references max
  - Links: 50 links max
  - Images: 20 images max

- **Hash Calculation**: O(n) where n = body_text length
- **DOM Traversal**: Optimized BeautifulSoup queries
- **Memory**: Limits prevent excessive memory usage

---

## Security Considerations

✅ **Content Integrity**:
- SHA256 hash detects content tampering
- Timestamp enables freshness checks

✅ **Trust Boundaries**:
- Explicit trust tier assignment
- Domain-based trust evaluation
- No automatic trust escalation

✅ **Metadata Isolation**:
- Technical metadata separated from content
- No executable content in metadata
- Safe for serialization/storage

---

## Next Steps

1. ✅ **Task #4 completed**: Enhanced fetch stage with structured output
2. **Task #5 pending**: Implement brief generation logic and phase gates
3. **Task #8 pending**: Write E2E golden path tests
4. **Task #9 pending**: Run acceptance tests and generate report

---

## Files Modified

1. **Enhanced**:
   - `/Users/pangge/PycharmProjects/AgentOS/agentos/core/communication/connectors/web_fetch.py`
     - Added imports: `hashlib`, `re`, `UTC`
     - Added methods: `_build_fetched_document()`, `_determine_trust_tier()`
     - Enhanced methods: `_extract_html_content()`, `_extract_author()`, `_extract_publish_date()`, `_normalize_date()`, `_extract_sections()`, `_extract_references()`
     - Updated `_fetch()` to generate fetched_document

2. **Tests Updated**:
   - `/Users/pangge/PycharmProjects/AgentOS/tests/test_web_fetch_connector.py`
     - Enhanced `test_html_extraction()` to verify new fields
     - Added `test_fetched_document_structure()`
     - Added `test_trust_tier_determination()`
     - Added `test_content_hash_calculation()`

3. **Documentation Created**:
   - `/Users/pangge/PycharmProjects/AgentOS/WEB_FETCH_ENHANCEMENT_REPORT.md` (this file)

---

## Summary

✅ **Successfully enhanced** the `WebFetchConnector` to output structured `fetched_document` format that fully complies with ADR-COMM-002 and ADR-EXTERNAL-INFO-DECLARATION-001 requirements.

**Key Achievements**:
- Enhanced content extraction (author, date, sections, references)
- Added content hash calculation (SHA256)
- Implemented structured fetched_document output
- Automatic trust tier determination
- NO analytical fields (maintaining FETCH stage purity)
- Comprehensive testing (13 tests pass)
- Full ADR compliance
- Zero regressions

**Status**: ✅ TASK COMPLETED
