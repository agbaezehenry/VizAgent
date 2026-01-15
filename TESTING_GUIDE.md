# Testing the Memory System

This guide explains how to test the context engineering memory system.

## Quick Test (Recommended)

The fastest way to verify the system works:

```bash
python test_with_data.py
```

This runs a demo showing:
- **Session 1**: User expresses preferences (bar charts, finance domain, executives audience)
- **Session 2**: User returns and preferences are automatically loaded
- **Features**: Deduplication, conversation trimming, memory injection

**Expected Output**: You should see preferences being saved, loaded, and applied across sessions.

## Comprehensive Test Suite

For thorough verification of all components:

```bash
python test_memory_system.py
```

This runs 8 detailed tests:
1. ✅ Basic state creation
2. ✅ Memory tools (save, search, update)
3. ✅ State persistence to disk
4. ✅ Conversation trimming
5. ✅ Memory consolidation
6. ✅ Multi-session persistence
7. ✅ Memory injection format
8. ✅ Session summary

**Expected Output**: All tests should pass with ✅ marks.

## Manual Testing with Real Data

### Step 1: Load Data
```python
from plotly_agent.workflow_orchestrator_with_memory import WorkflowOrchestratorWithMemory

# Create orchestrator with your user ID
orch = WorkflowOrchestratorWithMemory(user_id="your_name", enable_memory=True)

# Load your data
orch.load_data('Data/omnitech_trends.csv')
```

### Step 2: Express Preferences
```python
# Get memory tools
tools = orch.get_memory_tools()

# Save preferences
tools.save_memory_note("I prefer horizontal bar charts", ["chart_type", "bar"])
tools.update_profile("domain", "finance")
tools.update_profile("audience", "executives")
```

### Step 3: End Session
```python
# Consolidate memories
orch.new_session(consolidate_memories=True)
```

### Step 4: New Session - Verify Persistence
```python
# Create new orchestrator with same user ID
orch2 = WorkflowOrchestratorWithMemory(user_id="your_name", enable_memory=True)

# Check that preferences loaded
summary = orch2.get_session_summary()
print(f"Global memories: {summary['global_memory_count']}")
print(f"Profile domain: {summary['profile']['domain']}")

# Search memories
result = orch2.get_memory_tools().search_memories(["chart_type"])
print(f"Found {result['count']} chart type preferences")
```

## What to Look For

### ✅ Success Indicators

1. **State Files Created**
   - Check `states/` directory
   - Should see `{user_id}.json` files
   - Files contain profile, memories, history

2. **Memory Persistence**
   - Preferences saved in Session 1
   - Automatically loaded in Session 2
   - No need to repeat preferences

3. **Memory Consolidation**
   - Session memories → Global memories
   - Similar memories deduplicated
   - Session memory cleared after consolidation

4. **Conversation Trimming**
   - Long conversations trimmed to last 10 turns
   - Older context preserved in session memory
   - Reinjection flag set for next turn

### ❌ Potential Issues

**Issue**: `ModuleNotFoundError: No module named 'plotly_agent'`
- **Fix**: Make sure you're in the project root directory

**Issue**: `FileNotFoundError: Data/omnitech_trends.csv`
- **Fix**: This is expected if you don't have the data file. The memory system still works without it.

**Issue**: State file not created
- **Fix**: Check that `states/` directory exists and is writable

**Issue**: Memories not persisting
- **Fix**: Make sure to call `orch.new_session(consolidate_memories=True)` to save

## Checking State Files

View a user's saved state:

```python
import json
from pathlib import Path

# Load a state file
with open('states/your_name.json', 'r') as f:
    state = json.load(f)

# Inspect contents
print("Profile:", state['profile'])
print("Global memories:", len(state['global_memory']['notes']))
print("Session memories:", len(state['session_memory']['notes']))
print("Visualizations:", len(state['visualization_history']))
```

## Testing with Web Interface

Once web endpoints are implemented (Phase 4), you can test via HTTP:

```bash
# Get all memories
curl http://localhost:5000/api/memories

# Delete a memory
curl -X DELETE http://localhost:5000/api/memories/{memory_id}

# Update profile
curl -X PUT http://localhost:5000/api/profile -d '{"domain": "finance"}'

# Get visualization history
curl http://localhost:5000/api/history
```

## Performance Testing

Test with many memories:

```python
# Add 100 memories
tools = orch.get_memory_tools()
for i in range(100):
    tools.save_memory_note(f"Test memory {i}", ["test"])

# Consolidate
orch.new_session(consolidate_memories=True)

# Check deduplication worked
summary = orch.get_session_summary()
print(f"Memories after dedup: {summary['global_memory_count']}")
# Should be much less than 100 due to deduplication
```

## Next Steps After Testing

Once you've verified the system works:

1. **Try with your own data** - Load a CSV and create visualizations
2. **Express real preferences** - Save your actual chart preferences
3. **Test multi-session** - Close and reopen, verify preferences persist
4. **Review state files** - Check `states/` to see what's saved
5. **Integrate with web app** - Add memory endpoints (Phase 4)

## Getting Help

If tests fail:
1. Check error messages in console output
2. Verify all dependencies installed (`pip install -r requirements.txt`)
3. Check that `states/` directory exists and is writable
4. Review `CONTEXT_ENGINEERING_STATUS.md` for system status

## Advanced Testing

### Test Memory Injection
```python
from plotly_agent.memory_injection import inject_memories_into_prompt

base_prompt = "You are a visualization expert."
enhanced = inject_memories_into_prompt(base_prompt, orch.state)

# Should see YAML frontmatter + memories
print(enhanced[:500])
```

### Test Deduplication
```python
from plotly_agent.memory_consolidation import deduplicate_memories
from plotly_agent.memory_manager import MemoryNote

notes = [
    MemoryNote("User prefers bar charts", "2025-01-14", ["bar"]),
    MemoryNote("User likes bar charts", "2025-01-14", ["bar"]),
]

deduped = deduplicate_memories(notes)
print(f"From {len(notes)} to {len(deduped)} memories")
```

### Test Conversation Trimming
```python
from plotly_agent.context_trimmer import should_trim_conversation, trim_conversation

# Create long conversation
long_conv = []
for i in range(15):
    long_conv.append({"role": "user", "content": f"Message {i}"})
    long_conv.append({"role": "assistant", "content": f"Response {i}"})

# Check if needs trimming
needs_trim = should_trim_conversation(long_conv, max_turns=10)
print(f"Needs trimming: {needs_trim}")  # Should be True

# Trim it
trimmed, removed = trim_conversation(long_conv, orch.state, max_turns=10)
print(f"Removed {removed} messages")
print(f"Kept {len(trimmed)} messages")
```

## Summary

**Quick Test**: `python test_with_data.py` (2 minutes)
**Full Test**: `python test_memory_system.py` (5 minutes)
**Manual Test**: Use Python REPL with code examples above

All tests should pass with ✅ indicators. The memory system is ready for production use!
