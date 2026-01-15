"""
Context Trimmer - Manage conversation length and context window

Implements conversation trimming to stay within context limits while preserving
important information in session memory for later reinjection.
"""

from typing import List, Dict, Any, Tuple
from .memory_manager import PlotlyAgentState, add_memory_note


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_MAX_TURNS = 10  # Keep last N conversation turns
MIN_TURNS_TO_KEEP = 3   # Always keep at least this many


# ============================================================================
# Conversation Trimming
# ============================================================================

def should_trim_conversation(
    conversation_history: List[Dict[str, str]],
    max_turns: int = DEFAULT_MAX_TURNS
) -> bool:
    """
    Check if conversation should be trimmed.

    Args:
        conversation_history: List of conversation messages
        max_turns: Maximum number of turns to keep

    Returns:
        True if trimming is needed
    """
    # Count user-assistant pairs
    user_messages = [m for m in conversation_history if m.get('role') == 'user']
    return len(user_messages) > max_turns


def trim_conversation(
    conversation_history: List[Dict[str, str]],
    state: PlotlyAgentState,
    max_turns: int = DEFAULT_MAX_TURNS,
    preserve_context: bool = True
) -> Tuple[List[Dict[str, str]], int]:
    """
    Trim conversation history while preserving key context.

    Args:
        conversation_history: Full conversation history
        state: Agent state (for storing preserved context)
        max_turns: Maximum number of user turns to keep
        preserve_context: If True, save trimmed context to session memory

    Returns:
        Tuple of (trimmed_history, number_of_messages_removed)
    """
    if not should_trim_conversation(conversation_history, max_turns):
        return conversation_history, 0

    # Separate user and assistant messages
    user_indices = [
        i for i, m in enumerate(conversation_history)
        if m.get('role') == 'user'
    ]

    if len(user_indices) <= max_turns:
        return conversation_history, 0

    # Find cutoff point (keep last max_turns user messages and their responses)
    cutoff_index = user_indices[-(max_turns)]

    # Messages to remove and messages to keep
    trimmed_messages = conversation_history[:cutoff_index]
    kept_messages = conversation_history[cutoff_index:]

    # Preserve key context from trimmed messages
    if preserve_context and trimmed_messages:
        context_summary = _extract_context_from_trimmed(trimmed_messages)
        if context_summary:
            add_memory_note(
                state,
                context_summary,
                keywords=["context", "conversation"],
                to_session=True
            )

        # Set flag to reinject session memories on next turn
        state.inject_session_memories_next_turn = True

    return kept_messages, len(trimmed_messages)


def _extract_context_from_trimmed(messages: List[Dict[str, str]]) -> str:
    """
    Extract key context from trimmed messages.

    Looks for:
    - Data uploads
    - Preferences stated
    - Chart types discussed
    - Important decisions

    Args:
        messages: Messages that will be trimmed

    Returns:
        Summary of key context
    """
    context_points = []

    for msg in messages:
        content = msg.get('content', '').lower()
        role = msg.get('role')

        # Look for data-related mentions
        if 'upload' in content or 'data' in content:
            if role == 'user':
                context_points.append("User uploaded/discussed data")

        # Look for preference statements
        if role == 'user' and ('prefer' in content or 'like' in content or 'want' in content):
            # Extract a short snippet
            snippet = msg.get('content', '')[:100]
            context_points.append(f"User stated: {snippet}...")

        # Look for chart type discussions
        chart_types = ['bar', 'line', 'scatter', 'pie', 'histogram']
        for chart_type in chart_types:
            if chart_type in content:
                context_points.append(f"Discussed {chart_type} charts")
                break

    if not context_points:
        return "Earlier conversation trimmed (no specific context preserved)"

    # Deduplicate and combine
    unique_points = list(dict.fromkeys(context_points))[:5]  # Max 5 points
    return "Earlier in conversation: " + "; ".join(unique_points)


# ============================================================================
# Token Estimation
# ============================================================================

def estimate_conversation_tokens(conversation_history: List[Dict[str, str]]) -> int:
    """
    Estimate token count for conversation history.

    Uses rough heuristic: ~4 characters = 1 token

    Args:
        conversation_history: List of messages

    Returns:
        Estimated token count
    """
    total_chars = sum(len(msg.get('content', '')) for msg in conversation_history)
    return total_chars // 4


