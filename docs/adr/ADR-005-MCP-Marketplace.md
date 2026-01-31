# ADR-005: MCP Marketplace is NOT an App Store

## Status
Accepted

## Context

AgentOS needs a UI to manage third-party MCP integration, allowing users to discover and attach MCP servers. However, we need to be crystal clear about what this system is and is not:

**This is NOT a plugin marketplace like Chrome Web Store or VS Code Extensions.**

This is a **capability discovery and governance preview layer** - a controlled interface for:
1. Discovering available MCP capabilities
2. Previewing governance implications before attachment
3. Attaching MCP servers to AgentOS (with audit)
4. Enforcing disabled-by-default policy

## Decision

### What MCP Marketplace IS

1. **Capability Discovery Layer**
   - Browse available MCP packages with metadata
   - Search and filter by tags, trust tier, side effects
   - View tool declarations and capabilities

2. **Governance Preview Tool**
   - Pre-attachment risk assessment
   - Trust Tier inference based on transport type
   - Risk Level calculation based on side effects
   - Quota recommendations
   - Admin token requirements preview

3. **Controlled Attachment Interface**
   - Attach MCP servers to local AgentOS config
   - **Default state: disabled** (not executable)
   - Full audit trail of all attachments
   - Trust tier override with warnings

4. **Upstream View of Governance**
   - Shows "what would happen if we attach"
   - NOT "what permissions do we grant"
   - Governance decisions still made by policy engine at runtime

### What MCP Marketplace IS NOT

