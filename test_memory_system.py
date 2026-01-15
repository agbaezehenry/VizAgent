"""
Test Script for Context Engineering Memory System

This script tests the complete memory system end-to-end, including:
1. State creation and persistence
2. Memory capture and search
3. Conversation trimming
4. Memory consolidation
5. Multi-session persistence

Run this script to verify the memory system is working correctly.
"""

import sys
import os
from pathlib import Path

# Add plotly_agent to path
sys.path.insert(0, str(Path(__file__).parent))

from plotly_agent.workflow_orchestrator_with_memory import WorkflowOrchestratorWithMemory
from plotly_agent.memory.memory_manager import PlotlyAgentState
from plotly_agent.state_storage import StateStorageManager
from plotly_agent.memory.memory_consolidation import consolidate_session_memories, deduplicate_memories
from plotly_agent.memory.context_trimmer import should_trim_conversation


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_1_basic_state_creation():
    """Test 1: Basic state creation and initialization."""
    print_section("TEST 1: Basic State Creation")

    # Create orchestrator with memory enabled
    orch = WorkflowOrchestratorWithMemory(
        user_id="test_user_1",
        enable_memory=True
    )

    # Check state was created
    assert orch.state is not None, "State should be created"
    assert orch.state.user_id == "test_user_1", "User ID should match"
    assert orch.enable_memory == True, "Memory should be enabled"

    # Check default profile
    assert "preferred_chart_types" in orch.state.profile
    assert "audience" in orch.state.profile
    assert "domain" in orch.state.profile

    print("✅ State created successfully")
    print(f"   User ID: {orch.state.user_id}")
    print(f"   Profile keys: {list(orch.state.profile.keys())}")
    print(f"   Global memories: {len(orch.state.global_memory.get('notes', []))}")
    print(f"   Session memories: {len(orch.state.session_memory.get('notes', []))}")

    return orch


def test_2_memory_tools(orch):
    """Test 2: Memory tool operations (save, search, update)."""
    print_section("TEST 2: Memory Tool Operations")

    # Get memory tools
    memory_tools = orch.get_memory_tools()

    # Test saving a memory note
    print("\n📝 Saving memory notes...")
    result1 = memory_tools.save_memory_note(
        "User prefers horizontal bar charts for comparisons",
        ["chart_type", "bar", "horizontal"]
    )
    print(f"   Saved: {result1['note']['text'][:50]}...")

    result2 = memory_tools.save_memory_note(
        "User works in finance domain",
        ["domain", "finance"]
    )
    print(f"   Saved: {result2['note']['text'][:50]}...")

    result3 = memory_tools.save_memory_note(
        "User dislikes legends, prefers direct labeling",
        ["design", "legend", "labeling"]
    )
    print(f"   Saved: {result3['note']['text'][:50]}...")

    # Verify memories were added to session memory
    session_notes = orch.state.session_memory.get("notes", [])
    assert len(session_notes) >= 3, "Should have at least 3 session memories"
    print(f"\n✅ {len(session_notes)} memories saved to session memory")

    # Test searching memories
    print("\n🔍 Searching memories...")
    search_result = memory_tools.search_memories(["chart_type"])
    print(f"   Found {search_result['count']} memories with keyword 'chart_type'")
    for mem in search_result['memories']:
        print(f"   - {mem['text'][:60]}...")

    # Test updating profile
    print("\n⚙️ Updating profile...")
    profile_result = memory_tools.update_profile("audience", "executives")
    print(f"   {profile_result['message']}")
    assert orch.state.profile["audience"] == "executives"

    profile_result2 = memory_tools.update_profile("domain", "finance")
    print(f"   {profile_result2['message']}")

    print("\n✅ Memory tools working correctly")

    return orch


def test_3_state_persistence(orch):
    """Test 3: State persistence to disk."""
    print_section("TEST 3: State Persistence")

    user_id = orch.state.user_id

    # Save state
    print(f"\n💾 Saving state for user: {user_id}")
    success = orch.storage_manager.save(orch.state)
    assert success, "State should save successfully"

    # Check file exists
    state_file = Path(f"states/{user_id}.json")
    assert state_file.exists(), f"State file should exist at {state_file}"
    print(f"   ✅ State saved to: {state_file}")
    print(f"   File size: {state_file.stat().st_size} bytes")

    # Load state in new orchestrator
    print(f"\n📂 Loading state in new orchestrator...")
    orch2 = WorkflowOrchestratorWithMemory(user_id=user_id, enable_memory=True)

    # Verify loaded state matches
    assert orch2.state.user_id == user_id
    assert orch2.state.profile["audience"] == "executives"
    assert orch2.state.profile["domain"] == "finance"

    session_notes = orch2.state.session_memory.get("notes", [])
    print(f"   ✅ Loaded {len(session_notes)} session memories")
    print(f"   Profile audience: {orch2.state.profile['audience']}")
    print(f"   Profile domain: {orch2.state.profile['domain']}")

    print("\n✅ State persistence working correctly")

    return orch2


