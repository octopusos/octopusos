# Brief Command Quick Reference

**Quick Start Guide for `/comm brief` Command**

---

## Usage

### Command Syntax
```bash
/comm brief <topic> [--today] [--max-items N]
```

### Examples
```bash
# Generate AI brief with default settings (7 items)
/comm brief ai

# Generate AI brief with today's results only
/comm brief ai --today

# Generate AI brief with custom item count
/comm brief ai --max-items 10
```

---

## Requirements

### Phase Gate Requirements
1. **Execution Phase**: Command ONLY works in `execution` phase (blocked in `planning`)
2. **Minimum Documents**: Requires ≥3 verified documents
3. **Trust Tier**: All documents must be `verified_source` (≥Tier 1)
   - ✅ Accepted: `external_source`, `primary_source`, `authoritative`
   - ❌ Rejected: `search_result` (Tier 0)

### Input Document Schema
```python
{
    "url": "https://example.com/article",        # Required
    "title": "Article Title",                     # Required
    "trust_tier": "external_source",              # Required (≥Tier 1)
    "text": "Full article content...",            # Optional but recommended
    "summary": "Article summary",                 # Optional
    "domain": "example.com",                      # Optional (auto-extracted)
    "retrieved_at": "2026-01-31T12:00:00Z"       # Optional
}
```

---

## Pipeline Flow

```
User: /comm brief ai
       ↓
   [Phase Gate Check]
       ↓
   Step 1: Multi-query Search (4 queries)
       ↓
   Step 2: Candidate Filtering (dedup + domain limit)
       ↓
   Step 3: Fetch Verification (parallel, max 3 concurrent)
       ↓
   Step 4: Phase Gate Validation ← CRITICAL
       • Check: ≥3 documents
       • Check: All trust_tier ≥ Tier 1
       • Check: Required fields present
       ↓
   Step 5: Brief Generation
       • Regional categorization
       • Trend extraction
       • Markdown formatting
       ↓
   Output: Structured Markdown Brief
```

---

## Output Format

```markdown
# Today's AI Policy Brief (2026-01-31)

**Generation Time**: 2026-01-31T12:34:56Z
**Source**: CommunicationOS (5 verified sources)
**Scope**: AI / Policy / Regulation

---

## 🇦🇺 Australia
### Policy Update: [Title]
- **Key Content**: [Extracted content]
- **Effective Date**: [Date]
- **Source**: [domain](url)
- **Trust Tier**: authoritative

## 🌍 Global Trends
- Trend description (observed in N sources)

## Risk & Impact (Declarative)
- **Enterprise Impact**: [Statement]
- **Developer Notes**: [Guidance]

---

> All content based on N verified official sources
> 📝 **Source Attribution**:
> - [domain](url)

---

## Pipeline Statistics
- Search queries executed: 4
- Candidate results: 14
- Documents verified: 5
- Generation time: 12.34s
```

---

## Error Handling

### Error 1: Phase Gate Blocked (Planning Phase)
```
🚫 Command blocked: comm.* commands are forbidden in planning phase.
External communication is only allowed during execution to prevent
information leakage and ensure controlled access.
```

**Solution**: Switch to execution phase
```bash
/phase execution
/comm brief ai
```

---

### Error 2: Insufficient Documents
```
# Brief Generation Failed

## Phase Gate Error

Insufficient documents: 2 < 3. Brief requires at least 3 verified documents.

**Pipeline Stats**:
- Search queries: 4
- Candidates found: 14
- Documents verified: 2
- Required minimum: 3 verified documents

**Recommendation**: Try expanding search criteria or verify more sources.
```

**Solution**: Increase `--max-items` to fetch more candidates
```bash
/comm brief ai --max-items 15
```

---

### Error 3: Invalid Trust Tier
```
# Brief Generation Failed

## Phase Gate Error

Found 1 documents with invalid trust tier:
  - https://example.com/search-result: search_result
    (search_result tier not accepted, must be verified)

**Recommendation**: Ensure all documents are from FETCH stage, not SEARCH.
```

**Solution**: This should not happen in normal pipeline usage. If it occurs, it indicates search results were passed directly without fetching.

---

## Regional Categorization

### Supported Regions
| Region | Detection Method | Example Domains |
|--------|------------------|-----------------|
| 🇦🇺 Australia | `.au` domain, "australia" keyword | `gov.au`, `edu.au` |
| 🇨🇳 China | `.cn` domain, "china" keyword | `gov.cn` |
| 🇬🇧 United Kingdom | `.uk` domain, "britain" keyword | `gov.uk`, `ac.uk` |
| 🇪🇺 European Union | `.eu` domain, "european" keyword | `europa.eu` |
| 🇺🇸 United States | `.gov` + whitehouse, "US" keywords | `whitehouse.gov`, `.gov` |
| 🇯🇵 Japan | `.jp` domain, "japan" keyword | `go.jp` |
| 🌍 Global | Default (no specific region) | All others |

