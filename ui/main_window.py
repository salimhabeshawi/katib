"""Main window for the Katib application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.models import AppState, ProjectContext
from core.project_manager import ProjectManager
from services.markdown_service import MarkdownService
from services.settings_service import SettingsService
from ui.editor import MarkdownEditor
from ui.file_tree import FileTree
from ui.preview import PreviewBrowser


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self, settings_service: SettingsService, parent: object | None = None) -> None:
        """Initialize the main window and restore state."""
        super().__init__(parent)
        self._settings_service = settings_service
        self._state = self._settings_service.load_state()
        self._document_directions = self._settings_service.load_document_directions()
        self._project_manager = ProjectManager()
        self._markdown_service = MarkdownService()

        self._project: ProjectContext | None = None
        self._current_file: Path | None = None
        self._is_loading_file = False

        self._save_timer = QTimer(self)
        self._save_timer.setInterval(350)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_file)

        self._file_tree = FileTree()
        self._file_tree.setMinimumWidth(220)
        self._file_tree.file_open_requested.connect(self.open_file)

        self._editor = MarkdownEditor()
        self._editor.textChanged.connect(self._on_editor_text_changed)
        self._editor_page = self._build_centered_page(self._editor)

        self._preview = PreviewBrowser()
        self._preview_page = self._build_centered_page(self._preview)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._editor_page)
        self._stack.addWidget(self._preview_page)

        self._direction_button = QPushButton()
        self._direction_button.setObjectName("directionToggle")
        self._direction_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._direction_button.clicked.connect(self.toggle_direction)

        self._content_panel = QWidget()
        self._content_layout = QVBoxLayout(self._content_panel)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)

        self._top_bar = QWidget()
        self._top_bar_layout = QHBoxLayout(self._top_bar)
        self._top_bar_layout.setContentsMargins(20, 14, 20, 0)
        self._top_bar_layout.setSpacing(0)
        self._top_bar_layout.addStretch(1)
        self._top_bar_layout.addWidget(self._direction_button)

        self._content_layout.addWidget(self._top_bar)
        self._content_layout.addWidget(self._stack, 1)

        self._splitter = QSplitter()
        self._splitter.addWidget(self._file_tree)
        self._splitter.addWidget(self._content_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setCollapsible(0, True)
        self._splitter.setChildrenCollapsible(False)

        self.setCentralWidget(self._splitter)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")
        self.resize(1180, 780)
        self.setWindowTitle("Katib")

        self._create_actions()
        self._restore_session()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist state when the window closes."""
        self._save_current_file()
        self._persist_state()
        super().closeEvent(event)

    def open_project(self) -> None:
        """Open an existing project folder."""
        directory = QFileDialog.getExistingDirectory(self, "Open Project")
        if not directory:
            return
        self._load_project(Path(directory))

    def create_project(self) -> None:
        """Create and open a new project folder."""
        directory = QFileDialog.getExistingDirectory(self, "Create Project")
        if not directory:
            return
        project_root = self._project_manager.create_project(Path(directory))
        self._load_project(project_root)

    def create_file(self) -> None:
        """Create a new Markdown file in the current project."""
        if not self._require_project():
            return

        file_name, accepted = QInputDialog.getText(
            self,
            "New Markdown File",
            "File name:",
            text="untitled.md",
        )
        if not accepted or not file_name.strip():
            return

        safe_name = file_name.strip()
        if not safe_name.endswith(".md"):
            safe_name += ".md"

        target = self._project.root / safe_name
        if target.exists():
            self._show_error("A file with that name already exists.")
            return

        self._project_manager.create_markdown_file(target)
        self._refresh_tree(select_path=target)
        self.open_file(target)

    def rename_current_file(self) -> None:
        """Rename the currently opened Markdown file."""
        if not self._current_file or not self._project:
            return

        relative_name = self._project.relative_path(self._current_file)
        new_name, accepted = QInputDialog.getText(
            self,
            "Rename File",
            "File name:",
            text=relative_name,
        )
        if not accepted or not new_name.strip():
            return

        candidate = self._project.root / new_name.strip()
        if candidate.suffix.lower() != ".md":
            candidate = candidate.with_suffix(".md")
        if candidate.exists():
            self._show_error("A file with that name already exists.")
            return

        old_relative = self._project.relative_path(self._current_file)
        new_path = self._project_manager.rename_file(self._current_file, candidate)
        self._current_file = new_path
        if old_relative in self._document_directions:
            self._document_directions[self._project.relative_path(new_path)] = self._document_directions.pop(
                old_relative
            )
        self._refresh_tree(select_path=new_path)
        self._persist_state()

    def delete_current_file(self) -> None:
        """Delete the currently opened Markdown file."""
        if not self._current_file:
            return

        answer = QMessageBox.question(
            self,
            "Delete File",
            f"Delete {self._current_file.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        path_to_delete = self._current_file
        self._project_manager.delete_file(path_to_delete)
        self._current_file = None
        self._editor.clear()
        self._preview.clear()
        if self._project:
            relative_key = self._project.relative_path(path_to_delete)
            self._document_directions.pop(relative_key, None)
        self._refresh_tree()
        self._persist_state()

    def open_file(self, file_path: Path) -> None:
        """Open a Markdown file in the editor."""
        if not file_path.exists():
            return

        self._save_current_file()
        self._is_loading_file = True
        self._current_file = file_path
        content = self._project_manager.read_file(file_path)

        with QSignalBlocker(self._editor):
            self._editor.setPlainText(content)

        self._is_loading_file = False
        self._apply_direction(self._document_direction(file_path))
        self._file_tree.select_file(file_path)
        self._update_preview()
        self._update_status()
        self._update_direction_button()
        self._persist_state()

    def toggle_preview(self) -> None:
        """Toggle between edit and preview modes."""
        showing_preview = self._stack.currentWidget() is self._preview_page
        self._stack.setCurrentWidget(self._editor_page if showing_preview else self._preview_page)
        self._state.preview_visible = not showing_preview
        if not showing_preview:
            self._update_preview()
        self._update_status()

    def toggle_sidebar(self) -> None:
        """Toggle the sidebar visibility."""
        is_hidden = self._file_tree.isHidden()
        self._file_tree.setVisible(is_hidden)
        self._state.sidebar_visible = is_hidden

    def set_document_direction(self, direction: str) -> None:
        """Set the text direction for the current document."""
        if not self._project or not self._current_file:
            return
        key = self._project.relative_path(self._current_file)
        self._document_directions[key] = "rtl" if direction == "rtl" else "ltr"
        self._apply_direction(self._document_directions[key])
        self._update_preview()
        self._persist_state()

    def set_global_direction(self, direction: str) -> None:
        """Set the default direction for new documents."""
        self._state.global_direction = "rtl" if direction == "rtl" else "ltr"
        if self._project and self._current_file:
            self._apply_direction(self._document_direction(self._current_file))
            self._update_preview()
        else:
            self._update_direction_button()
        self._persist_state()

    def toggle_direction(self) -> None:
        """Toggle RTL/LTR for the current document or global default."""
        current_direction = (
            self._document_direction(self._current_file)
            if self._project and self._current_file
            else self._state.global_direction
        )
        next_direction = "ltr" if current_direction == "rtl" else "rtl"
        if self._project and self._current_file:
            self.set_document_direction(next_direction)
            return
        self.set_global_direction(next_direction)

    def _create_actions(self) -> None:
        """Create actions, menus, and shortcuts."""
        open_project_action = QAction("Open Project", self)
        open_project_action.setShortcut(QKeySequence.StandardKey.Open)
        open_project_action.triggered.connect(self.open_project)

        new_project_action = QAction("New Project", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        new_project_action.triggered.connect(self.create_project)

        new_file_action = QAction("New File", self)
        new_file_action.setShortcut(QKeySequence.New)
        new_file_action.triggered.connect(self.create_file)

        rename_file_action = QAction("Rename File", self)
        rename_file_action.setShortcut(QKeySequence("F2"))
        rename_file_action.triggered.connect(self.rename_current_file)

        delete_file_action = QAction("Delete File", self)
        delete_file_action.setShortcut(QKeySequence.Delete)
        delete_file_action.triggered.connect(self.delete_current_file)

        preview_action = QAction("Toggle Preview", self)
        preview_action.setShortcut(QKeySequence("Ctrl+P"))
        preview_action.triggered.connect(self.toggle_preview)

        sidebar_action = QAction("Toggle Sidebar", self)
        sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        sidebar_action.triggered.connect(self.toggle_sidebar)

        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(new_project_action)
        file_menu.addAction(open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(new_file_action)
        file_menu.addAction(rename_file_action)
        file_menu.addAction(delete_file_action)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction(preview_action)
        view_menu.addAction(sidebar_action)

        for action in [
            open_project_action,
            new_project_action,
            new_file_action,
            rename_file_action,
            delete_file_action,
            preview_action,
            sidebar_action,
        ]:
            self.addAction(action)

    def _restore_session(self) -> None:
        """Restore the last project and file if they still exist."""
        self._file_tree.setVisible(self._state.sidebar_visible)
        self._stack.setCurrentWidget(
            self._preview_page if self._state.preview_visible else self._editor_page
        )
        self._update_direction_button()

        if not self._state.last_project:
            return

        project_path = self._normalize_path(Path(self._state.last_project))
        if not project_path.is_dir():
            return

        try:
            self._load_project(project_path, restore_file=True)
        except OSError:
            self._project = None
            self._current_file = None
            self._file_tree.clear()
            self._editor.clear()
            self._preview.clear()
            self.statusBar().showMessage("Ready")

    def _load_project(self, project_root: Path, restore_file: bool = False) -> None:
        """Load a project into the UI."""
        normalized_root = self._normalize_path(project_root)
        self._project = ProjectContext(root=normalized_root)
        self._refresh_tree()
        self.setWindowTitle(f"Katib  |  {normalized_root.name}")
        self.statusBar().showMessage(f"Project: {normalized_root}")
        self._state.last_project = str(normalized_root)

        if restore_file and self._state.last_file:
            candidate = self._normalize_path(Path(self._state.last_file))
            if candidate.exists() and self._is_within_project(candidate):
                self.open_file(candidate)
                return

        files = self._project_manager.list_markdown_files(normalized_root)
        if files:
            self.open_file(files[0])
        else:
            self._current_file = None
            self._editor.clear()
            self._preview.clear()
            self._apply_direction(self._state.global_direction)
            self._persist_state()

    def _refresh_tree(self, select_path: Path | None = None) -> None:
        """Refresh the Markdown file tree."""
        if not self._project:
            self._file_tree.clear()
            return
        files = self._project_manager.list_markdown_files(self._project.root)
        self._file_tree.populate(self._project.root, files)
        if select_path:
            self._file_tree.select_file(select_path)

    def _on_editor_text_changed(self) -> None:
        """Handle editor changes with auto-save."""
        if self._is_loading_file:
            return
        self._save_timer.start()
        if self._stack.currentWidget() is self._preview_page:
            self._update_preview()

    def _save_current_file(self) -> None:
        """Persist the current document if one is opened."""
        if not self._current_file:
            return
        self._project_manager.write_file(self._current_file, self._editor.toPlainText())
        self._update_preview()
        self._update_status("Saved")

    def _update_preview(self) -> None:
        """Refresh the rendered Markdown preview."""
        direction = self._document_direction(self._current_file) if self._current_file else self._state.global_direction
        html = self._markdown_service.render(self._editor.toPlainText(), direction)
        self._preview.setHtml(html)

    def _update_status(self, prefix: str | None = None) -> None:
        """Update the status bar."""
        if not self._current_file:
            self.statusBar().showMessage(prefix or "Ready")
            return
        mode = "Preview" if self._stack.currentWidget() is self._preview_page else "Edit"
        direction = self._document_direction(self._current_file).upper()
        text = f"{mode}  |  {direction}  |  {self._current_file.name}"
        if prefix:
            text = f"{prefix}  |  {text}"
        self.statusBar().showMessage(text)

    def _apply_direction(self, direction: str) -> None:
        """Apply direction to editor and preview widgets."""
        self._editor.set_direction(direction)
        preview_direction = (
            Qt.LayoutDirection.RightToLeft if direction == "rtl" else Qt.LayoutDirection.LeftToRight
        )
        self._preview.setLayoutDirection(preview_direction)
        self._preview.document().setDefaultTextOption(self._editor.document().defaultTextOption())
        self._update_direction_button()
        self._update_status()

    def _document_direction(self, file_path: Path | None) -> str:
        """Resolve the direction for a document."""
        if not self._project or not file_path:
            return self._state.global_direction
        try:
            key = self._project.relative_path(self._normalize_path(file_path))
        except ValueError:
            return self._state.global_direction
        return self._document_directions.get(key, self._state.global_direction)

    def _persist_state(self) -> None:
        """Persist current UI state."""
        self._state.last_project = str(self._project.root) if self._project else None
        self._state.last_file = str(self._current_file) if self._current_file else None
        self._state.sidebar_visible = not self._file_tree.isHidden()
        self._state.preview_visible = self._stack.currentWidget() is self._preview_page
        self._settings_service.save_document_directions(self._document_directions)
        self._settings_service.save_state(self._state)

    def _build_centered_page(self, widget: QWidget) -> QWidget:
        """Wrap a widget in a centered fixed-width page layout."""
        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(16, 18, 16, 18)
        wrapper_layout.setSpacing(0)

        column = QWidget()
        column.setObjectName("writingColumn")
        column.setMinimumWidth(780)
        column.setMaximumWidth(1040)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(18, 18, 18, 18)
        column_layout.setSpacing(0)
        column_layout.addWidget(widget)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        wrapper_layout.addStretch(1)
        wrapper_layout.addWidget(column)
        wrapper_layout.addStretch(1)
        return wrapper

    def _require_project(self) -> bool:
        """Ensure a project is open before acting."""
        if self._project:
            return True
        self._show_error("Open or create a project first.")
        return False

    def _show_error(self, message: str) -> None:
        """Display an error dialog."""
        QMessageBox.critical(self, "Katib", message)

    def _update_direction_button(self) -> None:
        """Refresh the direction toggle label."""
        direction = (
            self._document_direction(self._current_file)
            if self._project and self._current_file
            else self._state.global_direction
        )
        self._direction_button.setText(direction.upper())
        self._direction_button.setToolTip("Toggle writing direction")

    def _normalize_path(self, path: Path) -> Path:
        """Normalize a path without requiring it to exist."""
        return path.expanduser().resolve(strict=False)

    def _is_within_project(self, path: Path) -> bool:
        """Return whether a path belongs to the current project."""
        if not self._project:
            return False
        try:
            self._normalize_path(path).relative_to(self._project.root)
        except ValueError:
            return False
        return True
