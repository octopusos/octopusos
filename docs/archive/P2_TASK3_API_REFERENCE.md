# P2-3: Subgraph API Endpoint Reference

## Overview

**Endpoint**: `GET /api/brain/subgraph`
**Description**: Query a k-hop subgraph centered at a seed entity
**Authentication**: None (local API)
**Version**: P2-3 (2026-01-30)

This endpoint provides **cognitive structure extraction** - it doesn't just return graph data, it returns nodes and edges enriched with:
- Evidence counts and sources
- Coverage metrics (how well each node is understood)
- Blind spot detection (cognitive gaps)
- Missing connections (relationships that should exist but don't)
- Visual encoding (colors, sizes, styles based on cognitive attributes)

---

## Request Parameters

| Parameter | Type | Required | Default | Range | Description |
|-----------|------|----------|---------|-------|-------------|
| `seed` | string | ✅ | - | - | Seed entity (format: `type:key`) |
| `k_hop` | integer | ❌ | 2 | 1-3 | Number of hops from seed |
| `min_evidence` | integer | ❌ | 1 | 1-10 | Minimum evidence count per edge |
| `include_suspected` | boolean | ❌ | false | - | Include suspected edges (no evidence) |
| `project_id` | string | ❌ | null | - | Project ID filter (reserved) |

### Seed Format

Seed must follow the format `type:key`:

- **file**: `file:manager.py`, `file:agentos/core/task/service.py`
- **capability**: `capability:api`, `capability:task_runner`
- **term**: `term:authentication`, `term:retry`
- **doc**: `doc:README.md`, `doc:architecture/ADR-001.md`
- **commit**: `commit:abc123def456`
- **symbol**: `symbol:TaskManager`, `symbol:execute_plan`

**Examples**:
```
GET /api/brain/subgraph?seed=file:manager.py
GET /api/brain/subgraph?seed=capability:api&k_hop=1
GET /api/brain/subgraph?seed=term:authentication&k_hop=3&min_evidence=2
```

---

## Response Format

### Success Response (200)

```json
{
  "ok": true,
  "data": {
    "nodes": [
      {
        "id": "n123",
        "entity_type": "file",
        "entity_key": "manager.py",
        "entity_name": "Task Manager",
        "entity_id": 123,
        "evidence_count": 15,
        "coverage_sources": ["git", "doc", "code"],
        "evidence_density": 0.85,
        "is_blind_spot": false,
        "blind_spot_severity": null,
        "blind_spot_type": null,
        "blind_spot_reason": null,
        "in_degree": 5,
        "out_degree": 3,
        "distance_from_seed": 0,
        "visual": {
          "color": "#00C853",
          "size": 45,
          "border_color": "#00C853",
          "border_width": 1,
          "border_style": "solid",
          "shape": "circle",
          "label": "manager.py\n✅ 85% | 15 evidence",
          "tooltip": "Entity: manager.py\nType: file\nCoverage: 85.0%\nEvidence: 15\nSources: code, doc, git\nIn-Degree: 5\nOut-Degree: 3\n"
        }
      }
    ],
    "edges": [
      {
        "id": "e456",
        "source_id": "n123",
        "target_id": "n789",
        "edge_type": "imports",
        "edge_db_id": 456,
        "evidence_count": 3,
        "evidence_types": ["git", "code"],
        "evidence_list": [
          {
            "id": 1,
            "source_type": "git",
            "source_ref": "commit_abc123",
            "span": {},
            "attrs": {}
          },
          {
            "id": 2,
            "source_type": "code",
            "source_ref": "import statement",
            "span": {"line": 10, "col": 0},
            "attrs": {}
          }
        ],
        "confidence": 0.7,
        "status": "confirmed",
        "is_weak": false,
        "is_suspected": false,
        "visual": {
          "width": 2,
          "color": "#4A90E2",
          "style": "solid",
          "opacity": 0.7,
          "label": "imports | 3 (code+git)",
          "tooltip": "Edge: imports\nEvidence: 3\nConfidence: 0.70\nStatus: confirmed\n\nEvidence Sources:\n1. git: commit_abc123\n2. code: import statement\n"
        }
      }
    ],
    "metadata": {
      "seed_entity": "file:manager.py",
      "k_hop": 2,
      "total_nodes": 12,
      "total_edges": 18,
      "confirmed_edges": 16,
      "suspected_edges": 2,
      "coverage_percentage": 0.83,
      "evidence_density": 8.5,
      "blind_spot_count": 2,
      "high_risk_blind_spot_count": 0,
      "missing_connections_count": 3,
      "coverage_gaps": [
        {
          "type": "missing_doc_coverage",
          "description": "Code depends on service.py but no doc explains this relationship"
        }
      ]
    }
  },
  "error": null,
  "cached": false
}
```

### Error Response (400 - Invalid Parameters)

```json
{
  "ok": false,
  "data": null,
  "error": "Invalid seed format: 'manager.py'. Expected 'type:key'."
}
```

### Error Response (404 - Entity Not Found)

```json
{
  "ok": false,
  "data": null,
  "error": "Seed entity not found: 'file:nonexistent.py'. This entity may not be indexed yet."
}
```

### Error Response (404 - Index Not Found)

```json
{
  "ok": false,
  "data": null,
  "error": "BrainOS index not found. Run '/brain build' to create the index first."
}
```

### Error Response (500 - Internal Server Error)

```json
{
  "ok": false,
  "data": null,
  "error": "Internal server error. Please contact support. Details: Database connection failed"
}
```

---

## Data Structures

### SubgraphNode

A node in the cognitive graph with evidence and coverage metrics.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Node identifier (e.g., "n123") |
| `entity_type` | string | Entity type (file, capability, term, doc, commit, symbol) |
| `entity_key` | string | Entity key (e.g., "manager.py") |
| `entity_name` | string | Human-readable name |
| `entity_id` | integer | Internal database ID |
| `evidence_count` | integer | Total evidence count for edges touching this node |
| `coverage_sources` | string[] | Evidence source types (["git", "doc", "code"]) |
| `evidence_density` | float | Normalized evidence density (0-1) |
| `is_blind_spot` | boolean | Whether this node is a cognitive blind spot |
| `blind_spot_severity` | float\|null | Severity (0-1) if blind spot, null otherwise |
| `blind_spot_type` | string\|null | Type of blind spot, null if not a blind spot |
| `blind_spot_reason` | string\|null | Reason for blind spot, null if not a blind spot |
| `in_degree` | integer | Number of incoming edges (within subgraph) |
| `out_degree` | integer | Number of outgoing edges (within subgraph) |
| `distance_from_seed` | integer | Hops from seed node |
| `visual` | NodeVisual | Visual encoding for rendering |

### NodeVisual

Visual encoding for a node based on cognitive attributes.

| Field | Type | Description |
|-------|------|-------------|
| `color` | string | Fill color (hex) - based on coverage_sources count |
| `size` | integer | Radius in pixels - based on evidence_count and in_degree |
| `border_color` | string | Border color (hex) - red/orange for blind spots |
| `border_width` | integer | Border width in pixels |
| `border_style` | string | Border style ("solid", "dashed", "dotted") |
| `shape` | string | Node shape ("circle", "square", "diamond", etc.) |
| `label` | string | Display text with coverage badge |
| `tooltip` | string | Hover tooltip with detailed info |

**Color Mapping**:
- `#00C853` (green): 3 sources (git + doc + code) - strong coverage
- `#4A90E2` (blue): 2 sources - medium coverage
- `#FFA000` (orange): 1 source - weak coverage
- `#FF0000` (red): 0 sources - no evidence (should not happen)

**Size Calculation**:
```
size = 20 (base) + min(20, evidence_count * 2) + min(15, in_degree * 3) + seed_bonus(10)
```

### SubgraphEdge

An edge in the cognitive graph with evidence chain.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Edge identifier (e.g., "e456") |
| `source_id` | string | Source node ID |
| `target_id` | string | Target node ID |
| `edge_type` | string | Edge type (imports, depends_on, references, etc.) |
| `edge_db_id` | integer | Internal database ID |
| `evidence_count` | integer | Number of evidence records |
| `evidence_types` | string[] | Evidence types (["git", "doc", "code"]) |
| `evidence_list` | Evidence[] | Full evidence records |
| `confidence` | float | Confidence score (0-1) |
| `status` | string | "confirmed" or "suspected" |
| `is_weak` | boolean | evidence_count < 3 |
| `is_suspected` | boolean | evidence_count = 0 |
| `visual` | EdgeVisual | Visual encoding for rendering |

### EdgeVisual

Visual encoding for an edge based on evidence count and diversity.

| Field | Type | Description |
|-------|------|-------------|
| `width` | integer | Line width in pixels (1-4) |
| `color` | string | Line color (hex) |
| `style` | string | Line style ("solid", "dashed", "dotted") |
| `opacity` | float | Opacity (0-1) |
| `label` | string | Display text with evidence info |
| `tooltip` | string | Hover tooltip with evidence list |

**Width Mapping**:
- 1px: 0-1 evidence
- 2px: 2-4 evidence
- 3px: 5-9 evidence
- 4px: 10+ evidence

**Color Mapping**:
- `#00C853` (green): 3 evidence types
- `#4A90E2` (blue): 2 evidence types
- `#B0B0B0` (gray): 1 evidence type
- `#CCCCCC` (light gray): 0 evidence (suspected)

### SubgraphMetadata

Summary statistics for the subgraph.

| Field | Type | Description |
|-------|------|-------------|
| `seed_entity` | string | Seed entity key |
| `k_hop` | integer | Number of hops |
| `total_nodes` | integer | Total nodes in subgraph |
| `total_edges` | integer | Total edges in subgraph |
| `confirmed_edges` | integer | Edges with evidence >= 1 |
| `suspected_edges` | integer | Edges with evidence = 0 |
| `coverage_percentage` | float | Ratio of nodes with evidence > 0 (0-1) |
| `evidence_density` | float | Average evidence per edge |
| `blind_spot_count` | integer | Number of blind spot nodes |
| `high_risk_blind_spot_count` | integer | Blind spots with severity >= 0.7 |
| `missing_connections_count` | integer | Number of missing connections detected |
| `coverage_gaps` | Gap[] | List of coverage gaps |

### CoverageGap

A detected gap in cognitive coverage.

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Gap type (e.g., "missing_doc_coverage") |
| `description` | string | Human-readable description |

---

## Examples

### Example 1: Query File Subgraph (2-hop)

**Request**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=1"
```

**Response**:
```json
{
  "ok": true,
  "data": {
    "nodes": [
      {
        "id": "n123",
        "entity_type": "file",
        "entity_key": "manager.py",
        "entity_name": "Task Manager",
        "evidence_count": 15,
        "coverage_sources": ["git", "doc", "code"],
        "is_blind_spot": false,
        "in_degree": 5,
        "out_degree": 3,
        "distance_from_seed": 0,
        "visual": {
          "color": "#00C853",
          "size": 45,
          "label": "manager.py\n✅ 85% | 15 evidence"
        }
      }
    ],
    "edges": [],
    "metadata": {
      "seed_entity": "file:manager.py",
      "k_hop": 2,
      "total_nodes": 1,
      "total_edges": 0,
      "coverage_percentage": 1.0
    }
  },
  "error": null,
  "cached": false
}
```

### Example 2: Query Capability Subgraph (1-hop)

**Request**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=capability:api&k_hop=1"
```

**Response**: Similar structure with capability-type nodes.

### Example 3: Query with High Evidence Filter

**Request**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=5"
```

This filters out edges with < 5 evidence, returning only high-confidence relationships.

### Example 4: Include Suspected Edges

**Request**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&include_suspected=true"
```

This includes edges with 0 evidence (suspected relationships), shown with dashed lines.

---

## Error Handling

### Error Codes

| Status Code | Reason | Solution |
|-------------|--------|----------|
| 200 (ok=false, error present) | Invalid seed format | Use correct format: `type:key` |
| 200 (ok=false, error present) | Seed entity not found | Check entity is indexed with `/brain build` |
| 200 (ok=false, error present) | Index not found | Run `/brain build` to create index |
| 200 (ok=false, error present) | Service error | Check logs, verify database integrity |
| 422 | Parameter validation error | Check parameter ranges (k_hop: 1-3, min_evidence: 1-10) |

**Note**: The API returns 200 OK even for errors, with `ok=false` in the response body. Only FastAPI validation errors return 422.

### Common Errors

#### 1. Invalid Seed Format

**Error**:
```json
{
  "ok": false,
  "error": "Invalid seed format: 'manager.py'. Expected 'type:key'."
}
```

**Fix**: Add entity type prefix:
```bash
# Wrong
curl "http://localhost:5000/api/brain/subgraph?seed=manager.py"

# Correct
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py"
```

#### 2. Entity Not Indexed

**Error**:
```json
{
  "ok": false,
  "error": "Seed entity not found: 'file:new_file.py'. This entity may not be indexed yet."
}
```

**Fix**: Build or rebuild the index:
```bash
# Via CLI
agentos brain build

# Via API
curl -X POST "http://localhost:5000/api/brain/build"
```

#### 3. Index Not Found

**Error**:
```json
{
  "ok": false,
  "error": "BrainOS index not found. Run '/brain build' to create the index first."
}
```

**Fix**: Initialize BrainOS:
```bash
agentos brain build
```

---

## Performance

### Response Times

| Query Type | Average Time | 95th Percentile | Notes |
|------------|--------------|-----------------|-------|
| 1-hop (no cache) | 150ms | 300ms | Simple neighborhood |
| 2-hop (no cache) | 250ms | 500ms | Medium complexity |
| 3-hop (no cache) | 450ms | 800ms | Large subgraph |
| Cached query | 10ms | 20ms | Cache hit |

### Caching

- **Cache TTL**: 15 minutes
- **Cache Key**: `subgraph:{seed}:{k_hop}:{min_evidence}:{include_suspected}`
- **Cache Storage**: In-memory (production: Redis)

**Cache Behavior**:
1. First query: Executes full query, caches result, returns with `cached: false`
2. Subsequent queries (within 15 min): Returns cached result with `cached: true`
3. After 15 min: Cache expires, next query re-executes and caches

### Limits

| Limit | Value | Reason |
|-------|-------|--------|
| Max k_hop | 3 | Prevent full graph traversal |
| Max min_evidence | 10 | Avoid overly strict filtering |
| Max nodes (auto-truncate) | 1000 | Prevent huge payloads |
| Max edges (auto-truncate) | 5000 | Prevent huge payloads |

---

## Testing

### Test with curl

```bash
# Basic query
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2"

# With authentication (if needed)
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2"

# Pretty-print JSON
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2" | jq .
```

### Test with Python

```python
import requests

response = requests.get(
    "http://localhost:5000/api/brain/subgraph",
    params={
        "seed": "file:manager.py",
        "k_hop": 2,
        "min_evidence": 1
    }
)

data = response.json()
if data["ok"]:
    print(f"Nodes: {len(data['data']['nodes'])}")
    print(f"Edges: {len(data['data']['edges'])}")
    print(f"Cached: {data['cached']}")
else:
    print(f"Error: {data['error']}")
```

### Test with JavaScript

```javascript
const response = await fetch(
    "/api/brain/subgraph?seed=file:manager.py&k_hop=2"
);
const data = await response.json();

if (data.ok) {
    console.log(`Nodes: ${data.data.nodes.length}`);
    console.log(`Edges: ${data.data.edges.length}`);
} else {
    console.error(`Error: ${data.error}`);
}
```

---

## OpenAPI Documentation

The endpoint is fully documented in the OpenAPI schema:

```
GET /docs
```

This provides:
- Interactive API testing
- Request/response schemas
- Parameter validation rules
- Example requests

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| P2-3 | 2026-01-30 | Initial release with cognitive structure extraction |
| P2-2 | 2026-01-29 | Backend subgraph query engine implemented |
| P2-1 | 2026-01-28 | Cognitive model and visual semantics defined |

---

## See Also

- [P2_TASK3_QUICK_START.md](./P2_TASK3_QUICK_START.md) - Quick start guide
- [P2_TASK3_IMPLEMENTATION_REPORT.md](./P2_TASK3_IMPLEMENTATION_REPORT.md) - Implementation details
- [P2_COGNITIVE_MODEL_DEFINITION.md](./P2_COGNITIVE_MODEL_DEFINITION.md) - Cognitive model specification
- [P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md](./P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md) - Visual encoding rules