---

## Trend Extraction

### Tracked Keywords
- regulation, policy, compliance
- safety, ethics, transparency
- privacy, security, audit, governance

### Trend Criteria
- Must appear in ≥2 sources (or 50% of documents)
- Returns top 5 trends maximum
- Format: "Trend description (observed in N sources)"

---

## Programmatic Usage

### Python API
```python
from agentos.core.communication.brief_generator import BriefGenerator

# Initialize generator
generator = BriefGenerator(min_documents=3)

# Validate inputs (Phase Gate)
is_valid, error_msg = generator.validate_inputs(fetched_documents)
if not is_valid:
    print(f"Validation failed: {error_msg}")
    return

# Generate brief
brief_md = generator.generate_brief(fetched_documents, topic="AI")
print(brief_md)
```

### Configuration
```python
# Custom minimum documents
generator = BriefGenerator(min_documents=5)

# Custom trust tier requirement
generator = BriefGenerator(
    min_documents=3,
    trust_tier_requirement="verified_source"
)
```

---

## Testing

### Run Unit Tests
```bash
# All tests
python3 -m pytest tests/unit/core/communication/test_brief_generator.py -v

# Specific test class
python3 -m pytest tests/unit/core/communication/test_brief_generator.py::TestBriefGeneratorValidation -v

# With coverage
python3 -m pytest tests/unit/core/communication/test_brief_generator.py --cov=agentos.core.communication.brief_generator
```

### Test Results
```
========================== 24 passed in 0.24s ===========================
Coverage: 95%
```

---

## Best Practices

### Do's ✅
- ✅ Use in execution phase only
- ✅ Provide ≥3 fetched documents
- ✅ Ensure all documents have trust_tier ≥ Tier 1
- ✅ Include text/content for better key point extraction
- ✅ Use `--max-items` to control document count

### Don'ts ❌
- ❌ Don't bypass phase gate validation
- ❌ Don't pass search_result tier documents
- ❌ Don't use in planning phase
- ❌ Don't expect deep semantic analysis (keyword-based only)
- ❌ Don't mix search snippets with fetched content

---

## Performance

### Typical Timings
- Search: 1-3 seconds (4 queries)
- Fetch: 2-10 seconds (parallel, depends on document count)
- Validation + Generation: <1 second
- **Total**: 3-14 seconds

### Optimization Tips
1. Use `--max-items` to limit document count
2. Pipeline runs searches in parallel (4 queries)
3. Fetch operations use semaphore (max 3 concurrent)
4. Regional categorization is O(n) - fast

---

## Troubleshooting

### Issue: Brief generation is slow
**Cause**: Fetching many documents
**Solution**: Reduce `--max-items` parameter
```bash
/comm brief ai --max-items 5  # Faster
```

---

### Issue: No trends detected
**Cause**: Documents don't share common keywords
**Solution**: This is expected if documents cover diverse topics. Default message will be shown:
```
- Diverse policy developments across regions
```

---

### Issue: All documents in "Global" category
**Cause**: No region-specific markers detected
**Solution**: This is normal for generic .com/.org domains. Regional categorization is best-effort.

---

### Issue: Key points are truncated
**Cause**: Content exceeds 200 characters
**Solution**: This is by design. Full content is preserved in source documents. Brief shows excerpts only.

---

## Related Documentation

- **Full Implementation Report**: `BRIEF_COMMAND_IMPLEMENTATION_REPORT.md`
- **ADR-COMM-002**: `docs/adr/ADR-COMM-002-Search-Fetch-Brief-Pipeline.md`
- **CommunicationOS Architecture**: `docs/architecture/ADR-COMM-001-CommunicationOS-Boundary.md`
- **Test Suite**: `tests/unit/core/communication/test_brief_generator.py`

---

## Support

### Common Questions

**Q: Can I use brief in planning phase?**
A: No. Phase gate blocks all /comm commands in planning phase.

**Q: Why is search_result tier rejected?**
A: Search results are candidates, not verified facts. Brief requires fetched content.

**Q: How are regions determined?**
A: By domain TLD (.au, .cn, etc.) and keywords in title/text.

**Q: Can I customize the output format?**
A: Not currently. Format follows ADR-COMM-002 specifications.

**Q: What if I need < 3 documents?**
A: Configure BriefGenerator with custom min_documents, but this violates ADR-COMM-002 requirements.

---

**Last Updated**: 2026-01-31
**Version**: 1.0.0
**Status**: ACTIVE
