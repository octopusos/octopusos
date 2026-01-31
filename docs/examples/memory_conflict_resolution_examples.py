"""
Memory Conflict Resolution Examples

Task #12: 实现Memory冲突解决策略

This file contains practical examples demonstrating the Memory conflict
resolution system in various scenarios.
"""

from agentos.core.memory.service import MemoryService


def example_1_user_changes_mind():
    """
    Example 1: User changes their mind about their preferred name.

    Scenario:
    - First: "Please call me Zhang San"
    - Later: "Actually, call me Li Si instead"

    Expected behavior:
    - Old value is preserved but marked as superseded
    - New value becomes active
    - Version chain is maintained
    """
    print("=" * 60)
    print("Example 1: User Changes Mind")
    print("=" * 60)

    memory_service = MemoryService()

    # First preference
    print("\n1. User says: 'Please call me Zhang San'")
    id1 = memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "preferred_name",
            "value": "张三"
        },
        "confidence": 0.9
    })
    print(f"   → Created memory: {id1}")

    # List active memories
    active = memory_service.list(scope="global")
    print(f"   → Active memories: {len(active)}")
    print(f"   → Current name: {active[0]['content']['value']}")

    # User changes mind
    print("\n2. User says: 'Actually, call me Li Si'")
    id2 = memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "preferred_name",
            "value": "李四"
        },
        "confidence": 0.9
    })
    print(f"   → Created memory: {id2}")

    # List active memories (should only show new one)
    active = memory_service.list(scope="global")
    print(f"   → Active memories: {len(active)}")
    print(f"   → Current name: {active[0]['content']['value']}")

    # Check old memory status
    old_memory = memory_service.get(id1)
    print(f"\n3. Old memory status:")
    print(f"   → ID: {old_memory['id']}")
    print(f"   → Active: {old_memory['is_active']}")
    print(f"   → Version: {old_memory['version']}")
    print(f"   → Superseded by: {old_memory['superseded_by']}")

    # Check new memory status
    new_memory = memory_service.get(id2)
    print(f"\n4. New memory status:")
    print(f"   → ID: {new_memory['id']}")
    print(f"   → Active: {new_memory['is_active']}")
    print(f"   → Version: {new_memory['version']}")
    print(f"   → Supersedes: {new_memory['supersedes']}")

    # Get version history
    history = memory_service.get_version_history(id2)
    print(f"\n5. Version history:")
    for i, mem in enumerate(history, 1):
        print(f"   v{i}: {mem['content']['value']} "
              f"(active={mem['is_active']}, id={mem['id']})")


def example_2_high_confidence_wins():
    """
    Example 2: High confidence memory prevents superseding.

    Scenario:
    - User explicitly sets preference (high confidence)
    - System infers different preference (low confidence)

    Expected behavior:
    - Explicit preference is retained (higher confidence wins)
    - Inferred preference is rejected
    """
    print("\n\n" + "=" * 60)
    print("Example 2: High Confidence Wins")
    print("=" * 60)

    memory_service = MemoryService()

    # User explicit preference
    print("\n1. User explicitly sets: 'My language is Chinese'")
    id1 = memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "preferred_language",
            "value": "Chinese"
        },
        "confidence": 0.95  # Very high confidence
    })
    print(f"   → Created memory: {id1} (confidence: 0.95)")

    # System inference (wrong)
    print("\n2. System infers: 'Maybe user prefers English?' (low confidence)")
    id2 = memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "preferred_language",
            "value": "English"
        },
        "confidence": 0.6  # Lower confidence
    })
    print(f"   → Attempted to create memory")
    print(f"   → Returned ID: {id2}")
    print(f"   → Same as original? {id1 == id2}")

    # Check active memory
    active = memory_service.list(scope="global")
    print(f"\n3. Active memory:")
    print(f"   → Language: {active[0]['content']['value']}")
    print(f"   → Confidence: {active[0]['confidence']}")
    print(f"   → Result: High confidence preference RETAINED ✓")


