"""
State Storage - Persist agent state to disk

Saves and loads PlotlyAgentState to/from JSON files for long-term persistence.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from .memory.memory_manager import PlotlyAgentState


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_STATES_DIR = "states"


# ============================================================================
# Storage Operations
# ============================================================================

def get_states_directory(base_dir: Optional[str] = None) -> Path:
    """
    Get the states directory path.

    Args:
        base_dir: Optional base directory (defaults to ./states)

    Returns:
        Path to states directory
    """
    if base_dir:
        states_dir = Path(base_dir)
    else:
        states_dir = Path(DEFAULT_STATES_DIR)

    # Create if doesn't exist
    states_dir.mkdir(parents=True, exist_ok=True)

    return states_dir


def get_state_file_path(user_id: str, base_dir: Optional[str] = None) -> Path:
    """
    Get the file path for a user's state.

    Args:
        user_id: User identifier
        base_dir: Optional base directory

    Returns:
        Path to state file
    """
    states_dir = get_states_directory(base_dir)

    # Sanitize user_id for filename
    safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('_', '-'))
    filename = f"{safe_user_id}.json"

    return states_dir / filename


def save_state(
    state: PlotlyAgentState,
    base_dir: Optional[str] = None
) -> bool:
    """
    Save agent state to disk.

    Args:
        state: Agent state to save
        base_dir: Optional base directory

    Returns:
        True if save successful
    """
    try:
        file_path = get_state_file_path(state.user_id, base_dir)

        # Convert state to dictionary
        state_dict = state.to_dict()

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"Error saving state for user {state.user_id}: {e}")
        return False


def load_state(
    user_id: str,
    base_dir: Optional[str] = None,
    create_if_missing: bool = True
) -> Optional[PlotlyAgentState]:
    """
    Load agent state from disk.

    Args:
        user_id: User identifier
        base_dir: Optional base directory
        create_if_missing: If True, create default state if file doesn't exist

    Returns:
        PlotlyAgentState or None if load failed
    """
    try:
        file_path = get_state_file_path(user_id, base_dir)

        if not file_path.exists():
            if create_if_missing:
                # Create and save default state
                state = PlotlyAgentState.create_default(user_id)
                save_state(state, base_dir)
                return state
            else:
                return None

        # Read from file
        with open(file_path, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)

        # Convert to PlotlyAgentState
        state = PlotlyAgentState.from_dict(state_dict)

        return state

    except Exception as e:
        print(f"Error loading state for user {user_id}: {e}")
        if create_if_missing:
            return PlotlyAgentState.create_default(user_id)
        return None


def state_exists(user_id: str, base_dir: Optional[str] = None) -> bool:
    """
    Check if a state file exists for a user.

    Args:
        user_id: User identifier
        base_dir: Optional base directory

    Returns:
        True if state file exists
    """
    file_path = get_state_file_path(user_id, base_dir)
    return file_path.exists()


def delete_state(user_id: str, base_dir: Optional[str] = None) -> bool:
    """
    Delete a user's state file.

    Args:
        user_id: User identifier
        base_dir: Optional base directory

    Returns:
        True if deletion successful
    """
    try:
        file_path = get_state_file_path(user_id, base_dir)

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    except Exception as e:
        print(f"Error deleting state for user {user_id}: {e}")
        return False


def list_all_states(base_dir: Optional[str] = None) -> list[str]:
    """
    List all user IDs with saved states.

    Args:
        base_dir: Optional base directory

    Returns:
        List of user IDs
    """
    states_dir = get_states_directory(base_dir)

    user_ids = []
    for file_path in states_dir.glob("*.json"):
        # Extract user_id from filename (remove .json extension)
        user_id = file_path.stem
        user_ids.append(user_id)

    return sorted(user_ids)


# ============================================================================
# Backup and Export
# ============================================================================

def backup_state(
    user_id: str,
    base_dir: Optional[str] = None,
    backup_dir: Optional[str] = "states/backups"
) -> Optional[Path]:
    """
    Create a backup of a user's state.

    Args:
        user_id: User identifier
        base_dir: Optional base directory
        backup_dir: Directory for backups

    Returns:
        Path to backup file or None if failed
    """
    try:
        # Load current state
        state = load_state(user_id, base_dir, create_if_missing=False)
        if not state:
            return None

        # Create backup directory
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('_', '-'))
        backup_file = backup_path / f"{safe_user_id}_{timestamp}.json"

        # Save backup
        state_dict = state.to_dict()
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)

        return backup_file

    except Exception as e:
        print(f"Error creating backup for user {user_id}: {e}")
        return None


def export_state_for_user(
    user_id: str,
    export_path: str,
    base_dir: Optional[str] = None
) -> bool:
    """
    Export a user's state to a specific file.

    Useful for sharing states or migration.

    Args:
        user_id: User identifier
        export_path: Path to export file
        base_dir: Optional base directory

    Returns:
        True if export successful
    """
    try:
        state = load_state(user_id, base_dir, create_if_missing=False)
        if not state:
            return False

        # Ensure export directory exists
        export_file = Path(export_path)
        export_file.parent.mkdir(parents=True, exist_ok=True)

        # Save to export path
        state_dict = state.to_dict()
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"Error exporting state for user {user_id}: {e}")
        return False


def import_state_from_file(
    import_path: str,
    user_id: Optional[str] = None,
    base_dir: Optional[str] = None
) -> Optional[PlotlyAgentState]:
    """
    Import a state from a JSON file.

    Args:
        import_path: Path to import file
        user_id: Optional user ID (uses ID from file if not provided)
        base_dir: Optional base directory

    Returns:
        Imported PlotlyAgentState or None if failed
    """
    try:
        import_file = Path(import_path)
        if not import_file.exists():
            print(f"Import file not found: {import_path}")
            return None

        # Read state from file
        with open(import_file, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)

        # Override user_id if provided
        if user_id:
            state_dict['user_id'] = user_id

        # Convert to state object
        state = PlotlyAgentState.from_dict(state_dict)

        # Save to states directory
        save_state(state, base_dir)

        return state

    except Exception as e:
        print(f"Error importing state from {import_path}: {e}")
        return None


# ============================================================================
# Storage Manager
# ============================================================================

class StateStorageManager:
    """Manages state storage operations."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir

    def save(self, state: PlotlyAgentState) -> bool:
        """Save state."""
        return save_state(state, self.base_dir)

    def load(self, user_id: str, create_if_missing: bool = True) -> Optional[PlotlyAgentState]:
        """Load state."""
        return load_state(user_id, self.base_dir, create_if_missing)

    def exists(self, user_id: str) -> bool:
        """Check if state exists."""
        return state_exists(user_id, self.base_dir)

    def delete(self, user_id: str) -> bool:
        """Delete state."""
        return delete_state(user_id, self.base_dir)

    def list_users(self) -> list[str]:
        """List all user IDs."""
        return list_all_states(self.base_dir)

    def backup(self, user_id: str) -> Optional[Path]:
        """Create backup."""
        return backup_state(user_id, self.base_dir)

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information."""
        states_dir = get_states_directory(self.base_dir)
        user_count = len(self.list_users())

        # Calculate total size
        total_size = sum(
            f.stat().st_size
            for f in states_dir.glob("*.json")
        )

        return {
            "states_directory": str(states_dir.absolute()),
            "user_count": user_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
