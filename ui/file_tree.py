"""Markdown project file tree widget."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem


class FileTree(QTreeWidget):
    """Display Markdown files in a project tree."""

    file_open_requested = Signal(Path)
    file_context_requested = Signal(Path, QPoint)

    def __init__(self, parent: object | None = None) -> None:
        """Initialize the file tree."""
        super().__init__(parent)
        self.setHeaderHidden(True)
        # Keep file rows flush-left with no icon/branch gutter.
        self.setIndentation(0)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.itemActivated.connect(
            lambda item, _column: self._emit_file_requested(item)
        )
        self.itemClicked.connect(lambda item, _column: self._emit_file_requested(item))
        self.customContextMenuRequested.connect(self._emit_context_requested)

    def populate(self, project_root: Path, files: list[Path]) -> None:
        """Populate the tree from Markdown files."""
        self.clear()

        project_item = QTreeWidgetItem([project_root.name.upper()])
        project_item.setData(0, Qt.ItemDataRole.UserRole, None)
        project_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        project_font = project_item.font(0)
        project_font.setPointSize(project_font.pointSize() + 1)
        project_item.setFont(0, project_font)
        project_item.setForeground(0, QColor("#8f9aa7"))
        project_item.setChildIndicatorPolicy(
            QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
        )
        self.addTopLevelItem(project_item)

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

    def _emit_context_requested(self, pos: QPoint) -> None:
        """Emit a signal when a file item receives a context-menu click."""
        item = self.itemAt(pos)
        if item is None:
            return

        value = item.data(0, Qt.ItemDataRole.UserRole)
        if not value:
            return

        file_path = Path(value)
        if file_path.suffix.lower() != ".md":
            return

        self.setCurrentItem(item)
        self.file_context_requested.emit(file_path, self.viewport().mapToGlobal(pos))