def example_3_multiple_updates():
    """
    Example 3: Multiple updates create version chain.

    Scenario:
    - User updates preference 3 times
    - Each update supersedes the previous

    Expected behavior:
    - Version numbers increment
    - Chain links all versions
    - History retrieval works from any point
    """
    print("\n\n" + "=" * 60)
    print("Example 3: Multiple Updates (Version Chain)")
    print("=" * 60)

    memory_service = MemoryService()

    names = ["张三", "李四", "王五"]
    ids = []

    for i, name in enumerate(names, 1):
        print(f"\n{i}. User updates name to: '{name}'")
        mem_id = memory_service.upsert({
            "scope": "global",
            "type": "preference",
            "content": {
                "key": "team_lead_name",
                "value": name
            },
            "confidence": 0.9
        })
        ids.append(mem_id)
        print(f"   → Memory ID: {mem_id}")

    # Check version chain
    print(f"\n4. Version chain analysis:")
    for i, mem_id in enumerate(ids, 1):
        mem = memory_service.get(mem_id)
        print(f"   v{i} ({mem_id}):")
        print(f"      - Value: {mem['content']['value']}")
        print(f"      - Version: {mem['version']}")
        print(f"      - Active: {mem['is_active']}")
        print(f"      - Supersedes: {mem.get('supersedes', 'None')}")
        print(f"      - Superseded by: {mem.get('superseded_by', 'None')}")

    # Get history from latest
    print(f"\n5. Full history (from latest):")
    history = memory_service.get_version_history(ids[-1])
    for mem in history:
        print(f"   v{mem['version']}: {mem['content']['value']} "
              f"({'ACTIVE' if mem['is_active'] else 'superseded'})")


def example_4_different_scopes_no_conflict():
    """
    Example 4: Same key in different scopes doesn't conflict.

    Scenario:
    - Global preference: timeout = 30s
    - Project preference: timeout = 60s

    Expected behavior:
    - Both exist independently (different scopes)
    - No conflict detected
    """
    print("\n\n" + "=" * 60)
    print("Example 4: Different Scopes, No Conflict")
    print("=" * 60)

    memory_service = MemoryService()

    # Global timeout
    print("\n1. Set global timeout: 30s")
    id1 = memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "timeout",
            "value": "30s"
        },
        "confidence": 0.9
    })
    print(f"   → Created memory: {id1}")

    # Project-specific timeout
    print("\n2. Set project timeout: 60s")
    id2 = memory_service.upsert({
        "scope": "project",
        "type": "preference",
        "content": {
            "key": "timeout",
            "value": "60s"
        },
        "confidence": 0.9,
        "project_id": "proj-123"
    })
    print(f"   → Created memory: {id2}")

    # Both should exist
    print(f"\n3. Check both memories exist:")
    global_mem = memory_service.get(id1)
    project_mem = memory_service.get(id2)

    print(f"   → Global timeout: {global_mem['content']['value']} "
          f"(active={global_mem['is_active']})")
    print(f"   → Project timeout: {project_mem['content']['value']} "
          f"(active={project_mem['is_active']})")
    print(f"   → Result: Both coexist (different scopes) ✓")


def example_5_audit_trail():
    """
    Example 5: Audit trail with include_inactive.

    Scenario:
    - Create and update a preference
    - View audit trail showing all versions

    Expected behavior:
    - Active-only query returns latest
    - Audit query returns all versions
    """
    print("\n\n" + "=" * 60)
    print("Example 5: Audit Trail")
    print("=" * 60)

    memory_service = MemoryService()

    # Create initial preference
    print("\n1. Create initial preference")
    memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "notification_style",
            "value": "email"
        },
        "confidence": 0.9
    })

    # Update preference
    print("2. Update to SMS")
    memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "notification_style",
            "value": "sms"
        },
        "confidence": 0.9
    })

    # Update again
    print("3. Update to push notification")
    memory_service.upsert({
        "scope": "global",
        "type": "preference",
        "content": {
            "key": "notification_style",
            "value": "push"
        },
        "confidence": 0.9
    })

    # Active-only query
    print("\n4. Active-only query:")
    active = memory_service.list(scope="global")
    print(f"   → Count: {len(active)}")
    for mem in active:
        print(f"   → {mem['content']['value']} (v{mem['version']})")

    # Audit query (include inactive)
    print("\n5. Audit query (all versions):")
    all_memories = memory_service.list(scope="global", include_inactive=True)
    print(f"   → Count: {len(all_memories)}")
    for mem in sorted(all_memories, key=lambda m: m['version']):
        status = "ACTIVE" if mem['is_active'] else "superseded"
        print(f"   → v{mem['version']}: {mem['content']['value']} ({status})")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Memory Conflict Resolution Examples" + " " * 12 + "║")
    print("║" + " " * 18 + "Task #12 Demonstrations" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")

    example_1_user_changes_mind()
    example_2_high_confidence_wins()
    example_3_multiple_updates()
    example_4_different_scopes_no_conflict()
    example_5_audit_trail()

    print("\n\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