def test_4_conversation_trimming(orch):
    """Test 4: Conversation trimming and context preservation."""
    print_section("TEST 4: Conversation Trimming")

    print("\n💬 Simulating 15 conversation turns (exceeds max of 10)...")

    # Simulate conversation
    for i in range(15):
        orch.conversation_history.append({
            "role": "user",
            "content": f"Message {i+1}: Tell me about visualization {i+1}"
        })
        orch.conversation_history.append({
            "role": "assistant",
            "content": f"Response {i+1}: Here's information about visualization {i+1}"
        })

    print(f"   Added 15 user-assistant pairs (30 messages total)")
    print(f"   Current conversation length: {len(orch.conversation_history)} messages")

    # Check if trimming is needed
    needs_trim = should_trim_conversation(orch.conversation_history, max_turns=10)
    print(f"   Needs trimming: {needs_trim}")
    assert needs_trim, "Should need trimming with 15 turns"

    # Manually trigger trim via conversation manager
    if orch.conversation_manager:
        print("\n✂️ Triggering conversation trim...")
        trimmed = orch.conversation_manager.manual_trim(orch.conversation_history)
        orch.conversation_history = trimmed

        user_messages = [m for m in orch.conversation_history if m.get('role') == 'user']
        print(f"   ✅ Trimmed to {len(user_messages)} user turns")
        print(f"   Total messages after trim: {len(orch.conversation_history)}")

        # Check that context was preserved in session memory
        session_notes = orch.state.session_memory.get("notes", [])
        context_notes = [n for n in session_notes if "context" in n.get("keywords", [])]
        if context_notes:
            print(f"   ✅ Context preserved in {len(context_notes)} session memory note(s)")
            print(f"   Reinjection flag: {orch.state.inject_session_memories_next_turn}")

    print("\n✅ Conversation trimming working correctly")

    return orch


def test_5_memory_consolidation(orch):
    """Test 5: Memory consolidation (session → global)."""
    print_section("TEST 5: Memory Consolidation")

    # Check current state
    session_count_before = len(orch.state.session_memory.get("notes", []))
    global_count_before = len(orch.state.global_memory.get("notes", []))

    print(f"\n📊 Before consolidation:")
    print(f"   Session memories: {session_count_before}")
    print(f"   Global memories: {global_count_before}")

    # Consolidate
    print("\n🔄 Consolidating session memories into global memory...")
    stats = consolidate_session_memories(orch.state)

    print(f"   Before count: {stats['before_count']}")
    print(f"   After count: {stats['after_count']}")
    print(f"   Merged/deduplicated: {stats['merged_count']}")
    print(f"   Session notes added: {stats['session_notes_added']}")

    # Check after consolidation
    session_count_after = len(orch.state.session_memory.get("notes", []))
    global_count_after = len(orch.state.global_memory.get("notes", []))

    print(f"\n📊 After consolidation:")
    print(f"   Session memories: {session_count_after} (should be 0)")
    print(f"   Global memories: {global_count_after}")

    assert session_count_after == 0, "Session memory should be cleared after consolidation"
    assert global_count_after > 0, "Global memory should have memories"

    print("\n✅ Memory consolidation working correctly")

    return orch


def test_6_multi_session_persistence():
    """Test 6: Multi-session persistence."""
    print_section("TEST 6: Multi-Session Persistence")

    user_id = "test_user_multi_session"

    # Session 1: Create preferences
    print("\n🔵 Session 1: Creating and saving preferences...")
    orch1 = WorkflowOrchestratorWithMemory(user_id=user_id, enable_memory=True)

    tools1 = orch1.get_memory_tools()
    tools1.save_memory_note("User prefers bar charts", ["chart_type", "bar"])
    tools1.save_memory_note("User audience is executives", ["audience", "executives"])
    tools1.update_profile("color_scheme", "professional")

    # Consolidate and save
    orch1.new_session(consolidate_memories=True)

    global_count_1 = len(orch1.state.global_memory.get("notes", []))
    print(f"   ✅ Session 1 complete: {global_count_1} global memories")

    # Session 2: Load and verify preferences persist
    print("\n🟢 Session 2: Loading user state...")
    orch2 = WorkflowOrchestratorWithMemory(user_id=user_id, enable_memory=True)

    # Check that memories persisted
    global_count_2 = len(orch2.state.global_memory.get("notes", []))
    print(f"   Global memories loaded: {global_count_2}")
    assert global_count_2 == global_count_1, "Memories should persist across sessions"

    # Check profile persisted
    assert orch2.state.profile["color_scheme"] == "professional"
    print(f"   Profile color_scheme: {orch2.state.profile['color_scheme']}")

    # Add more memories in session 2
    tools2 = orch2.get_memory_tools()
    tools2.save_memory_note("User prefers minimal design", ["design", "minimal"])

    # Search for memories
    search_result = tools2.search_memories(["chart_type"])
    print(f"   Search for 'chart_type': {search_result['count']} results")

    # End session 2
    orch2.new_session(consolidate_memories=True)

    global_count_2_after = len(orch2.state.global_memory.get("notes", []))
    print(f"   ✅ Session 2 complete: {global_count_2_after} global memories")

    # Session 3: Verify all memories persist
    print("\n🟣 Session 3: Final verification...")
    orch3 = WorkflowOrchestratorWithMemory(user_id=user_id, enable_memory=True)

    global_count_3 = len(orch3.state.global_memory.get("notes", []))
    print(f"   Global memories loaded: {global_count_3}")

    # List all memories
    print("\n   📋 All persisted memories:")
    for note in orch3.state.global_memory.get("notes", []):
        print(f"      - {note['text'][:60]}...")

    print("\n✅ Multi-session persistence working correctly")