- ❌ **NOT a SaaS application marketplace**
- ❌ **NOT a one-click install tool**
- ❌ **NOT a plugin store**
- ❌ **NOT an execution environment**
- ❌ **NOT a permissions manager** (that's Governance)
- ❌ **NOT a bypass for security gates**

### Core Principle: Discover → Inspect → Approve → Attach

**NOT**: Browse → Install → Use

**YES**: Discover → Inspect → Approve → Attach → Enable (via CLI/explicit action)

## Key Design Decisions

### 1. Attach ≠ Enable

**Problem**: Users might expect "attach" to mean "ready to use"

**Decision**: 
- Attach writes MCP config with `enabled: false`
- Requires explicit enable action (CLI or API with admin token)
- WebUI shows "Attached but not enabled" status clearly

**Rationale**: 
- Prevents silent activation of high-risk capabilities
- Gives users time to review before enabling
- Maintains governance control surface

### 2. Marketplace Has No Execution Authority

**Problem**: Marketplace could become a backdoor for tool execution

**Decision**:
- Marketplace API has zero tool execution endpoints
- Cannot call `/execute`, `/invoke`, `/call`
- Cannot bypass security gates
- Cannot modify governance policies

**Enforcement**:
- Code review: no execution logic in marketplace
- Test coverage: verify no execution endpoints
- Audit: all attachments logged, but no execution events

### 3. Governance Preview is Core UX

**Problem**: Users need to understand risks before attaching

**Decision**:
- Every package has governance preview endpoint
- Preview shows:
  - Inferred Trust Tier (based on transport)
  - Risk Level (based on side effects)
  - Default Quota
  - Admin Token requirements
  - Gate warnings
- Preview is generated on-demand, not stored

**Rationale**:
- Users make informed decisions
- No surprises after attachment
- Transparency builds trust

### 4. Audit is Mandatory

**Problem**: Need traceability for all MCP attachments

**Decision**:
- Every attach creates `mcp_attached` audit event
- Audit includes:
  - package_id
  - trust_tier (including override)
  - transport type
  - side effects declared
  - enabled state (always false initially)
  - timestamp
- No attachment without audit

**Rationale**:
- Compliance and accountability
- Debug and troubleshooting
- Security incident investigation

### 5. Data Source is Controlled

**Problem**: Where does package metadata come from?

**Decision** (Current):
- Local YAML registry (`data/mcp_registry.yaml`)
- Version controlled with AgentOS
- Manually curated by AgentOS team

**Decision** (Future):
- Can extend to remote catalog (pull metadata only)
- **Never trust remote** - always verify locally
- Governance decisions still made by local policy engine

**Rationale**:
- Local registry is auditable and versioned
- No dependency on external services
- Users can fork and customize
- Future flexibility without compromising security

## Implementation

### Data Layer

**Files**:
- `agentos/core/mcp/marketplace_models.py` - Pydantic models
- `agentos/core/mcp/marketplace_registry.py` - Registry manager
- `data/mcp_registry.yaml` - Package declarations

**Models**:
- `MCPPackage` - Complete package metadata
- `MCPGovernancePreview` - Risk assessment preview
- `MCPToolDeclaration` - Individual tool metadata
- `MCPSideEffect` - Side effect types

### API Layer

**Files**:
- `agentos/webui/api/mcp_marketplace.py` - FastAPI routes

**Endpoints**:
```
GET  /api/mcp/marketplace/packages                  # List packages (Discover)
GET  /api/mcp/marketplace/packages/{package_id}     # Get details (Inspect)
GET  /api/mcp/marketplace/governance-preview/{id}   # Preview governance (Approve)
POST /api/mcp/marketplace/attach                    # Attach MCP (Attach)
```

**RED LINES**:
- ❌ No `/execute`, `/call`, `/invoke` endpoints
- ❌ No permission modification endpoints
- ❌ No gate bypass mechanisms

### Attachment Flow

```
User clicks "Attach" → API validates package_id
                    → Generate server_id
                    → Determine trust_tier (with override support)
                    → Write MCP config with enabled=false
                    → Emit audit event (mcp_attached)
                    → Return warnings and next_steps
                    → User must explicitly enable via CLI/API
```

### Governance Preview Logic

```python
# Infer Trust Tier from transport
stdio → T1
http/https → T3
tcp/ssh → T2

# Infer Risk Level from Trust Tier
T0 → LOW
T1 → MEDIUM
T2 → HIGH
T3 → CRITICAL

# Admin Token required if:
- Trust Tier is T3, OR
- Package declares side effects

# Gate Warnings:
- No side effects declared → Policy Gate may block
- Large tool set (>10) → Quota limits may be hit faster
- T2/T3 tier → Requires careful approval
```

## Consequences

### Positive

1. **Clear Mental Model**
   - Users understand Marketplace is discovery, not execution
   - No confusion about "installed but not working"
   - Governance stays in Governance module

2. **Security by Default**
   - High-risk MCPs cannot silent enable
   - All attachments audited
   - No execution backdoors

3. **Auditability**
   - Complete trace of what was attached, when, by whom
   - Trust tier overrides are logged
   - Can reconstruct attachment history

4. **Governance Integrity**
   - Marketplace cannot bypass gates
   - Policy engine makes all runtime decisions
   - No permission escalation path

### Negative

1. **Extra Steps for Users**
   - Not as smooth as "one-click install"
   - Requires CLI command after attachment
   - Might frustrate users wanting quick setup

2. **Initial Friction**
   - Users need to learn "Attach ≠ Enable" concept
   - Extra click/command to actually use MCP
   - More documentation needed

### Mitigation

1. **Clear UI Guidance**
   - Show "Next Steps" prominently after attachment
   - Link to Capabilities page to enable
   - Tooltip explaining why MCP is disabled

2. **Streamlined Enable Flow** (Future)
   - Consider "Attach + Enable" button with:
     - Clear warnings
     - Admin token requirement
     - Audit event
   - Still requires explicit user action
   - Not a silent enable

3. **Documentation**
   - Quick start guide: "Attaching vs Enabling"
   - Video tutorial
   - FAQ section

## Security Analysis

### Threat: Marketplace becomes execution backdoor

**Mitigation**: 
- No execution endpoints in marketplace API
- Code review and tests enforce this
- Marketplace module cannot import ToolRouter

### Threat: Silent enable of high-risk MCP

**Mitigation**:
- `enabled: false` is hardcoded in attach logic
- Test coverage verifies disabled state
- Audit event records disabled state

### Threat: Governance policy bypass

**Mitigation**:
- Marketplace only writes config, doesn't grant permissions
- Policy engine evaluates at runtime
- No override mechanism in marketplace

### Threat: Malicious package in registry

**Mitigation**:
- Local registry is version controlled
- Manual curation by AgentOS team
- Users can inspect YAML before use
- Future: Package signature verification

## Related ADRs

- **ADR-001**: Capability Abstraction Layer - How MCP fits into unified capability system
- **ADR-002**: Trust Tier Topology - T0-T3 trust tier definitions
- **ADR-003**: Provenance System - Audit trail for capability operations
- **ADR-EXT-001**: Declarative Extensions Only - Why marketplace uses declarations

## Future Considerations

### Remote Catalog Support

**Idea**: Pull package metadata from remote catalog (e.g., https://marketplace.agentos.dev)

**Requirements**:
- Only pull metadata (YAML), never code
- Verify signatures
- Local caching
- Fallback to local registry

### Community Contributions

**Idea**: Allow users to submit packages to official registry

**Requirements**:
- Package review process
- Security audit for T2/T3 packages
- Source code inspection
- Test coverage requirement

### Package Ratings and Reviews

**Idea**: Add user ratings and reviews

**Concerns**:
- Need backend service
- Moderation requirements
- Privacy considerations

### Auto-Update Mechanism

**Idea**: Update MCP package versions automatically

**Concerns**:
- Breaking changes
- Security implications
- Need rollback mechanism
- Opt-in only

## References

- MCP Protocol Specification: https://modelcontextprotocol.io
- Extension WebUI Implementation: `agentos/webui/api/extensions.py`
- Governance vNext Design: `docs/governance_vnext.md`
- Capability Registry: `agentos/core/capabilities/registry.py`

## Approval

- **Proposed**: 2026-01-31
- **Accepted**: 2026-01-31
- **Authors**: AgentOS Team
- **Reviewers**: Security Team, Product Team

---

**Summary**: MCP Marketplace is a **discovery and governance preview layer**, not an app store. It helps users understand and attach MCP capabilities with full transparency and audit, while maintaining strict separation from execution and governance enforcement.
