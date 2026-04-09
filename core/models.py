"""Data models used by the Katib application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppState:
    """Persistent application state."""

    last_project: str | None = None
    last_file: str | None = None
    sidebar_visible: bool = True
    preview_visible: bool = False
    global_direction: str = "rtl"


@dataclass(slots=True)
class ProjectContext:
    """Represents the currently opened project."""

    root: Path

    def relative_path(self, file_path: Path) -> str:
        """Return a portable relative path inside the project."""
        return file_path.relative_to(self.root).as_posix()