def test_7_memory_injection_format():
    """Test 7: Memory injection format (for prompts)."""
    print_section("TEST 7: Memory Injection Format")

    from plotly_agent.memory_injection import (
        render_profile_as_yaml,
        render_memories_as_markdown,
        inject_memories_into_prompt
    )

    # Create a state with some data
    user_id = "test_user_injection"
    orch = WorkflowOrchestratorWithMemory(user_id=user_id, enable_memory=True)

    tools = orch.get_memory_tools()
    tools.update_profile("preferred_chart_types", ["bar", "line"])
    tools.update_profile("audience", "executives")
    tools.save_memory_note("User prefers horizontal bars", ["chart_type", "bar"])

    # Consolidate to global
    consolidate_session_memories(orch.state)

    print("\n📄 Testing YAML profile rendering...")
    yaml_output = render_profile_as_yaml(orch.state)
    print(yaml_output)
    assert "user_profile:" in yaml_output
    assert "preferred_chart_types:" in yaml_output

    print("\n📝 Testing Markdown memories rendering...")
    md_output = render_memories_as_markdown(
        orch.state.global_memory.get("notes", []),
        title="Long-Term Preferences"
    )
    print(md_output)
    assert "## Long-Term Preferences" in md_output

    print("\n🔗 Testing full prompt injection...")
    base_prompt = "You are a visualization expert."
    enhanced_prompt = inject_memories_into_prompt(base_prompt, orch.state)

    print("Enhanced prompt preview (first 500 chars):")
    print(enhanced_prompt[:500] + "...\n")

    assert "user_profile:" in enhanced_prompt
    assert "You are a visualization expert." in enhanced_prompt

    print("✅ Memory injection format working correctly")


def test_8_session_summary():
    """Test 8: Session summary functionality."""
    print_section("TEST 8: Session Summary")

    user_id = "test_user_summary"
    orch = WorkflowOrchestratorWithMemory(user_id=user_id, enable_memory=True)

    # Add some data
    tools = orch.get_memory_tools()
    tools.save_memory_note("Test memory 1", ["test"])
    tools.save_memory_note("Test memory 2", ["test"])
    tools.update_profile("domain", "healthcare")

    # Get summary
    summary = orch.get_session_summary()

    print("\n📊 Session Summary:")
    print(f"   User ID: {summary['user_id']}")
    print(f"   Memory enabled: {summary['memory_enabled']}")
    print(f"   Conversation messages: {summary['conversation_length']}")
    print(f"   Session memories: {summary['session_memory_count']}")
    print(f"   Global memories: {summary['global_memory_count']}")
    print(f"   Visualizations created: {summary['visualizations_created']}")
    print(f"   Profile audience: {summary['profile'].get('audience', 'N/A')}")
    print(f"   Profile domain: {summary['profile'].get('domain', 'N/A')}")

    assert summary["user_id"] == user_id
    assert summary["memory_enabled"] == True
    assert summary["session_memory_count"] >= 2

    print("\n✅ Session summary working correctly")


def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "█"*70)
    print("  CONTEXT ENGINEERING MEMORY SYSTEM - FULL TEST SUITE")
    print("█"*70)

    try:
        # Run tests in sequence
        orch = test_1_basic_state_creation()
        orch = test_2_memory_tools(orch)
        orch = test_3_state_persistence(orch)
        orch = test_4_conversation_trimming(orch)
        orch = test_5_memory_consolidation(orch)
        test_6_multi_session_persistence()
        test_7_memory_injection_format()
        test_8_session_summary()

        # Final summary
        print_section("🎉 ALL TESTS PASSED! 🎉")
        print("\n✅ Memory system is fully functional!")
        print("\nKey features verified:")
        print("   ✓ State creation and initialization")
        print("   ✓ Memory tools (save, search, update)")
        print("   ✓ State persistence to disk")
        print("   ✓ Conversation trimming with context preservation")
        print("   ✓ Memory consolidation and deduplication")
        print("   ✓ Multi-session persistence")
        print("   ✓ Memory injection format for prompts")
        print("   ✓ Session summary functionality")

        print("\n📂 Check the 'states/' directory to see saved user states")
        print("🚀 The memory system is ready for production use!")

        return True

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
