"""
Memory Injection - Inject memories into agent prompts

Renders user state (profile, memories, history) as YAML frontmatter and Markdown
for injection into system prompts following OpenAI's context engineering pattern.

Precedence rules:
- Latest user message > Session memory > Global memory > Profile defaults
"""

from typing import List, Dict, Any
import yaml
from .memory_manager import PlotlyAgentState, MemoryNote


# ============================================================================
# Rendering Functions
# ============================================================================

def render_profile_as_yaml(state: PlotlyAgentState) -> str:
    """
    Render user profile as YAML frontmatter.

    Args:
        state: Current agent state

    Returns:
        YAML string of profile data
    """
    profile_data = {
        "user_profile": {
            "user_id": state.user_id,
            **state.profile
        }
    }

    return yaml.dump(profile_data, default_flow_style=False, sort_keys=False)


def render_memories_as_markdown(
    memories: List[Dict[str, Any]],
    title: str = "Memories"
) -> str:
    """
    Render memory notes as Markdown bullet list.

    Args:
        memories: List of memory note dictionaries
        title: Section title

    Returns:
        Markdown formatted string
    """
    if not memories:
        return ""

    lines = [f"## {title}\n"]

    for note_dict in memories:
        text = note_dict.get("text", "")
        updated = note_dict.get("last_update_date", "")
        lines.append(f"- {text} (Updated: {updated})")

    return "\n".join(lines)


def render_visualization_history(state: PlotlyAgentState, limit: int = 5) -> str:
    """
    Render recent visualization history as Markdown.

    Args:
        state: Current agent state
        limit: Maximum number of visualizations to show

    Returns:
        Markdown formatted string
    """
    if not state.visualization_history:
        return ""

    recent = state.visualization_history[-limit:]
    lines = ["## Recent Visualizations\n"]

    for viz in recent:
        chart_type = viz.get("chart_type", "unknown")
        story = viz.get("story_summary", "")
        timestamp = viz.get("timestamp", "")
        success = viz.get("success", True)
        status = "✓" if success else "✗"

        lines.append(f"- {status} {chart_type.capitalize()}: {story[:60]}... ({timestamp[:10]})")

    return "\n".join(lines)


def inject_memories_into_prompt(
    base_prompt: str,
    state: PlotlyAgentState,
    include_frontmatter: bool = True,
    include_global: bool = True,
    include_session: bool = True,
    include_history: bool = True
) -> str:
    """
    Inject memories into a system prompt.

    Follows precedence rules:
    1. Latest user message (handled by conversation flow)
    2. Session memory (most recent context)
    3. Global memory (long-term preferences)
    4. Profile defaults

    Args:
        base_prompt: Original system prompt
        state: Current agent state
        include_frontmatter: Include YAML frontmatter with profile
        include_global: Include global memories
        include_session: Include session memories
        include_history: Include visualization history

    Returns:
        Enhanced prompt with memories injected
    """
    sections = []

    # YAML frontmatter with profile
    if include_frontmatter:
        yaml_str = render_profile_as_yaml(state)
        sections.append(f"---\n{yaml_str}---\n")

    # Global memories (long-term preferences)
    if include_global and state.global_memory.get("notes"):
        global_md = render_memories_as_markdown(
            state.global_memory["notes"],
            title="Long-Term Preferences"
        )
        sections.append(global_md)

    # Session memories (current context) - takes precedence
    if include_session and state.session_memory.get("notes"):
        session_md = render_memories_as_markdown(
            state.session_memory["notes"],
            title="Current Session Context"
        )
        sections.append(session_md)

    # Visualization history
    if include_history:
        history_md = render_visualization_history(state)
        if history_md:
            sections.append(history_md)

    # Add usage instructions
    if sections:
        sections.append(_get_memory_usage_instructions())

    # Combine with base prompt
    memory_context = "\n\n".join(sections)
    enhanced_prompt = f"{memory_context}\n\n{base_prompt}"

    return enhanced_prompt


