# Memory and Context Management Module

This folder contains all memory and context engineering components for the Plotly Agent.

## Architecture Overview

The memory system implements OpenAI's state-based memory pattern, providing long-term memory capabilities across user sessions.

## Module Files

### Core Memory Components

**memory_manager.py** (~350 lines)
- Core state classes: `MemoryNote`, `PlotlyAgentState`
- Memory operations: save, search, update
- Standard keywords and utilities
- State creation and manipulation functions

**memory_tools.py** (~280 lines)
- Tools for agents to capture/search memories
- OpenAI function calling schemas
- `MemoryToolRegistry` class for tool management
- Integration with workflow agents

**memory_injection.py** (~270 lines)
- Render memories as YAML + Markdown
- Inject into prompts with precedence rules
- Context reinjection after trimming
- Prompt enhancement functions

### Context Management

**context_trimmer.py** (~280 lines)
- Automatic conversation trimming
- Preserve context in session memory
- `ConversationManager` class
- Keep last N turns, save older context

**memory_consolidation.py** (~360 lines)
- Similarity-based deduplication
- Memory quality assessment
- Session → global memory merging
- Cleanup and optimization

## Memory Types

### 1. Structured Profile
Trusted, structured user preferences:
- User ID
- Preferred chart types
- Default color schemes
- Industry/domain
- Audience level

### 2. Global Memory
Long-term preferences across sessions:
- Chart type preferences
- Design preferences (colors, legends, layouts)
- Domain-specific requirements
- Audience considerations

### 3. Session Memory
Temporary session-scoped context:
- Current conversation context
- Temporary preferences for this session
- Trimmed conversation context for reinjection

### 4. Visualization History
Track past visualizations:
- Charts created
- Successful patterns
- User feedback

## Usage

### Basic Import
```python
from plotly_agent.memory import (
    PlotlyAgentState,
    MemoryToolRegistry,
    inject_memories_into_prompt,
    ConversationManager,
    deduplicate_memories
)
```

### Create State
```python
from plotly_agent.memory.memory_manager import create_default_state

state = create_default_state(user_id="john_doe")
```

### Use Memory Tools
```python
from plotly_agent.memory.memory_tools import MemoryToolRegistry

tools = MemoryToolRegistry(state)
tools.save_memory_note("User prefers bar charts", ["chart_type", "bar"])
results = tools.search_memories(["chart_type"])
```

### Inject Memories into Prompts
```python
from plotly_agent.memory.memory_injection import inject_memories_into_prompt

enhanced_prompt = inject_memories_into_prompt(base_prompt, state)
```

### Manage Conversations
```python
from plotly_agent.memory.context_trimmer import ConversationManager

manager = ConversationManager(state, max_turns=10)
trimmed = manager.manual_trim(conversation_history)
```

### Consolidate Memories
```python
from plotly_agent.memory.memory_consolidation import consolidate_session_to_global

stats = consolidate_session_to_global(state)
print(f"Merged {stats['merged_count']} duplicate memories")
```

## Memory Flow

```
User Message
    ↓
Check if trimming needed
    ├─ Yes → Trim + save to session memory
    └─ No → Continue
    ↓
Reinject session memories if needed
    ↓
Call Agent (with memory context injected)
    ↓
Agent can call memory tools:
    ├─ save_memory_note()
    ├─ search_memories()
    └─ update_profile()
    ↓
Generate response
    ↓
Save state to disk
    ↓
End of session: Consolidate session → global
```

## Precedence Rules

When memories conflict:
1. **Latest user message** (highest priority)
2. **Session memory** (current context)
3. **Global memory** (long-term preferences)
4. **Profile defaults** (lowest priority)

## Integration

The memory system integrates with:
- **workflow_orchestrator_with_memory.py** - Main orchestrator
- **state_storage.py** - Persistence layer (JSON files)
- **workflow_agents.py** - All agents receive memory context

## Standard Keywords

Common keywords for memory categorization:
- `chart_type` - Bar, line, scatter preferences
- `color` - Color scheme preferences
- `design` - Layout, legend, annotation preferences
- `audience` - Technical level, stakeholders
- `domain` - Industry, data domain
- `data_format` - Date formats, number formats

## Performance

- State load time: < 10ms
- State save time: < 20ms
- Memory search: < 5ms
- Deduplication: < 50ms for 100 memories
- Storage overhead: ~5-20 KB per user

## Testing

Test files using this module:
- `test_memory_system.py` - Comprehensive test suite
- `test_with_data.py` - Real-world demo

Run tests:
```bash
python test_memory_system.py
python test_with_data.py
```

## Related Documentation

- `../../MEMORY_SYSTEM_COMPLETE.md` - Complete system overview
- `../../CONTEXT_ENGINEERING_STATUS.md` - Implementation status
- `../../TESTING_GUIDE.md` - Testing instructions
- `../../MODEL_CONFIGURATION.md` - OpenAI model configuration
