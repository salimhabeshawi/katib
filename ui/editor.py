"""Custom editor widgets for Katib."""

from __future__ import annotations

import re

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QTextBlock,
    QTextBlockFormat,
    QTextCursor,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QTextEdit, QWidget

from ui.markdown_highlighter import MarkdownHighlighter


class _LineNumberArea(QWidget):
    """Paintable gutter area for editor line numbers."""

    def __init__(self, editor: "MarkdownEditor") -> None:
        """Initialize the line-number gutter."""
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        """Return the gutter preferred width."""
        return QSize(self._editor._line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        """Delegate gutter painting to the editor."""
        self._editor._paint_line_number_area(event)


class MarkdownEditor(QPlainTextEdit):
    """Plain text editor tuned for long-form Markdown writing."""

    _PAIRABLE_MARKERS = {"*", "_", "~", "`"}
    _OPENING_PAIRS = {"(": ")", "[": "]", "{": "}"}
    _SYMMETRIC_PAIRS = {'"': '"', "'": "'"}
    _CLOSING_BRACKETS = {")", "]", "}"}
    _LINE_NUMBER_GAP = 14

    def __init__(self, parent: object | None = None) -> None:
        """Initialize the writing editor."""
        super().__init__(parent)
        self._line_number_area = _LineNumberArea(self)

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

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._refresh_line_number_area)
        self._update_line_number_area_width(0)
        self._highlight_current_line()

    def resizeEvent(self, event) -> None:
        """Resize the line-number gutter with the editor viewport."""
        super().resizeEvent(event)
        content_rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(
                content_rect.left(),
                content_rect.top(),
                self._line_number_area_width(),
                content_rect.height(),
            )
        )

    def _line_number_area_width(self) -> int:
        """Compute the width needed for rendering all line numbers."""
        digits = max(2, len(str(max(1, self.blockCount()))))
        text_width = 12 + self.fontMetrics().horizontalAdvance("9") * digits
        return text_width + self._LINE_NUMBER_GAP

    def _update_line_number_area_width(self, _block_count: int) -> None:
        """Adjust viewport margins to reserve line-number gutter space."""
        self.setViewportMargins(self._line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy: int) -> None:
        """Update or scroll the gutter when editor content updates."""
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def _refresh_line_number_area(self) -> None:
        """Repaint gutter to reflect the active cursor line."""
        self._line_number_area.update()
        self._highlight_current_line()

    def _highlight_current_line(self) -> None:
        """Highlight the line that currently contains the cursor."""
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#1a2028"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def _paint_line_number_area(self, event) -> None:
        """Paint line numbers beside the editor text."""
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#0f1318"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())
        current_block = self.textCursor().blockNumber()
        number_width = self._line_number_area.width() - self._LINE_NUMBER_GAP

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(
                    QColor("#cdd6df")
                    if block_number == current_block
                    else QColor("#66707d")
                )
                painter.drawText(
                    0,
                    top,
                    number_width,
                    max(1, bottom - top),
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                    str(block_number + 1),
                )

            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def set_direction(self, direction: str) -> None:
        """Apply RTL or LTR direction to the editor."""
        is_rtl = direction == "rtl"
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        )

        option = self.document().defaultTextOption()
        option.setAlignment(
            Qt.AlignmentFlag.AlignRight if is_rtl else Qt.AlignmentFlag.AlignLeft
        )
        option.setTextDirection(
            Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        )
        self.document().setDefaultTextOption(option)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle editor key presses with Markdown-aware indentation."""
        if self._handle_symbol_autoclose(event):
            return

        if self._handle_double_marker_autoclose(event):
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            if cursor.hasSelection():
                super().keyPressEvent(event)
                return

            if self._handle_bracket_enter_split(cursor):
                return

            if self._handle_fence_enter_split(cursor):
                return

            block = cursor.block()
            text_before_cursor = block.text()[: cursor.positionInBlock()]
            prefix = self._next_line_prefix(block, text_before_cursor)
            super().keyPressEvent(event)
            if prefix:
                self.insertPlainText(prefix)
            return

        super().keyPressEvent(event)

    def _handle_symbol_autoclose(self, event: QKeyEvent) -> bool:
        """Auto-close common symbol pairs and step through existing closers."""
        if event.modifiers() not in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ):
            return False

        symbol = event.text()
        if len(symbol) != 1:
            return False

        cursor = self.textCursor()
        has_selection = cursor.hasSelection()
        block = cursor.block()
        line = block.text()
        position = cursor.positionInBlock()
        if position < 0 or position > len(line):
            return False

        next_char = line[position] if position < len(line) else ""
        previous_char = line[position - 1] if position > 0 else ""

        if not has_selection and symbol in self._CLOSING_BRACKETS | set(
            self._SYMMETRIC_PAIRS
        ):
            if next_char == symbol:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
                self.setTextCursor(cursor)
                return True

        if symbol in self._OPENING_PAIRS:
            return self._insert_pair(
                cursor, symbol, self._OPENING_PAIRS[symbol], has_selection
            )

        if symbol in self._SYMMETRIC_PAIRS:
            # Keep contractions like don't natural without forced pairing.
            if symbol == "'" and (previous_char.isalnum() or next_char.isalnum()):
                return False
            if previous_char == "\\":
                return False
            return self._insert_pair(cursor, symbol, symbol, has_selection)

        return False

    def _insert_pair(
        self,
        cursor: QTextCursor,
        opening: str,
        closing: str,
        has_selection: bool,
    ) -> bool:
        """Insert a pair around selection or place cursor between a new pair."""
        if has_selection:
            selected_text = cursor.selectedText().replace("\u2029", "\n")
            cursor.insertText(f"{opening}{selected_text}{closing}")
            self.setTextCursor(cursor)
            return True

        cursor.insertText(f"{opening}{closing}")
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        self.setTextCursor(cursor)
        return True

    def _handle_bracket_enter_split(self, cursor: QTextCursor) -> bool:
        """Split paired brackets on Enter into a multiline block."""
        block = cursor.block()
        line = block.text()
        position = cursor.positionInBlock()

        if position <= 0 or position >= len(line):
            return False

        opening = line[position - 1]
        closing = line[position]
        if self._OPENING_PAIRS.get(opening) != closing:
            return False

        indent_match = re.match(r"^(\s*)", line)
        indent = indent_match.group(1) if indent_match else ""
        inner_indent = f"{indent}{self._indent_unit(indent)}"
        replacement = f"{indent}{opening}\n{inner_indent}\n{indent}{closing}"

        block_start = block.position()
        pair_start = block_start + position - 1
        cursor.beginEditBlock()
        cursor.setPosition(pair_start)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 2
        )
        cursor.insertText(replacement)
        cursor.setPosition(pair_start + 2 + len(inner_indent))
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        return True

    def _handle_double_marker_autoclose(self, event: QKeyEvent) -> bool:
        """Auto-close Markdown markers for single, double, and triple backticks."""
        if event.modifiers() not in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ):
            return False

        marker = event.text()
        if marker not in self._PAIRABLE_MARKERS:
            return False

        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        block = cursor.block()
        line = block.text()
        if self._highlighter.language_for_block_state(
            block.userState()
        ) is not None and not self._highlighter._is_fence_line(line):
            return False

        position = cursor.positionInBlock()
        if position < 0 or position > len(line):
            return False

        # Do not auto-pair underscores in the middle of identifiers.
        if marker == "_":
            if position > 0 and line[position - 1].isalnum():
                return False
            if position < len(line) and line[position].isalnum():
                return False

        if position > 0 and line[position - 1] == "\\":
            return False

        left_count = self._consecutive_count(line, position - 1, -1, marker)
        right_count = self._consecutive_count(line, position, 1, marker)
        max_pairs = 3 if marker in {"`", "*"} else 2

        # If we are at the boundary of an existing closer, step over it.
        if right_count > 0 and left_count != right_count:
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            self.setTextCursor(cursor)
            return True

        if left_count == right_count and left_count < max_pairs:
            cursor.insertText(marker * 2)
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return True

        return False

    def _handle_fence_enter_split(self, cursor: QTextCursor) -> bool:
        """Split paired triple backticks into a fenced block on Enter."""
        block = cursor.block()
        line = block.text()
        position = cursor.positionInBlock()

        if position < 3 or position + 3 > len(line):
            return False
        if (
            line[position - 3 : position] != "```"
            or line[position : position + 3] != "```"
        ):
            return False

        before_fence = line[: position - 3]
        after_fence = line[position + 3 :]
        if before_fence.strip() or after_fence.strip():
            return False

        indent_match = re.match(r"^(\s*)", line)
        indent = indent_match.group(1) if indent_match else ""
        replacement = f"{indent}```\n{indent}\n{indent}```"

        block_start = block.position()
        cursor.beginEditBlock()
        cursor.setPosition(block_start)
        cursor.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.insertText(replacement)
        cursor.setPosition(block_start + len(indent) + 4 + len(indent))
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        return True

    def _consecutive_count(self, text: str, start: int, step: int, marker: str) -> int:
        """Count consecutive marker characters from a start index in one direction."""
        count = 0
        index = start
        while 0 <= index < len(text) and text[index] == marker:
            count += 1
            index += step
        return count

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
            return (
                f"{ordered.group(1)}{next_number}{ordered.group(3)}{ordered.group(4)}"
            )

        quote = re.match(r"^(\s*)(>+)(\s?)(.*)$", line)
        if quote:
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
        elif language in {"ruby"} and re.search(
            r"\b(do|def|class|module|if|unless|case|begin)\b.*$", stripped
        ):
            increase = True
        elif language in {"yaml", "yml"} and stripped.endswith(":"):
            increase = True

        return f"{base_indent}{unit}" if increase else base_indent

    def _indent_unit(self, existing_indent: str) -> str:
        """Return a reasonable indentation unit."""
        if "\t" in existing_indent:
            return "\t"
        return "    "