def _get_memory_usage_instructions() -> str:
    """Get instructions for how agents should use memories."""
    return """## Using Memories

### How to Apply Memories

1. **Check Profile First**
   - Review user_profile for preferred_chart_types, audience, domain
   - These are factual preferences that should be respected

2. **Apply Long-Term Preferences**
   - Review Long-Term Preferences for visualization patterns
   - These are established preferences from past sessions

3. **Prioritize Session Context**
   - Current Session Context takes precedence over long-term preferences
   - These reflect what the user wants right now

4. **When Preferences Conflict**
   - Latest explicit user statement wins
   - Session context > Global memory > Profile defaults
   - Ask clarifying questions if unclear

5. **When to Capture New Memories**
   - User explicitly states a preference ("I prefer X")
   - User corrects something ("Actually, use Y instead")
   - User provides context ("I work in finance")
   - Pattern emerges (user always chooses bar charts)

### Memory Keywords

Use these standard keywords when saving memories:
- **Chart types**: chart_type, line, bar, scatter, pie
- **Design**: color, layout, design, legend, label, title
- **Audience**: audience, executives, technical, general
- **Domain**: domain, finance, healthcare, marketing, sales
- **Preferences**: preference, style, theme, complexity"""


# ============================================================================
# Context Window Management
# ============================================================================

def should_reinject_session_memories(state: PlotlyAgentState) -> bool:
    """
    Check if session memories should be reinjected.

    Returns True if:
    - inject_session_memories_next_turn flag is set
    - This happens after conversation trimming
    """
    return state.inject_session_memories_next_turn


def create_reinjection_message(state: PlotlyAgentState) -> str:
    """
    Create a system message to reinject session memories after trimming.

    Args:
        state: Current agent state

    Returns:
        System message with session memories
    """
    session_md = render_memories_as_markdown(
        state.session_memory.get("notes", []),
        title="Session Context (Reinjected)"
    )

    message = f"""# Context Reinjection

The conversation was trimmed to manage context length. Here are the key points from earlier in this session:

{session_md}

Continue the conversation with this context in mind."""

    # Clear the flag
    state.inject_session_memories_next_turn = False

    return message


# ============================================================================
# Utility Functions
# ============================================================================

def estimate_token_count(text: str) -> int:
    """
    Rough estimate of token count.
    Actual tokenization depends on the model, but ~4 chars = 1 token.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4


def get_memory_context_size(state: PlotlyAgentState) -> Dict[str, int]:
    """
    Estimate token sizes of memory components.

    Args:
        state: Current agent state

    Returns:
        Dictionary with size estimates
    """
    profile_yaml = render_profile_as_yaml(state)
    global_md = render_memories_as_markdown(state.global_memory.get("notes", []))
    session_md = render_memories_as_markdown(state.session_memory.get("notes", []))
    history_md = render_visualization_history(state)

    return {
        "profile_tokens": estimate_token_count(profile_yaml),
        "global_memory_tokens": estimate_token_count(global_md),
        "session_memory_tokens": estimate_token_count(session_md),
        "history_tokens": estimate_token_count(history_md),
        "total_tokens": estimate_token_count(
            profile_yaml + global_md + session_md + history_md
        )
    }


def trim_memories_if_needed(
    state: PlotlyAgentState,
    max_global: int = 20,
    max_session: int = 10
) -> None:
    """
    Trim memories if they exceed limits.

    Args:
        state: Current agent state
        max_global: Maximum global memory notes
        max_session: Maximum session memory notes
    """
    # Trim global memories (keep most recent)
    if "notes" in state.global_memory:
        notes = state.global_memory["notes"]
        if len(notes) > max_global:
            state.global_memory["notes"] = notes[-max_global:]

    # Trim session memories (keep most recent)
    if "notes" in state.session_memory:
        notes = state.session_memory["notes"]
        if len(notes) > max_session:
            state.session_memory["notes"] = notes[-max_session:]
