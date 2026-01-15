"""
Memory and Context Management Module

This module provides long-term memory and context engineering capabilities
for the Plotly Agent, following OpenAI's state-based memory pattern.

Components:
- memory_manager: Core state classes and memory operations
- memory_tools: Tools for agents to capture/search memories
- memory_injection: Inject memories into prompts
- context_trimmer: Conversation trimming and context management
- memory_consolidation: Deduplication and memory optimization
"""

from .memory_manager import (
    MemoryNote,
    PlotlyAgentState,
    STANDARD_KEYWORDS,
    add_memory_note,
    search_memories,
    update_profile,
    add_visualization_to_history,
)

from .memory_tools import (
    MemoryToolRegistry,
)

from .memory_injection import (
    inject_memories_into_prompt,
    render_profile_as_yaml,
    render_memories_as_markdown,
)

from .context_trimmer import (
    ConversationManager,
    should_trim_conversation,
    trim_conversation,
)

from .memory_consolidation import (
    deduplicate_memories,
    consolidate_session_memories,
    assess_memory_quality,
)

__all__ = [
    # Core state
    "MemoryNote",
    "PlotlyAgentState",
    "STANDARD_KEYWORDS",
    "add_memory_note",
    "search_memories",
    "update_profile",
    "add_visualization_to_history",

    # Memory tools
    "MemoryToolRegistry",

    # Injection
    "inject_memories_into_prompt",
    "render_profile_as_yaml",
    "render_memories_as_markdown",

    # Context management
    "ConversationManager",
    "should_trim_conversation",
    "trim_conversation",

    # Consolidation
    "deduplicate_memories",
    "consolidate_session_memories",
    "assess_memory_quality",
]
