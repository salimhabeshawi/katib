"""Markdown project file tree widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


class FileTree(QTreeWidget):
    """Display Markdown files in a project tree."""

    file_open_requested = Signal(Path)

    def __init__(self, parent: object | None = None) -> None:
        """Initialize the file tree."""
        super().__init__(parent)
        self.setHeaderHidden(True)
        # Keep file rows flush-left with no icon/branch gutter.
        self.setIndentation(0)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.itemActivated.connect(
            lambda item, _column: self._emit_file_requested(item)
        )
        self.itemClicked.connect(lambda item, _column: self._emit_file_requested(item))

    def populate(self, project_root: Path, files: list[Path]) -> None:
        """Populate the tree from Markdown files."""
        self.clear()
        for file_path in files:
            relative = file_path.relative_to(project_root)
            item = QTreeWidgetItem([relative.as_posix()])
            item.setData(0, Qt.ItemDataRole.UserRole, str(file_path))
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
            )
            self.addTopLevelItem(item)

    def select_file(self, file_path: Path) -> None:
        """Select the matching file in the tree."""
        matches = self.findItems(
            "*", Qt.MatchFlag.MatchWildcard | Qt.MatchFlag.MatchRecursive
        )
        for item in matches:
            value = item.data(0, Qt.ItemDataRole.UserRole)
            if value == str(file_path):
                self.setCurrentItem(item)
                break

    def _emit_file_requested(self, item: QTreeWidgetItem) -> None:
        """Emit a signal when a file item is activated."""
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if value and Path(value).suffix.lower() == ".md":
            self.file_open_requested.emit(Path(value))