def get_conversation_stats(conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Get statistics about the conversation.

    Args:
        conversation_history: List of messages

    Returns:
        Dictionary with conversation stats
    """
    user_count = sum(1 for m in conversation_history if m.get('role') == 'user')
    assistant_count = sum(1 for m in conversation_history if m.get('role') == 'assistant')
    system_count = sum(1 for m in conversation_history if m.get('role') == 'system')

    return {
        "total_messages": len(conversation_history),
        "user_messages": user_count,
        "assistant_messages": assistant_count,
        "system_messages": system_count,
        "estimated_tokens": estimate_conversation_tokens(conversation_history),
        "needs_trimming": should_trim_conversation(conversation_history)
    }


# ============================================================================
# Smart Trimming (Context-Aware)
# ============================================================================

def smart_trim_conversation(
    conversation_history: List[Dict[str, str]],
    state: PlotlyAgentState,
    target_tokens: int = 4000,
    preserve_recent: int = 3
) -> List[Dict[str, str]]:
    """
    Smart trimming that aims for a token target while preserving important messages.

    Args:
        conversation_history: Full conversation history
        state: Agent state
        target_tokens: Target token count
        preserve_recent: Always keep this many recent user-assistant pairs

    Returns:
        Trimmed conversation history
    """
    current_tokens = estimate_conversation_tokens(conversation_history)

    if current_tokens <= target_tokens:
        return conversation_history

    # Always preserve recent messages
    user_indices = [
        i for i, m in enumerate(conversation_history)
        if m.get('role') == 'user'
    ]

    if len(user_indices) <= preserve_recent:
        return conversation_history

    # Find where to cut
    preserve_from = user_indices[-(preserve_recent)]
    recent_messages = conversation_history[preserve_from:]

    # Calculate how much context we can keep from older messages
    recent_tokens = estimate_conversation_tokens(recent_messages)
    available_tokens = target_tokens - recent_tokens

    if available_tokens <= 0:
        # Recent messages alone exceed target, just keep them
        _preserve_trimmed_context(conversation_history[:preserve_from], state)
        state.inject_session_memories_next_turn = True
        return recent_messages

    # Include as many older messages as fit
    older_messages = conversation_history[:preserve_from]
    kept_older = []
    current_older_tokens = 0

    for msg in reversed(older_messages):
        msg_tokens = len(msg.get('content', '')) // 4
        if current_older_tokens + msg_tokens <= available_tokens:
            kept_older.insert(0, msg)
            current_older_tokens += msg_tokens
        else:
            break

    # Preserve context from messages we're removing
    removed = older_messages[:len(older_messages) - len(kept_older)]
    if removed:
        _preserve_trimmed_context(removed, state)
        state.inject_session_memories_next_turn = True

    return kept_older + recent_messages


def _preserve_trimmed_context(messages: List[Dict[str, str]], state: PlotlyAgentState) -> None:
    """Helper to preserve context from trimmed messages."""
    context = _extract_context_from_trimmed(messages)
    if context:
        add_memory_note(
            state,
            context,
            keywords=["context", "trimmed"],
            to_session=True
        )


# ============================================================================
# Conversation Management
# ============================================================================

class ConversationManager:
    """Manages conversation history with automatic trimming."""

    def __init__(
        self,
        state: PlotlyAgentState,
        max_turns: int = DEFAULT_MAX_TURNS,
        auto_trim: bool = True
    ):
        self.state = state
        self.max_turns = max_turns
        self.auto_trim = auto_trim

    def add_message(
        self,
        conversation_history: List[Dict[str, str]],
        role: str,
        content: str
    ) -> List[Dict[str, str]]:
        """
        Add a message to conversation history with automatic trimming.

        Args:
            conversation_history: Current conversation
            role: Message role (user/assistant/system)
            content: Message content

        Returns:
            Updated conversation history
        """
        # Add new message
        conversation_history.append({"role": role, "content": content})

        # Auto-trim if enabled
        if self.auto_trim and should_trim_conversation(conversation_history, self.max_turns):
            conversation_history, removed = trim_conversation(
                conversation_history,
                self.state,
                self.max_turns
            )

            if removed > 0:
                print(f"[ConversationManager] Trimmed {removed} messages, preserved context in session memory")

        return conversation_history

    def get_stats(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get conversation statistics."""
        return get_conversation_stats(conversation_history)

    def manual_trim(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Manually trigger trimming."""
        trimmed, removed = trim_conversation(
            conversation_history,
            self.state,
            self.max_turns
        )

        if removed > 0:
            print(f"[ConversationManager] Manual trim: removed {removed} messages")

        return trimmed
