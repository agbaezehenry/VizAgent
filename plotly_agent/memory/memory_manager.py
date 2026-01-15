"""
Memory Manager - Core memory state and operations for context engineering

Based on OpenAI's Context Engineering for Personalization pattern.
Implements state-based long-term memory with profile, global memory, and session memory.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json


# ============================================================================
# Core Data Classes
# ============================================================================

@dataclass
class MemoryNote:
    """A single memory note capturing a user preference or context."""
    text: str
    last_update_date: str
    keywords: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'text': self.text,
            'last_update_date': self.last_update_date,
            'keywords': self.keywords
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryNote':
        """Create from dictionary."""
        return cls(
            text=data['text'],
            last_update_date=data['last_update_date'],
            keywords=data['keywords']
        )


@dataclass
class PlotlyAgentState:
    """
    Complete state for a user's Plotly agent session.

    Implements the state-based memory pattern with:
    - Structured profile (trusted, factual data)
    - Global memory (long-term, cross-session preferences)
    - Session memory (temporary, session-scoped context)
    - Visualization history (past charts created)
    """

    # User identification
    user_id: str = "anonymous"

    # Structured profile (from trusted sources)
    profile: Dict[str, Any] = field(default_factory=lambda: {
        "preferred_chart_types": [],  # ["bar", "line", "scatter"]
        "color_scheme": "default",  # "default", "professional", "colorblind"
        "audience": "general",  # "general", "executives", "technical"
        "domain": None,  # "finance", "healthcare", "marketing", etc.
        "technical_level": "intermediate",  # "beginner", "intermediate", "advanced"
    })

    # Long-term memories (persists across sessions)
    global_memory: Dict[str, Any] = field(default_factory=lambda: {"notes": []})

    # Session-scoped memories (merged after session)
    session_memory: Dict[str, Any] = field(default_factory=lambda: {"notes": []})

    # Visualization history
    visualization_history: List[Dict[str, Any]] = field(default_factory=list)

    # Rendered strings for injection (computed at runtime)
    system_frontmatter: str = ""
    global_memories_md: str = ""
    session_memories_md: str = ""

    # Control flags
    inject_session_memories_next_turn: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'profile': self.profile,
            'global_memory': self.global_memory,
            'session_memory': self.session_memory,
            'visualization_history': self.visualization_history,
            'inject_session_memories_next_turn': self.inject_session_memories_next_turn
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlotlyAgentState':
        """Create state from dictionary."""
        return cls(
            user_id=data.get('user_id', 'anonymous'),
            profile=data.get('profile', {}),
            global_memory=data.get('global_memory', {"notes": []}),
            session_memory=data.get('session_memory', {"notes": []}),
            visualization_history=data.get('visualization_history', []),
            inject_session_memories_next_turn=data.get('inject_session_memories_next_turn', False)
        )

    @classmethod
    def create_default(cls, user_id: str = "anonymous") -> 'PlotlyAgentState':
        """Create a default state for a new user."""
        return cls(user_id=user_id)


# ============================================================================
# Memory Operations
# ============================================================================

def today_iso_utc() -> str:
    """Get current date in ISO format (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def add_memory_note(
    state: PlotlyAgentState,
    text: str,
    keywords: List[str],
    to_session: bool = True
) -> MemoryNote:
    """
    Add a new memory note to the state.

    Args:
        state: Current agent state
        text: Memory text (preference, context, etc.)
        keywords: List of keywords for searching (max 5)
        to_session: If True, add to session memory; if False, add to global memory

    Returns:
        The created MemoryNote
    """
    # Normalize keywords
    clean_keywords = [k.strip().lower() for k in keywords if isinstance(k, str) and k.strip()][:5]

    # Create note
    note = MemoryNote(
        text=text.strip(),
        last_update_date=today_iso_utc(),
        keywords=clean_keywords
    )

    # Add to appropriate memory
    if to_session:
        if "notes" not in state.session_memory or state.session_memory["notes"] is None:
            state.session_memory["notes"] = []
        state.session_memory["notes"].append(note.to_dict())
    else:
        if "notes" not in state.global_memory or state.global_memory["notes"] is None:
            state.global_memory["notes"] = []
        state.global_memory["notes"].append(note.to_dict())

    return note


def search_memories(
    state: PlotlyAgentState,
    keywords: Optional[List[str]] = None,
    include_session: bool = True,
    include_global: bool = True
) -> List[MemoryNote]:
    """
    Search memories by keywords.

    Args:
        state: Current agent state
        keywords: Keywords to search for (searches all if None)
        include_session: Include session memories
        include_global: Include global memories

    Returns:
        List of matching MemoryNote objects
    """
    results = []

    # Normalize search keywords
    search_keywords = set(k.strip().lower() for k in (keywords or []))

    # Search global memory
    if include_global and "notes" in state.global_memory:
        for note_dict in state.global_memory["notes"]:
            note = MemoryNote.from_dict(note_dict)
            if not search_keywords or any(kw in search_keywords for kw in note.keywords):
                results.append(note)

    # Search session memory
    if include_session and "notes" in state.session_memory:
        for note_dict in state.session_memory["notes"]:
            note = MemoryNote.from_dict(note_dict)
            if not search_keywords or any(kw in search_keywords for kw in note.keywords):
                results.append(note)

    return results


def update_profile(
    state: PlotlyAgentState,
    field: str,
    value: Any
) -> bool:
    """
    Update a structured profile field.

    Args:
        state: Current agent state
        field: Profile field name
        value: New value

    Returns:
        True if update successful
    """
    if field in state.profile:
        state.profile[field] = value
        return True
    return False


def add_visualization_to_history(
    state: PlotlyAgentState,
    chart_type: str,
    story_summary: str,
    code_snippet: Optional[str] = None,
    success: bool = True
) -> None:
    """
    Add a visualization to the user's history.

    Args:
        state: Current agent state
        chart_type: Type of chart created
        story_summary: What the visualization showed
        code_snippet: Optional code snippet (first 200 chars)
        success: Whether the visualization was successful
    """
    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chart_type": chart_type,
        "story_summary": story_summary,
        "success": success
    }

    if code_snippet:
        history_entry["code_preview"] = code_snippet[:200]

    state.visualization_history.append(history_entry)

    # Keep only last 50 visualizations
    if len(state.visualization_history) > 50:
        state.visualization_history = state.visualization_history[-50:]


