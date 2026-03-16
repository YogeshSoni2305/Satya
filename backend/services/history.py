"""
HistoryService — per-user file-based verification history.

Uses fcntl file locking for multi-request safety.
Non-fatal: history failures don't crash the pipeline.
"""

import json
import fcntl
from pathlib import Path

from backend.utils.logger import logger
from backend.schemas.responses import HistoryEntry


class HistoryService:
    """Per-user verification history backed by JSON files."""

    def __init__(self, history_dir: Path) -> None:
        self._dir = history_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _user_file(self, user_id: str) -> Path:
        """Get history file path for a user (sanitized to prevent path traversal)."""
        safe_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
        return self._dir / f"{safe_id or 'anonymous'}.json"

    def save(self, user_id: str, entry: HistoryEntry) -> None:
        """Append a history entry to the user's file (thread-safe)."""
        filepath = self._user_file(user_id)

        try:
            with open(filepath, "a+", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    f.seek(0)
                    content = f.read().strip()
                    data = json.loads(content) if content else []
                    if not isinstance(data, list):
                        data = [data]

                    data.append(entry.model_dump())

                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, ensure_ascii=False, indent=2)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error("Failed to save history for user {}: {}", user_id, e)

    def get(self, user_id: str) -> list[HistoryEntry]:
        """Retrieve a user's verification history."""
        filepath = self._user_file(user_id)
        if not filepath.exists():
            return []

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            if not isinstance(data, list):
                data = [data]
            return [HistoryEntry(**item) for item in data]
        except Exception as e:
            logger.error("Failed to read history for user {}: {}", user_id, e)
            return []
