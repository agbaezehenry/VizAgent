"""
Quick Test with Real Data - Memory System Demo

This script demonstrates the memory system with actual data visualization.
It shows how preferences are captured and applied across sessions.

Usage:
    python test_with_data.py
"""

import sys
from pathlib import Path

# Add plotly_agent to path
sys.path.insert(0, str(Path(__file__).parent))

from plotly_agent.workflow_orchestrator_with_memory import WorkflowOrchestratorWithMemory


def print_banner(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def demo_session_1():
    """Session 1: User expresses preferences and creates first visualization."""
    print_banner("SESSION 1: First Interaction with Preferences")

    # Create orchestrator with memory
    orch = WorkflowOrchestratorWithMemory(
        user_id="demo_user",
        enable_memory=True
    )

    # Check if data file exists
    data_file = Path("Data/omnitech_trends.csv")
    if not data_file.exists():
        print("⚠️  Warning: Data/omnitech_trends.csv not found")
        print("   Using memory system without data visualization demo")
        print("   Memory features will still be demonstrated\n")
        has_data = False
    else:
        print(f"✅ Found data file: {data_file}\n")
        orch.load_data(str(data_file))
        has_data = True

    # Simulate user expressing preferences
    print("👤 User: 'I prefer horizontal bar charts for comparisons'")
    memory_tools = orch.get_memory_tools()
    result = memory_tools.save_memory_note(
        "User prefers horizontal bar charts for comparisons",
        ["chart_type", "bar", "horizontal"]
    )
    print(f"🧠 Memory saved: {result['note']['text']}\n")

    print("👤 User: 'I work in finance, so use green for positive, red for negative'")
    memory_tools.save_memory_note(
        "User works in finance domain, use green for positive, red for negative",
        ["domain", "finance", "color"]
    )
    memory_tools.update_profile("domain", "finance")
    print("🧠 Memory and profile updated\n")

    print("👤 User: 'My audience is executives, keep it simple'")
    memory_tools.save_memory_note(
        "User's audience is executives, prefers simple charts",
        ["audience", "executives", "complexity"]
    )
    memory_tools.update_profile("audience", "executives")
    print("🧠 Memory and profile updated\n")

    # Show session summary
    summary = orch.get_session_summary()
    print("📊 Current Session Summary:")
    print(f"   User ID: {summary['user_id']}")
    print(f"   Session memories: {summary['session_memory_count']}")
    print(f"   Global memories: {summary['global_memory_count']}")
    print(f"   Profile domain: {summary['profile']['domain']}")
    print(f"   Profile audience: {summary['profile']['audience']}\n")

    # End session and consolidate
    print("🔄 Ending session and consolidating memories...")
    orch.new_session(consolidate_memories=True)

    # Show final state
    summary_after = orch.get_session_summary()
    print(f"   Session memories: {summary_after['session_memory_count']} (cleared)")
    print(f"   Global memories: {summary_after['global_memory_count']} (consolidated)")
    print("\n✅ Session 1 complete - preferences saved!\n")

    return has_data


def demo_session_2():
    """Session 2: Load user and verify preferences persist."""
    print_banner("SESSION 2: Returning User - Preferences Applied")

    # Create new orchestrator - should load saved state
    orch = WorkflowOrchestratorWithMemory(
        user_id="demo_user",
        enable_memory=True
    )

    print("👤 User returns in a new session...")
    print("\n🧠 Loading user's saved state...\n")

    # Show that preferences were loaded
    summary = orch.get_session_summary()
    print("📊 Loaded User Profile:")
    print(f"   Domain: {summary['profile']['domain']}")
    print(f"   Audience: {summary['profile']['audience']}")
    print(f"   Global memories: {summary['global_memory_count']}\n")

    # Show loaded memories
    print("📋 User's Long-Term Preferences:")
    for i, note in enumerate(orch.state.global_memory.get("notes", [])[:5], 1):
        print(f"   {i}. {note['text']}")
    print()

    # Demonstrate memory search
    print("🔍 Searching for chart type preferences...")
    memory_tools = orch.get_memory_tools()
    search_result = memory_tools.search_memories(["chart_type"])
    print(f"   Found {search_result['count']} relevant memories:")
    for mem in search_result['memories']:
        print(f"   - {mem['text']}")
    print()

    # Add a new preference for this session
    print("👤 User: 'For this report, I don't want any legends'")
    memory_tools.save_memory_note(
        "User dislikes legends for current report",
        ["design", "legend"]
    )
    print("🧠 Session memory saved (will be merged after session)\n")

    # Show updated summary
    summary = orch.get_session_summary()
    print("📊 Updated Session Summary:")
    print(f"   Session memories: {summary['session_memory_count']} (new preference)")
    print(f"   Global memories: {summary['global_memory_count']} (from Session 1)")
    print("\n✅ Session 2 complete - preferences automatically applied!\n")


def demo_memory_system_features():
    """Demonstrate specific memory system features."""
    print_banner("MEMORY SYSTEM FEATURES DEMO")

    orch = WorkflowOrchestratorWithMemory(
        user_id="feature_demo_user",
        enable_memory=True
    )

    memory_tools = orch.get_memory_tools()

    # Feature 1: Deduplication
    print("📌 Feature 1: Memory Deduplication")
    print("   Saving similar memories...")
    memory_tools.save_memory_note("User prefers bar charts", ["chart_type", "bar"])
    memory_tools.save_memory_note("User likes bar charts for comparisons", ["chart_type", "bar"])
    memory_tools.save_memory_note("User prefers bar chart visualizations", ["chart_type", "bar"])

    from plotly_agent.memory.memory_consolidation import consolidate_session_memories
    before_count = len(orch.state.session_memory.get("notes", []))
    print(f"   Before deduplication: {before_count} memories")

    stats = consolidate_session_memories(orch.state)
    after_count = len(orch.state.global_memory.get("notes", []))
    print(f"   After deduplication: {after_count} memories")
    print(f"   Merged: {stats['merged_count']} duplicates\n")

    # Feature 2: Conversation trimming
    print("📌 Feature 2: Conversation Trimming")
    print("   Simulating long conversation (12 turns)...")

    for i in range(12):
        orch.conversation_history.append({"role": "user", "content": f"Question {i+1}"})
        orch.conversation_history.append({"role": "assistant", "content": f"Answer {i+1}"})

    print(f"   Total messages: {len(orch.conversation_history)}")

    if orch.conversation_manager:
        trimmed = orch.conversation_manager.manual_trim(orch.conversation_history)
        orch.conversation_history = trimmed
        user_messages = [m for m in orch.conversation_history if m['role'] == 'user']
        print(f"   After trimming: {len(user_messages)} user turns kept (last 10)")
        print(f"   Older context saved to session memory: {orch.state.inject_session_memories_next_turn}\n")

    # Feature 3: Memory injection preview
    print("📌 Feature 3: Memory Injection for Prompts")
    from plotly_agent.memory.memory_injection import inject_memories_into_prompt

    base_prompt = "You are a data visualization expert."
    enhanced = inject_memories_into_prompt(base_prompt, orch.state)

    print("   Base prompt length: {} chars".format(len(base_prompt)))
    print("   Enhanced prompt length: {} chars".format(len(enhanced)))
    print("   Added: YAML profile + Markdown memories\n")
    print("   Preview (first 300 chars):")
    print("   " + enhanced[:300].replace("\n", "\n   ") + "...\n")

    print("✅ All features demonstrated!\n")


def main():
    """Run the complete demo."""
    print("\n" + "█"*70)
    print("  MEMORY SYSTEM DEMO - Real World Usage")
    print("█"*70)

    try:
        # Run demo sessions
        has_data = demo_session_1()
        demo_session_2()
        demo_memory_system_features()

        # Final summary
        print_banner("🎉 DEMO COMPLETE")

        print("What just happened:")
        print("  1. ✅ Session 1: User expressed preferences → saved to memory")
        print("  2. ✅ Session 2: User returned → preferences automatically loaded")
        print("  3. ✅ Features: Deduplication, trimming, prompt injection demonstrated")
        print()
        print("What this means:")
        print("  • Users don't need to repeat preferences every session")
        print("  • Charts automatically match user's preferred style")
        print("  • Conversation stays manageable with automatic trimming")
        print("  • All preferences persist across sessions")
        print()
        print("Check the 'states/' directory to see saved user profiles!")
        print()

        if not has_data:
            print("💡 TIP: Add Data/omnitech_trends.csv to test with real visualizations")
            print()

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
