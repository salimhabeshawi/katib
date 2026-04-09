"""Project and Markdown file management."""

from __future__ import annotations

from pathlib import Path


class ProjectManager:
    """Manage project folders and Markdown files."""

    def list_markdown_files(self, project_root: Path) -> list[Path]:
        """Return all Markdown files inside a project."""
        return sorted(
            (
                path
                for path in project_root.rglob("*.md")
                if path.is_file() and not self._is_hidden(path, project_root)
            ),
            key=lambda item: item.relative_to(project_root).as_posix().lower(),
        )

    def create_project(self, directory: Path) -> Path:
        """Create a project directory if it does not already exist."""
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def create_markdown_file(self, path: Path) -> Path:
        """Create a new Markdown file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return path

    def rename_file(self, source: Path, target: Path) -> Path:
        """Rename a Markdown file."""
        target.parent.mkdir(parents=True, exist_ok=True)
        return source.rename(target)

    def delete_file(self, path: Path) -> None:
        """Delete a Markdown file."""
        path.unlink(missing_ok=False)

    def read_file(self, path: Path) -> str:
        """Read the contents of a Markdown file."""
        return path.read_text(encoding="utf-8")

    def write_file(self, path: Path, content: str) -> None:
        """Write content to a Markdown file."""
        path.write_text(content, encoding="utf-8")

    def _is_hidden(self, path: Path, root: Path) -> bool:
        """Return whether any project-relative segment is hidden."""
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            return False
        return any(part.startswith(".") for part in parts)