def get_recent_visualizations(
    state: PlotlyAgentState,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get recent visualizations from history.

    Args:
        state: Current agent state
        limit: Maximum number to return

    Returns:
        List of recent visualization entries
    """
    return state.visualization_history[-limit:] if state.visualization_history else []


def clear_session_memory(state: PlotlyAgentState) -> None:
    """Clear all session memories."""
    state.session_memory = {"notes": []}
    state.inject_session_memories_next_turn = False


def get_memory_summary(state: PlotlyAgentState) -> Dict[str, Any]:
    """
    Get a summary of the current memory state.

    Returns:
        Dictionary with memory statistics
    """
    global_notes = state.global_memory.get("notes", [])
    session_notes = state.session_memory.get("notes", [])

    return {
        "user_id": state.user_id,
        "global_memory_count": len(global_notes),
        "session_memory_count": len(session_notes),
        "visualization_count": len(state.visualization_history),
        "profile": state.profile,
        "recent_visualizations": get_recent_visualizations(state, limit=3)
    }


# ============================================================================
# Standard Keywords
# ============================================================================

STANDARD_KEYWORDS = {
    # Chart types
    "chart_type", "line", "bar", "scatter", "pie", "histogram", "box", "violin",

    # Design elements
    "color", "layout", "design", "legend", "label", "title", "axis",

    # Preferences
    "preference", "style", "theme", "formatting",

    # Audience
    "audience", "executives", "technical", "general",

    # Domain
    "domain", "finance", "healthcare", "marketing", "sales", "hr",

    # Data
    "data_format", "csv", "excel", "database",

    # Complexity
    "complexity", "simple", "advanced", "detailed"
}


def suggest_keywords(text: str) -> List[str]:
    """
    Suggest keywords based on memory text.

    Args:
        text: Memory note text

    Returns:
        List of suggested keywords
    """
    text_lower = text.lower()
    suggested = []

    for keyword in STANDARD_KEYWORDS:
        if keyword in text_lower:
            suggested.append(keyword)

    return suggested[:5]  # Max 5 keywords
