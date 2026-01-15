"""
Memory Consolidation - Deduplicate and merge memories

After each session, merge session memories into global memories while
deduplicating similar notes and maintaining quality.
"""

from typing import List, Dict, Any, Set
from datetime import datetime, timezone
from .memory_manager import MemoryNote, PlotlyAgentState, today_iso_utc


# ============================================================================
# Deduplication
# ============================================================================

def calculate_similarity(note1: MemoryNote, note2: MemoryNote) -> float:
    """
    Calculate similarity between two memory notes.

    Uses a simple keyword overlap heuristic. More sophisticated implementations
    could use embeddings or LLM-based comparison.

    Args:
        note1: First memory note
        note2: Second memory note

    Returns:
        Similarity score between 0 and 1
    """
    # Keyword overlap
    keywords1 = set(note1.keywords)
    keywords2 = set(note2.keywords)

    if not keywords1 or not keywords2:
        return 0.0

    overlap = len(keywords1 & keywords2)
    union = len(keywords1 | keywords2)

    keyword_similarity = overlap / union if union > 0 else 0.0

    # Text similarity (simple word overlap)
    words1 = set(note1.text.lower().split())
    words2 = set(note2.text.lower().split())

    text_overlap = len(words1 & words2)
    text_union = len(words1 | words2)

    text_similarity = text_overlap / text_union if text_union > 0 else 0.0

    # Combined score (weighted average)
    return 0.6 * keyword_similarity + 0.4 * text_similarity


def are_memories_similar(
    note1: MemoryNote,
    note2: MemoryNote,
    threshold: float = 0.6
) -> bool:
    """
    Check if two memories are similar enough to be considered duplicates.

    Args:
        note1: First memory note
        note2: Second memory note
        threshold: Similarity threshold (0.6 = 60% similar)

    Returns:
        True if memories are similar
    """
    similarity = calculate_similarity(note1, note2)
    return similarity >= threshold


def deduplicate_memories(notes: List[MemoryNote], threshold: float = 0.6) -> List[MemoryNote]:
    """
    Deduplicate a list of memory notes.

    Strategy:
    - Group similar memories
    - Keep the most recent version
    - Merge keywords from all versions

    Args:
        notes: List of memory notes
        threshold: Similarity threshold for considering duplicates

    Returns:
        Deduplicated list of memory notes
    """
    if not notes:
        return []

    # Sort by date (oldest first)
    sorted_notes = sorted(notes, key=lambda n: n.last_update_date)

    # Track which notes have been merged
    merged_indices: Set[int] = set()
    result: List[MemoryNote] = []

    for i, note in enumerate(sorted_notes):
        if i in merged_indices:
            continue

        # Find all similar notes
        similar_notes = [note]
        for j in range(i + 1, len(sorted_notes)):
            if j not in merged_indices:
                if are_memories_similar(note, sorted_notes[j], threshold):
                    similar_notes.append(sorted_notes[j])
                    merged_indices.add(j)

        # Merge similar notes
        if len(similar_notes) > 1:
            merged = _merge_similar_notes(similar_notes)
            result.append(merged)
        else:
            result.append(note)

    return result


def _merge_similar_notes(notes: List[MemoryNote]) -> MemoryNote:
    """
    Merge similar notes into one.

    Keeps:
    - Most recent text
    - Most recent date
    - Union of all keywords

    Args:
        notes: List of similar notes to merge

    Returns:
        Merged memory note
    """
    # Sort by date (most recent last)
    sorted_notes = sorted(notes, key=lambda n: n.last_update_date)

    # Use most recent text and date
    most_recent = sorted_notes[-1]

    # Merge keywords (unique)
    all_keywords = []
    for note in sorted_notes:
        all_keywords.extend(note.keywords)

    unique_keywords = list(dict.fromkeys(all_keywords))[:5]  # Max 5 keywords

    return MemoryNote(
        text=most_recent.text,
        last_update_date=most_recent.last_update_date,
        keywords=unique_keywords
    )


# ============================================================================
# Session Memory Consolidation
# ============================================================================

def consolidate_session_memories(state: PlotlyAgentState) -> Dict[str, Any]:
    """
    Merge session memories into global memories.

    This should be called at the end of a session.

    Process:
    1. Get all session memories
    2. Merge with global memories
    3. Deduplicate the combined list
    4. Update global memory
    5. Clear session memory

    Args:
        state: Current agent state

    Returns:
        Statistics about the consolidation
    """
    session_notes_dict = state.session_memory.get("notes", [])
    global_notes_dict = state.global_memory.get("notes", [])

    # Convert to MemoryNote objects
    session_notes = [MemoryNote.from_dict(n) for n in session_notes_dict]
    global_notes = [MemoryNote.from_dict(n) for n in global_notes_dict]

    # Count before consolidation
    before_count = len(global_notes) + len(session_notes)

    # Combine
    all_notes = global_notes + session_notes

    # Deduplicate
    deduplicated = deduplicate_memories(all_notes)

    # Update state
    state.global_memory["notes"] = [n.to_dict() for n in deduplicated]

    # Clear session memory
    state.session_memory = {"notes": []}

    # Statistics
    after_count = len(deduplicated)
    merged_count = before_count - after_count

    return {
        "before_count": before_count,
        "after_count": after_count,
        "merged_count": merged_count,
        "session_notes_added": len(session_notes)
    }


