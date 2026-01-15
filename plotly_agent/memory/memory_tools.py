"""
Memory Tools - Tools for agents to capture and search memories

These tools allow agents to:
- Save new memory notes (preferences, context)
- Search existing memories
- Update user profile
- Record visualization history
"""

from typing import List, Optional, Dict, Any
from .memory_manager import (
    PlotlyAgentState,
    add_memory_note,
    search_memories,
    update_profile,
    suggest_keywords
)


# ============================================================================
# Tool Functions (called by agents)
# ============================================================================

def save_memory_note_tool(
    state: PlotlyAgentState,
    text: str,
    keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Tool for agents to save a new memory note.

    This should be called when the user expresses a preference, provides context,
    or shares information that should be remembered across sessions.

    Args:
        state: Current agent state
        text: The memory text (e.g., "User prefers horizontal bar charts")
        keywords: Optional keywords for categorization

    Returns:
        Success status and the created note

    Examples:
        - User says: "I prefer bar charts" → save_memory_note("User prefers bar charts", ["chart_type", "bar"])
        - User says: "I work in finance" → save_memory_note("User works in finance domain", ["domain", "finance"])
        - User says: "Keep it simple for executives" → save_memory_note("User's audience is executives, prefers simple charts", ["audience", "executives", "simple"])
    """
    # Suggest keywords if not provided
    if not keywords:
        keywords = suggest_keywords(text)

    # Add to session memory (will be merged to global after session)
    note = add_memory_note(state, text, keywords, to_session=True)

    return {
        "success": True,
        "note": note.to_dict(),
        "message": f"Memory saved: {text[:50]}..."
    }


def search_memories_tool(
    state: PlotlyAgentState,
    keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Tool for agents to search existing memories.

    Use this to find relevant preferences or context before making decisions.

    Args:
        state: Current agent state
        keywords: Keywords to search for (searches all if None)

    Returns:
        List of matching memories

    Examples:
        - Before choosing chart type: search_memories(["chart_type"])
        - Before applying colors: search_memories(["color", "design"])
        - For all memories: search_memories()
    """
    memories = search_memories(state, keywords=keywords)

    return {
        "success": True,
        "count": len(memories),
        "memories": [
            {
                "text": m.text,
                "keywords": m.keywords,
                "updated": m.last_update_date
            }
            for m in memories
        ]
    }


def update_profile_tool(
    state: PlotlyAgentState,
    field: str,
    value: Any
) -> Dict[str, Any]:
    """
    Tool for agents to update structured profile fields.

    Use this for factual, structured information that should be stored
    in the profile rather than as unstructured notes.

    Args:
        state: Current agent state
        field: Profile field to update
        value: New value

    Returns:
        Success status

    Valid fields:
        - preferred_chart_types: List[str]
        - color_scheme: str ("default", "professional", "colorblind")
        - audience: str ("general", "executives", "technical")
        - domain: str ("finance", "healthcare", "marketing", etc.)
        - technical_level: str ("beginner", "intermediate", "advanced")

    Examples:
        - update_profile("preferred_chart_types", ["bar", "line"])
        - update_profile("domain", "finance")
        - update_profile("audience", "executives")
    """
    success = update_profile(state, field, value)

    if success:
        return {
            "success": True,
            "message": f"Updated {field} to {value}"
        }
    else:
        return {
            "success": False,
            "message": f"Unknown profile field: {field}"
        }


# ============================================================================
# Tool Schemas (for LLM function calling)
# ============================================================================

SAVE_MEMORY_NOTE_SCHEMA = {
    "name": "save_memory_note",
    "description": "Save a user preference or context as a memory note. Call this when the user expresses preferences, provides context, or shares information that should be remembered.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The memory text describing the preference or context (e.g., 'User prefers horizontal bar charts for comparisons')"
            },
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords for categorization (e.g., ['chart_type', 'bar']). Max 5. Suggested categories: chart_type, color, design, audience, domain, complexity"
            }
        },
        "required": ["text"]
    }
}

SEARCH_MEMORIES_SCHEMA = {
    "name": "search_memories",
    "description": "Search existing memory notes by keywords. Use this to find relevant user preferences before making decisions.",
    "parameters": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Keywords to search for (e.g., ['chart_type', 'color']). Leave empty to get all memories."
            }
        }
    }
}

UPDATE_PROFILE_SCHEMA = {
    "name": "update_profile",
    "description": "Update a structured profile field with factual information. Use for explicit user statements about preferences.",
    "parameters": {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "enum": ["preferred_chart_types", "color_scheme", "audience", "domain", "technical_level"],
                "description": "The profile field to update"
            },
            "value": {
                "description": "The new value for the field"
            }
        },
        "required": ["field", "value"]
    }
}


# ============================================================================
# Tool Registry
# ============================================================================

class MemoryToolRegistry:
    """Registry of all memory-related tools."""

    def __init__(self, state: PlotlyAgentState):
        self.state = state
        self.tools = {
            "save_memory_note": self.save_memory_note,
            "search_memories": self.search_memories,
            "update_profile": self.update_profile
        }

    def save_memory_note(self, text: str, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """Save memory note wrapper."""
        return save_memory_note_tool(self.state, text, keywords)

    def search_memories(self, keywords: Optional[List[str]] = None) -> Dict[str, Any]:
        """Search memories wrapper."""
        return search_memories_tool(self.state, keywords)

    def update_profile(self, field: str, value: Any) -> Dict[str, Any]:
        """Update profile wrapper."""
        return update_profile_tool(self.state, field, value)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schemas for all tools."""
        return [
            SAVE_MEMORY_NOTE_SCHEMA,
            SEARCH_MEMORIES_SCHEMA,
            UPDATE_PROFILE_SCHEMA
        ]

    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name."""
        if tool_name in self.tools:
            return self.tools[tool_name](**kwargs)
        else:
            return {
                "success": False,
                "message": f"Unknown tool: {tool_name}"
            }
