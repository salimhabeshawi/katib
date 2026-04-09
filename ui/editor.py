"""Custom editor widgets for Katib."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextBlock, QTextBlockFormat, QTextCursor, QTextOption
from PySide6.QtWidgets import QFrame, QPlainTextEdit

from ui.markdown_highlighter import MarkdownHighlighter


class MarkdownEditor(QPlainTextEdit):
    """Plain text editor tuned for long-form Markdown writing."""

    _DOUBLE_MARKERS = {"*", "_", "~", "`"}

    def __init__(self, parent: object | None = None) -> None:
        """Initialize the writing editor."""
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setTabStopDistance(32)
        self.setPlaceholderText("Start writing...")
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.setCursorWidth(2)
        self.setCenterOnScroll(True)

        font = self.font()
        font.setFamilies(["JetBrains Mono", "Cascadia Mono", "Noto Naskh Arabic"])
        font.setPointSize(12)
        self.setFont(font)
        self._highlighter = MarkdownHighlighter(self.document())

        block_format = self.textCursor().blockFormat()
        block_format.setLineHeight(
            165.0,
            QTextBlockFormat.LineHeightTypes.ProportionalHeight.value,
        )
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.mergeBlockFormat(block_format)
        cursor.clearSelection()
        self.setTextCursor(cursor)

        margins = self.contentsMargins()
        margins.setLeft(28)
        margins.setRight(28)
        margins.setTop(24)
        margins.setBottom(24)
        self.setContentsMargins(margins)

    def set_direction(self, direction: str) -> None:
        """Apply RTL or LTR direction to the editor."""
        is_rtl = direction == "rtl"
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight)

        option = self.document().defaultTextOption()
        option.setAlignment(Qt.AlignmentFlag.AlignRight if is_rtl else Qt.AlignmentFlag.AlignLeft)
        option.setTextDirection(
            Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        )
        self.document().setDefaultTextOption(option)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle editor key presses with Markdown-aware indentation."""
        if self._handle_double_marker_autoclose(event):
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            if cursor.hasSelection():
                super().keyPressEvent(event)
                return

            block = cursor.block()
            text_before_cursor = block.text()[: cursor.positionInBlock()]
            prefix = self._next_line_prefix(block, text_before_cursor)
            super().keyPressEvent(event)
            if prefix:
                self.insertPlainText(prefix)
            return

        super().keyPressEvent(event)

    def _handle_double_marker_autoclose(self, event: QKeyEvent) -> bool:
        """Auto-close paired Markdown markers when typing the second marker."""
        if event.modifiers() not in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ShiftModifier):
            return False

        marker = event.text()
        if marker not in self._DOUBLE_MARKERS:
            return False

        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        block = cursor.block()
        if self._highlighter.language_for_block_state(block.userState()) is not None:
            return False

        line = block.text()
        position = cursor.positionInBlock()
        if position <= 0 or position > len(line):
            return False

        previous = line[position - 1]
        if previous != marker:
            return False

        if position >= 2 and line[position - 2] == "\\":
            return False

        cursor.insertText(marker * 3)
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 2)
        self.setTextCursor(cursor)
        return True

    def _next_line_prefix(self, block: QTextBlock, line: str) -> str:
        """Build the indentation prefix for the next line."""
        code_language = self._highlighter.language_for_block_state(block.userState())
        if code_language is not None and not self._highlighter._is_fence_line(line):
            return self._next_code_indent(line, code_language)

        indent_match = re.match(r"^(\s+)", line)
        base_indent = indent_match.group(1) if indent_match else ""
        stripped = line.strip()

        if not stripped:
            return base_indent

        unordered = re.match(r"^(\s*)([-+*])(\s+)(.*)$", line)
        if unordered:
            content = unordered.group(4)
            if not content.strip():
                return unordered.group(1)
            return f"{unordered.group(1)}{unordered.group(2)}{unordered.group(3)}"

        checklist = re.match(r"^(\s*)([-+*])(\s+\[[ xX]\]\s+)(.*)$", line)
        if checklist:
            content = checklist.group(4)
            if not content.strip():
                return checklist.group(1)
            return f"{checklist.group(1)}{checklist.group(2)}{checklist.group(3)}"

        ordered = re.match(r"^(\s*)(\d+)([.)])(\s+)(.*)$", line)
        if ordered:
            content = ordered.group(5)
            if not content.strip():
                return ordered.group(1)
            next_number = int(ordered.group(2)) + 1
            return f"{ordered.group(1)}{next_number}{ordered.group(3)}{ordered.group(4)}"

        quote = re.match(r"^(\s*)(>+)(\s?)(.*)$", line)
        if quote:
            content = quote.group(4)
            if not content.strip():
                return quote.group(1)
            spacing = quote.group(3) or " "
            return f"{quote.group(1)}{quote.group(2)}{spacing}"

        return base_indent

    def _next_code_indent(self, line: str, language: str) -> str:
        """Build the indentation prefix for the next line inside a fenced code block."""
        indent_match = re.match(r"^(\s*)", line)
        base_indent = indent_match.group(1) if indent_match else ""
        stripped = line.strip()

        if not stripped:
            return base_indent

        unit = self._indent_unit(base_indent)
        increase = False

        if re.search(r"[\{\[\(]\s*$", stripped):
            increase = True
        elif language in {"python", "py"} and stripped.endswith(":"):
            increase = True
        elif language in {"ruby"} and re.search(r"\b(do|def|class|module|if|unless|case|begin)\b.*$", stripped):
            increase = True
        elif language in {"yaml", "yml"} and stripped.endswith(":"):
            increase = True

        return f"{base_indent}{unit}" if increase else base_indent

    def _indent_unit(self, existing_indent: str) -> str:
        """Return a reasonable indentation unit."""
        if "\t" in existing_indent:
            return "\t"
        return "    "