# ============================================================================
# Memory Quality
# ============================================================================

def assess_memory_quality(note: MemoryNote) -> Dict[str, Any]:
    """
    Assess the quality of a memory note.

    Checks:
    - Has keywords
    - Text is not too short or too long
    - Has recent update date
    - Keywords are relevant

    Args:
        note: Memory note to assess

    Returns:
        Quality assessment dictionary
    """
    issues = []
    score = 1.0

    # Check keywords
    if not note.keywords:
        issues.append("No keywords")
        score -= 0.3

    # Check text length
    text_len = len(note.text)
    if text_len < 10:
        issues.append("Text too short")
        score -= 0.3
    elif text_len > 500:
        issues.append("Text too long")
        score -= 0.2

    # Check date freshness (older than 1 year)
    try:
        note_date = datetime.fromisoformat(note.last_update_date)
        age_days = (datetime.now(timezone.utc) - note_date).days
        if age_days > 365:
            issues.append("Memory is old (>1 year)")
            score -= 0.1
    except:
        issues.append("Invalid date format")
        score -= 0.1

    # Check keyword relevance (very basic)
    text_lower = note.text.lower()
    relevant_keywords = [kw for kw in note.keywords if kw.lower() in text_lower]
    if relevant_keywords:
        relevance = len(relevant_keywords) / len(note.keywords)
        if relevance < 0.5:
            issues.append("Keywords not well matched to text")
            score -= 0.2

    return {
        "score": max(0.0, score),
        "issues": issues,
        "is_quality": score >= 0.7
    }


def filter_low_quality_memories(notes: List[MemoryNote], min_score: float = 0.5) -> List[MemoryNote]:
    """
    Filter out low-quality memories.

    Args:
        notes: List of memory notes
        min_score: Minimum quality score to keep

    Returns:
        Filtered list of quality memories
    """
    quality_notes = []

    for note in notes:
        assessment = assess_memory_quality(note)
        if assessment["score"] >= min_score:
            quality_notes.append(note)

    return quality_notes


# ============================================================================
# Memory Maintenance
# ============================================================================

def cleanup_old_memories(
    state: PlotlyAgentState,
    max_age_days: int = 365,
    max_memories: int = 50
) -> Dict[str, Any]:
    """
    Clean up old or excess memories.

    Args:
        state: Current agent state
        max_age_days: Remove memories older than this
        max_memories: Keep at most this many memories

    Returns:
        Cleanup statistics
    """
    notes_dict = state.global_memory.get("notes", [])
    notes = [MemoryNote.from_dict(n) for n in notes_dict]

    before_count = len(notes)

    # Filter by age
    current_date = datetime.now(timezone.utc)
    recent_notes = []

    for note in notes:
        try:
            note_date = datetime.fromisoformat(note.last_update_date)
            age_days = (current_date - note_date).days
            if age_days <= max_age_days:
                recent_notes.append(note)
        except:
            # Keep if date parsing fails
            recent_notes.append(note)

    # Keep only most recent if still too many
    if len(recent_notes) > max_memories:
        # Sort by date and keep most recent
        sorted_notes = sorted(recent_notes, key=lambda n: n.last_update_date, reverse=True)
        recent_notes = sorted_notes[:max_memories]

    # Update state
    state.global_memory["notes"] = [n.to_dict() for n in recent_notes]

    after_count = len(recent_notes)

    return {
        "before_count": before_count,
        "after_count": after_count,
        "removed_count": before_count - after_count
    }


def optimize_memories(state: PlotlyAgentState) -> Dict[str, Any]:
    """
    Run complete memory optimization.

    Steps:
    1. Deduplicate
    2. Filter low quality
    3. Clean up old memories
    4. Sort by date

    Args:
        state: Current agent state

    Returns:
        Optimization statistics
    """
    notes_dict = state.global_memory.get("notes", [])
    notes = [MemoryNote.from_dict(n) for n in notes_dict]

    before_count = len(notes)

    # Step 1: Deduplicate
    notes = deduplicate_memories(notes)
    after_dedup = len(notes)

    # Step 2: Filter low quality
    notes = filter_low_quality_memories(notes, min_score=0.5)
    after_quality = len(notes)

    # Step 3: Clean up old
    max_age = 365  # 1 year
    max_count = 50

    current_date = datetime.now(timezone.utc)
    recent_notes = []

    for note in notes:
        try:
            note_date = datetime.fromisoformat(note.last_update_date)
            age_days = (current_date - note_date).days
            if age_days <= max_age:
                recent_notes.append(note)
        except:
            recent_notes.append(note)

    if len(recent_notes) > max_count:
        sorted_notes = sorted(recent_notes, key=lambda n: n.last_update_date, reverse=True)
        recent_notes = sorted_notes[:max_count]

    # Step 4: Sort by date (most recent first)
    final_notes = sorted(recent_notes, key=lambda n: n.last_update_date, reverse=True)

    # Update state
    state.global_memory["notes"] = [n.to_dict() for n in final_notes]

    return {
        "before_count": before_count,
        "after_deduplication": after_dedup,
        "after_quality_filter": after_quality,
        "final_count": len(final_notes),
        "removed_total": before_count - len(final_notes)
    }
