# P2-3: Subgraph API Quick Start Guide

## What is the Subgraph API?

The Subgraph API (`GET /api/brain/subgraph`) lets you query a **cognitive neighborhood** around any entity in your codebase. It's not just graph data - it's cognitive structure with:

- **Evidence-based relationships** (every edge has proof)
- **Coverage metrics** (how well each entity is understood)
- **Blind spot detection** (entities we know we don't know enough about)
- **Visual encoding** (colors, sizes, styles based on cognitive attributes)

Think of it as "show me everything BrainOS understands about X and its neighbors."

---

## Prerequisites

### 1. BrainOS Index

You need a BrainOS index before using the API:

```bash
# Build index
cd /path/to/your/repo
agentos brain build

# Or via API
curl -X POST "http://localhost:5000/api/brain/build"
```

This creates `.brainos/v0.1_mvp.db` with your cognitive graph.

### 2. WebUI Running

Start the AgentOS WebUI:

```bash
agentos webui
```

The API will be available at `http://localhost:5000/api/brain/subgraph`.

---

## Basic Usage

### 1. Query with curl

**Simplest Query**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py"
```

**With Parameters**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=1"
```

**Pretty Print**:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py" | jq .
```

### 2. Query with Python

**Install requests**:
```bash
pip install requests
```

**Query Script** (`query_subgraph.py`):
```python
import requests
import json

# Query subgraph
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
    print("✅ Query successful")
    print(f"Cached: {data['cached']}")

    # Print metadata
    metadata = data["data"]["metadata"]
    print(f"\nSubgraph:")
    print(f"  - Seed: {metadata['seed_entity']}")
    print(f"  - Nodes: {metadata['total_nodes']}")
    print(f"  - Edges: {metadata['total_edges']}")
    print(f"  - Coverage: {metadata['coverage_percentage'] * 100:.1f}%")
    print(f"  - Evidence Density: {metadata['evidence_density']:.1f}")
    print(f"  - Blind Spots: {metadata['blind_spot_count']}")

    # Print nodes
    print(f"\nNodes:")
    for node in data["data"]["nodes"][:5]:  # First 5
        print(f"  - {node['entity_key']} ({node['entity_type']})")
        print(f"    Evidence: {node['evidence_count']}")
        print(f"    Sources: {', '.join(node['coverage_sources'])}")
        print(f"    Blind Spot: {node['is_blind_spot']}")

    # Print edges
    print(f"\nEdges:")
    for edge in data["data"]["edges"][:5]:  # First 5
        print(f"  - {edge['edge_type']}: {edge['source_id']} -> {edge['target_id']}")
        print(f"    Evidence: {edge['evidence_count']}")
        print(f"    Types: {', '.join(edge['evidence_types'])}")
else:
    print(f"❌ Error: {data['error']}")
```

**Run**:
```bash
python query_subgraph.py
```

### 3. Query with JavaScript (Browser)

**HTML Page** (`subgraph_test.html`):
```html
<!DOCTYPE html>
<html>
<head>
    <title>Subgraph API Test</title>
</head>
<body>
    <h1>Subgraph API Test</h1>

    <div>
        <label>Seed: <input id="seed" value="file:manager.py" /></label>
        <label>k_hop: <input id="k_hop" type="number" value="2" /></label>
        <button onclick="querySubgraph()">Query</button>
    </div>

    <pre id="result"></pre>

    <script>
    async function querySubgraph() {
        const seed = document.getElementById('seed').value;
        const k_hop = document.getElementById('k_hop').value;

        const response = await fetch(
            `/api/brain/subgraph?seed=${seed}&k_hop=${k_hop}`
        );
        const data = await response.json();

        if (data.ok) {
            const metadata = data.data.metadata;
            document.getElementById('result').textContent =
                `✅ Query successful (cached: ${data.cached})\n\n` +
                `Subgraph:\n` +
                `  - Nodes: ${metadata.total_nodes}\n` +
                `  - Edges: ${metadata.total_edges}\n` +
                `  - Coverage: ${(metadata.coverage_percentage * 100).toFixed(1)}%\n` +
                `  - Blind Spots: ${metadata.blind_spot_count}\n\n` +
                JSON.stringify(data.data, null, 2);
        } else {
            document.getElementById('result').textContent =
                `❌ Error: ${data.error}`;
        }
    }
    </script>
</body>
</html>
```

**Open in Browser**:
```bash
open subgraph_test.html
```

---

## Common Use Cases

### Use Case 1: Explore File Dependencies

**Goal**: Understand what a file depends on and who depends on it.

```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=1&min_evidence=2"
```

This returns:
- All files imported by `manager.py`
- All files that import `manager.py`
- Only relationships with >= 2 evidence (high confidence)

### Use Case 2: Understand Capability Scope

**Goal**: See what code implements a capability.

```bash
curl "http://localhost:5000/api/brain/subgraph?seed=capability:task_execution&k_hop=2"
```

This returns:
- Files that implement the capability
- Other capabilities it depends on
- Terms related to the capability

### Use Case 3: Trace Term Usage

**Goal**: Find all references to a term/concept.

```bash
curl "http://localhost:5000/api/brain/subgraph?seed=term:retry&k_hop=3"
```

This returns:
- Files that use "retry" (from code/docs)
- Related terms (from docs)
- Commits mentioning "retry" (from git)

### Use Case 4: Detect Cognitive Gaps

**Goal**: Find blind spots in understanding.

```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=1"
```

Then check:
```python
data = response.json()
blind_spot_nodes = [n for n in data["data"]["nodes"] if n["is_blind_spot"]]
print(f"Found {len(blind_spot_nodes)} blind spots")

for node in blind_spot_nodes:
    print(f"  - {node['entity_key']}: {node['blind_spot_reason']}")
```

### Use Case 5: Include Suspected Edges

**Goal**: See potential relationships that lack evidence.

```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&include_suspected=true"
```

This includes edges with 0 evidence (shown with dashed lines in visualizations).

---

## Understanding the Response

### Key Fields

**ok**: Boolean indicating success
```json
{
  "ok": true,  // Success
  "ok": false  // Error (check error field)
}
```

**data.nodes**: Array of cognitive nodes
```json
{
  "id": "n123",
  "entity_key": "manager.py",
  "evidence_count": 15,        // Total evidence
  "coverage_sources": ["git", "doc", "code"],  // Evidence diversity
  "is_blind_spot": false,      // Cognitive gap detected?
  "visual": {
    "color": "#00C853",        // Green = strong coverage
    "label": "manager.py\n✅ 85% | 15 evidence"
  }
}
```

**data.edges**: Array of cognitive edges
```json
{
  "id": "e456",
  "edge_type": "imports",
  "evidence_count": 3,         // Evidence count
  "confidence": 0.7,           // Confidence score
  "status": "confirmed",       // confirmed or suspected
  "visual": {
    "width": 2,                // Thicker = more evidence
    "style": "solid"           // solid=confirmed, dashed=suspected
  }
}
```

**data.metadata**: Subgraph summary
```json
{
  "total_nodes": 12,
  "total_edges": 18,
  "coverage_percentage": 0.83,      // 83% of nodes have evidence
  "evidence_density": 8.5,          // Average 8.5 evidence per edge
  "blind_spot_count": 2,            // 2 cognitive blind spots
  "missing_connections_count": 3    // 3 detected gaps
}
```

**cached**: Whether result came from cache
```json
{
  "cached": false  // Fresh query
  "cached": true   // Returned from cache (faster)
}
```

---

## Visual Encoding Guide

### Node Colors

- **🟢 Green** (`#00C853`): Strong coverage (git + doc + code)
- **🔵 Blue** (`#4A90E2`): Medium coverage (2 sources)
- **🟠 Orange** (`#FFA000`): Weak coverage (1 source)
- **🔴 Red** (`#FF0000`): No evidence (should not happen)

### Node Sizes

- **Large**: High evidence count + high fan-in (important node)
- **Medium**: Moderate evidence
- **Small**: Low evidence

### Node Borders

- **🔴 Red Dashed**: High-risk blind spot (severity >= 0.7)
- **🟠 Orange Dashed**: Medium-risk blind spot (severity >= 0.4)
- **🟡 Yellow Dotted**: Low-risk blind spot (severity < 0.4)
- **Solid**: Normal node

### Edge Styles

- **Solid**: Confirmed edge (evidence >= 1)
- **Dashed**: Suspected edge (evidence = 0)
- **Dotted**: "mentions" relationship

### Edge Widths

- **1px**: Weak (1 evidence)
- **2px**: Medium (2-4 evidence)
- **3px**: Strong (5-9 evidence)
- **4px**: Very strong (10+ evidence)

---

## Troubleshooting

### Error: "BrainOS index not found"

**Problem**: No index exists.

**Solution**:
```bash
agentos brain build
```

### Error: "Seed entity not found"

**Problem**: Entity not indexed.

**Solution**: Rebuild index or check seed format:
```bash
# Wrong
seed=manager.py

# Correct
seed=file:manager.py
```

### Error: "Invalid seed format"

**Problem**: Missing type prefix.

**Solution**: Use `type:key` format:
```bash
# Valid formats
seed=file:manager.py
seed=capability:api
seed=term:authentication
seed=doc:README.md
```

### Empty Results

**Problem**: No neighbors found.

**Possible Reasons**:
1. `min_evidence` too high (try lowering to 1)
2. `k_hop` too small (try increasing to 2-3)
3. Entity is isolated (no connections in graph)

**Solution**:
```bash
# Lower evidence threshold
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&min_evidence=1"

# Include suspected edges
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=2&include_suspected=true"
```

### Slow Queries

**Problem**: Query takes > 1 second.

**Solutions**:
1. Use caching (repeat same query within 15 min)
2. Reduce `k_hop` (3-hop can be expensive)
3. Increase `min_evidence` (filters out weak edges)

**Check Cache**:
```python
response1 = requests.get(...)  # First call: cached=False
response2 = requests.get(...)  # Second call: cached=True (fast!)
```

---

## Best Practices

### 1. Start Small

```bash
# ✅ Good: Start with 1-hop
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=1"

# ❌ Bad: Start with 3-hop (may be slow/large)
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&k_hop=3"
```

### 2. Use Evidence Filtering

```bash
# ✅ Good: Filter weak relationships
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&min_evidence=2"

# ❌ Bad: Include all relationships (may be noisy)
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py&min_evidence=1&include_suspected=true"
```

### 3. Check Blind Spots

```python
# ✅ Good: Highlight cognitive gaps
data = response.json()
blind_spots = [n for n in data["data"]["nodes"] if n["is_blind_spot"]]
if blind_spots:
    print("⚠️ Blind spots detected:")
    for bs in blind_spots:
        print(f"  - {bs['entity_key']}: {bs['blind_spot_reason']}")
```

### 4. Use Caching

```python
# ✅ Good: Reuse cached results
for _ in range(10):
    response = requests.get(...)  # Only first call hits database
    print(f"Cached: {response.json()['cached']}")
```

### 5. Handle Errors

```python
# ✅ Good: Check ok field
data = response.json()
if not data["ok"]:
    print(f"Error: {data['error']}")
    sys.exit(1)

# ❌ Bad: Assume success
nodes = response.json()["data"]["nodes"]  # May crash if error
```

---

## Next Steps

1. **API Reference**: See [P2_TASK3_API_REFERENCE.md](./P2_TASK3_API_REFERENCE.md) for complete API documentation
2. **Implementation Details**: See [P2_TASK3_IMPLEMENTATION_REPORT.md](./P2_TASK3_IMPLEMENTATION_REPORT.md)
3. **Cognitive Model**: See [P2_COGNITIVE_MODEL_DEFINITION.md](./P2_COGNITIVE_MODEL_DEFINITION.md)
4. **Visual Semantics**: See [P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md](./P2_VISUAL_SEMANTICS_QUICK_REFERENCE.md)

---

## Examples Library

### Example 1: Find High-Risk Files

```python
import requests

response = requests.get(
    "http://localhost:5000/api/brain/subgraph",
    params={"seed": "file:manager.py", "k_hop": 1}
)

data = response.json()
if data["ok"]:
    # Find nodes with high in-degree (many dependents)
    high_risk = [
        n for n in data["data"]["nodes"]
        if n["in_degree"] > 5 and n["evidence_count"] < 10
    ]
    print(f"High-risk files: {len(high_risk)}")
    for node in high_risk:
        print(f"  - {node['entity_key']}: {node['in_degree']} dependents, {node['evidence_count']} evidence")
```

### Example 2: Generate DOT Graph

```python
import requests

response = requests.get(
    "http://localhost:5000/api/brain/subgraph",
    params={"seed": "file:manager.py", "k_hop": 2}
)

data = response.json()
if data["ok"]:
    # Generate GraphViz DOT format
    print("digraph G {")

    # Nodes
    for node in data["data"]["nodes"]:
        color = node["visual"]["color"]
        label = node["entity_key"]
        print(f'  "{node["id"]}" [label="{label}", color="{color}"];')

    # Edges
    for edge in data["data"]["edges"]:
        style = edge["visual"]["style"]
        print(f'  "{edge["source_id"]}" -> "{edge["target_id"]}" [style={style}];')

    print("}")
```

Save as `graph.dot` and render:
```bash
python generate_dot.py > graph.dot
dot -Tpng graph.dot -o graph.png
open graph.png
```

### Example 3: Export to JSON

```python
import requests
import json

response = requests.get(
    "http://localhost:5000/api/brain/subgraph",
    params={"seed": "file:manager.py", "k_hop": 2}
)

# Save to file
with open("subgraph.json", "w") as f:
    json.dump(response.json(), f, indent=2)

print("✅ Saved to subgraph.json")
```

---

## FAQ

**Q: What's the difference between this and a regular graph query?**

A: Regular graph queries return structure. This API returns **cognitive structure** - every node/edge has evidence counts, coverage metrics, blind spot detection, and visual encoding based on cognitive attributes.

**Q: How long are results cached?**

A: 15 minutes. After that, the next query will re-execute and cache again.

**Q: Can I query multiple seeds at once?**

A: Not yet. Current API supports single seed. For multiple seeds, make multiple queries or use a batch endpoint (future feature).

**Q: What's the max k_hop?**

A: 3. Higher values would traverse too much of the graph and cause performance issues.

**Q: Why are some edges "suspected"?**

A: Suspected edges have 0 evidence. They may exist in the graph schema but lack proof. Use `include_suspected=true` to see them.

**Q: What does "blind spot" mean?**

A: A blind spot is an entity we know exists but don't have enough evidence/documentation about. It's a **cognitive gap** - we know we don't know enough.

---

**Ready to use the API?** Start with:
```bash
curl "http://localhost:5000/api/brain/subgraph?seed=file:manager.py" | jq .
```
