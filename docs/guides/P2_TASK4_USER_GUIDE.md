# P2-4 User Guide: Subgraph Visualization

**Version**: 1.0
**Date**: 2026-01-30
**Audience**: AgentOS users, developers, architects
**Purpose**: Learn how to use the Subgraph Visualization tool

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Understanding Visual Encoding](#3-understanding-visual-encoding)
4. [Identifying Blind Spots](#4-identifying-blind-spots)
5. [Understanding Blank Areas](#5-understanding-blank-areas)
6. [Interaction Guide](#6-interaction-guide)
7. [Advanced Usage](#7-advanced-usage)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Introduction

### What is Subgraph Visualization?

The **Subgraph Visualization** tool is not a traditional "knowledge graph viewer". Instead, it's a **cognitive boundary exploration tool** that helps you answer:

- **"What do I understand about this entity?"**
- **"How strong is my understanding?"**
- **"Where are the gaps in my knowledge?"**

### Key Concepts

- **Subgraph**: A small neighborhood of entities centered around a "seed" entity
- **Cognitive Attributes**: Properties like evidence count, coverage sources, blind spot status
- **Visual Encoding**: Colors, sizes, and styles that represent cognitive attributes
- **Three Red Lines**: Core rules that ensure honesty in visualization

### When to Use This Tool

- **Exploring a new codebase**: Start with key files and see what they depend on
- **Understanding a concept**: Query a term (e.g., `term:authentication`) and see related entities
- **Finding blind spots**: Identify areas with weak evidence or missing documentation
- **Navigating dependencies**: Click through nodes to explore the dependency graph

---

## 2. Getting Started

### Step 1: Access the Tool

1. Open AgentOS WebUI (usually at `http://localhost:5000`)
2. Click **"Subgraph"** in the sidebar (under the "Knowledge" section)
3. You'll see a welcome screen with example seeds

### Step 2: Enter a Seed Entity

A **seed entity** is the starting point for your exploration. Format: `type:key`

**Types**:
- `file:` - A source code file (e.g., `file:manager.py`)
- `capability:` - A system capability (e.g., `capability:api`)
- `term:` - A concept or term (e.g., `term:authentication`)
- `doc:` - A documentation file (e.g., `doc:README.md`)

**Examples**:
```
file:agentos/core/task/manager.py
capability:brain
term:retry_strategy
doc:architecture/ADR_001.md
```

### Step 3: Click "Query"

1. Enter your seed entity in the input field
2. Click the **"Query"** button (or press Enter)
3. Wait for the loading indicator (usually < 1 second)
4. The graph will appear!

### Step 4: Explore the Graph

- **Zoom**: Scroll with mouse wheel
- **Pan**: Click and drag the canvas
- **Hover**: Move mouse over nodes/edges to see details
- **Click**: Click a node to make it the new seed

---

## 3. Understanding Visual Encoding

The subgraph uses **colors, sizes, and styles** to represent cognitive attributes.

### 3.1 Node Colors (Coverage Sources)

**Color** represents **how many evidence sources** support a node:

| Color | Meaning | Sources |
|-------|---------|---------|
| 🟢 Green | **Strong coverage** | 3 sources (Git + Doc + Code) |
| 🔵 Blue | **Medium coverage** | 2 sources (e.g., Git + Doc) |
| 🟠 Orange | **Weak coverage** | 1 source (e.g., only Git commits) |
| 🔴 Red | **No coverage** | 0 sources (should not happen) |

**Example**:
- **Green node** (`file:manager.py`): Has Git commits, documentation references, and code dependencies
- **Orange node** (`file:utils.py`): Only has Git commits, no documentation or dependencies

### 3.2 Node Sizes (Importance)

**Size** represents **how important** a node is based on:
- **Evidence count**: More evidence = larger node
- **In-degree**: More dependents = larger node
- **Seed status**: The seed node is always larger

**Visual Scale**:
- **Tiny** (20px): Leaf nodes with minimal evidence
- **Small** (30px): Regular nodes
- **Medium** (40px): Nodes with good evidence
- **Large** (50px): Core nodes with many dependencies
- **Extra Large** (65px): Seed node or critical hubs

### 3.3 Node Borders (Blind Spots)

**Border style** marks **cognitive risks**:

| Border | Color | Style | Meaning |
|--------|-------|-------|---------|
| Thin solid | Same as fill | Solid | Normal node |
| **Thick dashed** | 🔴 Red | Dashed | **High-risk blind spot** |
| Medium dashed | 🟠 Orange | Dashed | Medium-risk blind spot |
| Medium dotted | 🟡 Yellow | Dotted | Low-risk blind spot |

**Red Flag**: If you see a **red dashed border**, that entity needs attention!

### 3.4 Edge Thickness (Evidence Count)

**Thickness** represents **how much evidence** supports a relationship:

| Thickness | Evidence | Strength |
|-----------|----------|----------|
| Thin (1px) | 1 evidence | Weak |
| Medium (2px) | 2-4 evidence | Moderate |
| Thick (3px) | 5-9 evidence | Strong |
| Very thick (4px) | 10+ evidence | Very strong |

### 3.5 Edge Colors (Evidence Diversity)

**Color** represents **diversity of evidence types**:

| Color | Types | Example |
|-------|-------|---------|
| 🟢 Green | 3 types | Git commit + Doc reference + Code import |
| 🔵 Blue | 2 types | Git commit + Doc reference |
| ⚪ Gray | 1 type | Only Git commit |
| ⚫ Light gray | 0 types (suspected) | No evidence (rare) |

**Best Practice**: Green edges are the most trustworthy!

### 3.6 Edge Styles

| Style | Meaning |
|-------|---------|
| **Solid** | Confirmed relationship (has evidence) |
| **Dashed** | Suspected relationship (no evidence, shown for completeness) |
| **Dotted** | Weak relationship (e.g., "mentions" in documentation) |

---

## 4. Identifying Blind Spots

### What is a Blind Spot?

A **blind spot** is an entity or relationship where **understanding is risky**. Examples:
- **High fan-in, no documentation**: Many files depend on it, but no docs explain why
- **Orphan node**: Exists in codebase but has no connections
- **Capability without implementation**: Declared in docs but no code implements it

### How to Spot Them

1. **Look for red dashed borders** around nodes
2. **Hover** to see blind spot details:
   - **Severity**: 0.0 (low) to 1.0 (high)
   - **Type**: e.g., "high_fan_in_undocumented"
   - **Reason**: e.g., "15 files depend on this, but no documentation"
   - **Suggested Action**: e.g., "Add ADR explaining architecture"

### Example

```
Node: file:governance.py
Border: 🔴 Red dashed (thick)
Tooltip:
  ⚠️ BLIND SPOT: High Fan-In Undocumented
  Severity: High (0.85)
  Reason: 15 files depend on this, but no documentation exists
  Suggested Action: Add ADR explaining this file's architecture
```

**Action**: You should document `governance.py` to reduce risk!

---

## 5. Understanding Blank Areas

### What Are Blank Areas?

**Blank areas** are **missing connections** that _should_ exist but don't. Examples:
- **Code depends on a file, but no documentation explains why**
- **Two files belong to the same capability, but have no direct connection**
- **A blind spot suggests a missing edge**

### How to Identify Them

1. **Check the metadata panel** (bottom-left):
   - **Missing Connections**: Shows count (e.g., "4")
2. **Look for sparse clusters**: Nodes that _should_ be connected but aren't
3. **Check coverage percentage**: If < 80%, there are likely gaps

### Example

**Metadata Panel**:
```
Seed: file:manager.py
Nodes: 12
Edges: 18
Coverage: 67%  ← ⚠️ Not complete!
Missing Connections: 4  ← ⚠️ Gaps exist!
```

**Interpretation**: This subgraph is only 67% complete. There are 4 relationships that _should_ exist but don't have evidence yet.

---

## 6. Interaction Guide

### 6.1 Hovering (Mouse Over)

**Hover over a node**:
- Shows **tooltip** with:
  - Entity type and key
  - Coverage percentage
  - Evidence count
  - In-degree and out-degree
  - Blind spot info (if applicable)

**Hover over an edge**:
- Shows **tooltip** with:
  - Edge type (e.g., "imports", "depends_on")
  - Evidence count
  - Confidence score
  - Evidence sources (e.g., "Git commit abc123", "Code import statement")

### 6.2 Clicking Nodes

**Click a node** to:
- **Re-query the graph** with that node as the new seed
- **Explore its neighborhood**

**Example Flow**:
1. Start with `file:manager.py`
2. See it depends on `file:service.py`
3. Click `file:service.py`
4. Graph re-queries with `file:service.py` as seed
5. Now you see what `service.py` depends on!

### 6.3 Zooming and Panning

- **Zoom In/Out**: Scroll mouse wheel (or pinch on trackpad)
- **Pan**: Click and drag the canvas
- **Zoom Range**: 0.3x (30%) to 3.0x (300%)

**Tip**: Use zoom to focus on specific clusters!

### 6.4 Filters

**Show/Hide Blind Spots**:
- ☑ Checked: Blind spots visible (default)
- ☐ Unchecked: Blind spots hidden (useful for "clean" view)

**Show/Hide Weak Edges**:
- ☑ Checked: Edges with low evidence visible (default)
- ☐ Unchecked: Only strong edges shown

**K-Hop Slider** (1-3):
- **1-hop**: Only immediate neighbors
- **2-hop**: Neighbors + neighbors of neighbors (default)
- **3-hop**: Deep exploration (may be slow for large graphs)

**Min Evidence Slider** (1-10):
- **1**: Show all edges (default)
- **5**: Only edges with 5+ evidence
- **10**: Only very strong edges

---

## 7. Advanced Usage

### 7.1 URL Parameters

You can **share subgraph views** with URL parameters:

```
http://localhost:5000/#subgraph?seed=file:manager.py&k_hop=2&min_evidence=1
```

### 7.2 Finding Critical Nodes

**Goal**: Find nodes that many others depend on (high fan-in).

**Steps**:
1. Load a central file (e.g., `file:manager.py`)
2. Look for **large nodes** with **many incoming edges**
3. Check if they have **red borders** (blind spots)
4. Document them if needed!

### 7.3 Tracing Dependencies

**Goal**: Understand what a file depends on.

**Steps**:
1. Start with your file (e.g., `file:api.py`)
2. Look at **outgoing edges** (arrows pointing away)
3. **Click** on dependency nodes to explore deeper

### 7.4 Concept Exploration

**Goal**: Understand a term or concept.

**Steps**:
1. Query a term (e.g., `term:retry_strategy`)
2. See which files, docs, and capabilities reference it
3. Explore connections to understand how it's used

---

## 8. Troubleshooting

### Problem: "Seed entity not found"

**Cause**: The entity is not indexed yet.

**Solution**:
1. Run `/brain build` in AgentOS CLI to build the index
2. Wait for indexing to complete
3. Try your query again

### Problem: "Invalid seed format"

**Cause**: Seed is missing the `type:` prefix.

**Solution**: Use format `type:key`, e.g., `file:manager.py` (not just `manager.py`)

### Problem: Graph looks like a "hairball" (too messy)

**Cause**: Too many nodes (k-hop too high or seed too central).

**Solution**:
1. Reduce k-hop to 1
2. Increase min_evidence to 3 or 5 (filter weak edges)
3. Choose a more specific seed

### Problem: No nodes are blind spots, but I know there are gaps

**Cause**: Blind spot detection depends on BrainOS index completeness.

**Solution**:
1. Ensure all sources (Git, Docs, Code) are indexed
2. Run `/brain rebuild` to refresh the index
3. Query again

### Problem: Graph loads slowly (> 5 seconds)

**Cause**: Subgraph is too large (100+ nodes).

**Solution**:
1. Reduce k-hop to 1
2. Increase min_evidence to filter edges
3. Choose a more specific seed (leaf node instead of core node)

---

## Appendix A: Visual Encoding Cheatsheet

**Nodes**:
- 🟢 Green = Strong (3 sources)
- 🔵 Blue = Medium (2 sources)
- 🟠 Orange = Weak (1 source)
- 🔴 Red dashed border = Blind spot

**Edges**:
- Thick = Many evidence (5+)
- Thin = Few evidence (1-2)
- 🟢 Green = Multi-type evidence
- ⚪ Gray = Single-type evidence
- Dashed = Suspected (no evidence)

**Size**:
- Large = Important (high evidence, high fan-in)
- Small = Leaf node

---

## Appendix B: Example Queries

**Explore a file**:
```
file:agentos/core/task/manager.py
```

**Explore a capability**:
```
capability:api
```

**Explore a concept**:
```
term:authentication
```

**Explore a document**:
```
doc:architecture/ADR_001.md
```

---

**User Guide Status**: ✅ Complete
**Word Count**: ~2,100 words
**Last Updated**: 2026-01-30
