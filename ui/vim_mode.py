"""Vim mode controller for the Markdown editor."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QInputDialog

if TYPE_CHECKING:
    from ui.editor import MarkdownEditor


class VimModeController:
    """Encapsulate Vim mode state and key handling for an editor."""

    def __init__(
        self,
        editor: "MarkdownEditor",
        mode_changed_callback: Callable[[bool, str], None],
    ) -> None:
        self._editor = editor
        self._mode_changed_callback = mode_changed_callback

        self._enabled = False
        self._insert_mode = True
        self._replace_mode = False
        self._pending_command = ""
        self._count_prefix = ""
        self._yank_buffer = ""

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable Vim-style modal keybindings."""
        self._enabled = enabled
        self._pending_command = ""
        self._set_insert_mode(not enabled)
        self._apply_cursor_style()
        self._emit_mode_changed()

    def is_enabled(self) -> bool:
        """Return whether Vim mode is enabled."""
        return self._enabled

    def label(self) -> str:
        """Return a label for the current Vim mode state."""
        if not self._enabled:
            return "OFF"
        return "INSERT" if self._insert_mode else "NORMAL"

    def _emit_mode_changed(self) -> None:
        self._mode_changed_callback(self._enabled, self.label())

    def _set_insert_mode(self, enabled: bool) -> None:
        """Switch Vim insert/normal state."""
        self._insert_mode = enabled
        self._apply_cursor_style()
        self._emit_mode_changed()

    def _apply_cursor_style(self) -> None:
        """Render block cursor in Vim normal mode and bar cursor otherwise."""
        normal_mode = self._enabled and not self._insert_mode
        self._editor.setOverwriteMode(normal_mode)
        self._editor.setCursorWidth(
            2
            if not normal_mode
            else max(8, self._editor.fontMetrics().averageCharWidth())
        )

    def handle_keypress(self, event: QKeyEvent) -> bool:
        """Handle Vim modal keybindings when Vim mode is enabled."""
        if not self._enabled:
            return False

        if self._insert_mode:
            if event.key() == Qt.Key.Key_Escape:
                self._pending_command = ""
                self._count_prefix = ""
                self._replace_mode = False
                self._set_insert_mode(False)
                return True
            if (
                self._replace_mode
                and event.text()
                and event.modifiers()
                in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ShiftModifier)
            ):
                cursor = self._editor.textCursor()
                cursor.deleteChar()
                cursor.insertText(event.text())
                self._editor.setTextCursor(cursor)
                return True
            return False

        if event.key() == Qt.Key.Key_Escape:
            self._pending_command = ""
            self._count_prefix = ""
            return True

        cursor = self._editor.textCursor()
        key_text = event.text()

        if (
            event.key() == Qt.Key.Key_R
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self._editor.redo()
            return True

        if key_text == "u":
            self._editor.undo()
            return True

        if key_text == "/":
            self._search_forward()
            return True

        if key_text.isdigit():
            if key_text == "0" and not self._count_prefix and not self._pending_command:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                self._editor.setTextCursor(cursor)
                return True
            self._count_prefix += key_text
            return True

        count = self._consume_count()
        had_count = count > 1

        if self._pending_command == "g":
            self._pending_command = ""
            if key_text == "g":
                if had_count:
                    self._go_to_line(count)
                else:
                    cursor.movePosition(QTextCursor.MoveOperation.Start)
                    self._editor.setTextCursor(cursor)
                return True
            if key_text == "J":
                self._join_with_next_line(count, add_space=False)
                return True
            if key_text == "_":
                self._move_to_last_non_blank()
                return True
            if key_text in {"~", "u", "U"}:
                self._pending_command = f"g{key_text}"
                return True
            if key_text in {"p", "P"}:
                self._paste(after=(key_text == "p"))
                return True
            return True

        if self._pending_command == "y":
            self._pending_command = ""
            if key_text == "y":
                self._yank_lines(count)
                return True
            if key_text in {"w", "$"}:
                self._yank_motion(key_text, count)
                return True
            if key_text == "i":
                self._pending_command = "yi"
                return True
            if key_text == "a":
                self._pending_command = "ya"
                return True
            return True

        if self._pending_command == "d":
            self._pending_command = ""
            if key_text == "d":
                self._delete_lines(count)
                return True
            if key_text in {"$", "w", "e"}:
                self._delete_motion(key_text, count)
                return True
            if key_text == "i":
                self._pending_command = "di"
                return True
            if key_text == "a":
                self._pending_command = "da"
                return True
            return True

        if self._pending_command == "c":
            self._pending_command = ""
            if key_text == "c":
                self._delete_lines(count)
                self._replace_mode = False
                self._set_insert_mode(True)
                return True
            if key_text in {"$", "w", "e"}:
                self._change_motion(key_text, count)
                return True
            if key_text == "i":
                self._pending_command = "ci"
                return True
            return True

        if self._pending_command in {"di", "da", "yi", "ya", "ci"}:
            pending = self._pending_command
            self._pending_command = ""
            if key_text == "w":
                self._text_object_word(pending)
                return True
            return True

        if self._pending_command in {">", "<"}:
            pending = self._pending_command
            self._pending_command = ""
            if key_text == pending:
                self._shift_current_line(right=(pending == ">"), count=count)
                return True
            return True

        if self._pending_command in {"f", "t", "r"}:
            pending = self._pending_command
            self._pending_command = ""
            if key_text:
                if pending == "r":
                    self._replace_single_character(key_text)
                else:
                    self._find_in_line(key_text, till=(pending == "t"), count=count)
                return True
            return True

        if self._pending_command == "g~":
            self._pending_command = ""
            self._apply_case_motion("swap", key_text, count)
            return True

        if self._pending_command == "gu":
            self._pending_command = ""
            self._apply_case_motion("lower", key_text, count)
            return True

        if self._pending_command == "gU":
            self._pending_command = ""
            self._apply_case_motion("upper", key_text, count)
            return True

        if key_text == "g":
            self._pending_command = "g"
            return True

        if key_text == "y":
            self._pending_command = "y"
            return True

        if key_text == "d":
            self._pending_command = "d"
            return True

        if key_text == "c":
            self._pending_command = "c"
            return True

        if key_text in {">", "<", "f", "t", "r"}:
            self._pending_command = key_text
            return True

        if key_text == "i":
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "I":
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            self._editor.setTextCursor(cursor)
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "a":
            cursor.movePosition(QTextCursor.MoveOperation.Right)
            self._editor.setTextCursor(cursor)
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "A":
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            self._editor.setTextCursor(cursor)
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "R":
            self._replace_mode = True
            self._set_insert_mode(True)
            return True

        if key_text == "h":
            cursor.movePosition(
                QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, count
            )
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "j":
            for _ in range(count):
                cursor.movePosition(QTextCursor.MoveOperation.Down)
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "k":
            for _ in range(count):
                cursor.movePosition(QTextCursor.MoveOperation.Up)
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "l":
            cursor.movePosition(
                QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, count
            )
            self._editor.setTextCursor(cursor)
            return True

        if key_text in {"H", "M", "L"}:
            self._move_to_viewport_line(key_text)
            return True

        if key_text == "$":
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "^":
            self._move_to_first_non_blank()
            return True

        if key_text == "{":
            self._move_paragraph(previous=True, count=count)
            return True

        if key_text == "}":
            self._move_paragraph(previous=False, count=count)
            return True

        if key_text in {"w", "W"}:
            for _ in range(count):
                cursor.movePosition(QTextCursor.MoveOperation.NextWord)
            self._editor.setTextCursor(cursor)
            return True

        if key_text in {"b", "B"}:
            for _ in range(count):
                cursor.movePosition(QTextCursor.MoveOperation.PreviousWord)
            self._editor.setTextCursor(cursor)
            return True

        if key_text in {"e", "E"}:
            for _ in range(count):
                cursor.movePosition(QTextCursor.MoveOperation.EndOfWord)
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "G":
            if had_count:
                self._go_to_line(count)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self._editor.setTextCursor(cursor)
            return True

        if key_text == "x":
            for _ in range(count):
                cursor.deleteChar()
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "X":
            for _ in range(count):
                cursor.deletePreviousChar()
            self._editor.setTextCursor(cursor)
            return True

        if key_text == "s":
            for _ in range(count):
                cursor.deleteChar()
            self._editor.setTextCursor(cursor)
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "C":
            self._change_motion("$", max(1, count))
            return True

        if key_text == "D":
            self._delete_motion("$", max(1, count))
            return True

        if key_text == "Y":
            self._yank_motion("$", max(1, count))
            return True

        if key_text == "J":
            self._join_with_next_line(max(1, count), add_space=True)
            return True

        if key_text == "~":
            for _ in range(max(1, count)):
                self._toggle_char_case_under_cursor()
            return True

        if key_text == "p":
            for _ in range(max(1, count)):
                self._paste(after=True)
            return True

        if key_text == "P":
            for _ in range(max(1, count)):
                self._paste(after=False)
            return True

        if key_text == "S":
            self._delete_lines(max(1, count))
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "o":
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            cursor.insertBlock()
            self._editor.setTextCursor(cursor)
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        if key_text == "O":
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.insertBlock()
            cursor.movePosition(QTextCursor.MoveOperation.Up)
            self._editor.setTextCursor(cursor)
            self._replace_mode = False
            self._set_insert_mode(True)
            return True

        return True

    def _consume_count(self) -> int:
        """Consume and clear numeric Vim prefix count."""
        if not self._count_prefix:
            return 1
        value = max(1, int(self._count_prefix))
        self._count_prefix = ""
        return value

    def _go_to_line(self, line_number: int) -> None:
        """Move cursor to a specific 1-based line number."""
        block = self._editor.document().findBlockByNumber(max(0, line_number - 1))
        if not block.isValid():
            block = self._editor.document().lastBlock()
        cursor = self._editor.textCursor()
        cursor.setPosition(block.position())
        self._editor.setTextCursor(cursor)

    def _move_to_first_non_blank(self) -> None:
        """Move to first non-blank character on current line."""
        cursor = self._editor.textCursor()
        text = cursor.block().text()
        idx = len(text) - len(text.lstrip())
        cursor.setPosition(cursor.block().position() + idx)
        self._editor.setTextCursor(cursor)

    def _move_to_last_non_blank(self) -> None:
        """Move to last non-blank character on current line."""
        cursor = self._editor.textCursor()
        text = cursor.block().text().rstrip()
        if not text:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        else:
            cursor.setPosition(cursor.block().position() + len(text) - 1)
        self._editor.setTextCursor(cursor)

    def _move_to_viewport_line(self, selector: str) -> None:
        """Move cursor to top/middle/bottom visible line (H/M/L)."""
        viewport_rect = self._editor.viewport().rect()
        if selector == "H":
            point = viewport_rect.topLeft()
        elif selector == "M":
            point = viewport_rect.center()
        else:
            point = viewport_rect.bottomLeft()
        cursor = self._editor.cursorForPosition(point)
        self._editor.setTextCursor(cursor)

    def _move_paragraph(self, *, previous: bool, count: int) -> None:
        """Move cursor to previous/next paragraph boundary."""
        cursor = self._editor.textCursor()
        step = (
            QTextCursor.MoveOperation.Up if previous else QTextCursor.MoveOperation.Down
        )
        for _ in range(max(1, count)):
            while True:
                moved = cursor.movePosition(step)
                if not moved:
                    break
                if not cursor.block().text().strip():
                    break
        self._editor.setTextCursor(cursor)

    def _find_in_line(self, char: str, *, till: bool, count: int) -> None:
        """Find next character occurrence in line (f/t)."""
        cursor = self._editor.textCursor()
        block = cursor.block()
        text = block.text()
        pos = cursor.positionInBlock()
        idx = pos
        for _ in range(max(1, count)):
            idx = text.find(char, idx + 1)
            if idx < 0:
                return
        if till:
            idx -= 1
            if idx < 0:
                return
        cursor.setPosition(block.position() + idx)
        self._editor.setTextCursor(cursor)

    def _replace_single_character(self, char: str) -> None:
        """Replace character under cursor (r)."""
        cursor = self._editor.textCursor()
        cursor.deleteChar()
        cursor.insertText(char)
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        self._editor.setTextCursor(cursor)

    def _join_with_next_line(self, count: int, *, add_space: bool) -> None:
        """Join current line with following line(s)."""
        cursor = self._editor.textCursor()
        for _ in range(max(1, count)):
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            if cursor.atEnd():
                break
            cursor.deleteChar()
            if add_space:
                cursor.insertText(" ")
        self._editor.setTextCursor(cursor)

    def _shift_current_line(self, *, right: bool, count: int) -> None:
        """Shift current line(s) right or left by one indent unit."""
        cursor = self._editor.textCursor()
        block = cursor.block()
        unit = self._editor._indent_unit("")
        for _ in range(max(1, count)):
            line_cursor = QTextCursor(block)
            line_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            if right:
                line_cursor.insertText(unit)
            else:
                line_text = block.text()
                remove = (
                    len(unit)
                    if line_text.startswith(unit)
                    else min(len(line_text) - len(line_text.lstrip()), len(unit))
                )
                if remove > 0:
                    line_cursor.movePosition(
                        QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor,
                        remove,
                    )
                    line_cursor.removeSelectedText()
            block = block.next()
            if not block.isValid():
                break
        self._editor.setTextCursor(cursor)

    def _yank_lines(self, count: int) -> None:
        """Yank one or more full lines into Vim buffer."""
        cursor = self._editor.textCursor()
        start = cursor.block().position()
        end_block = cursor.block()
        for _ in range(max(1, count) - 1):
            if end_block.next().isValid():
                end_block = end_block.next()
        end = end_block.position() + end_block.length()
        doc_text = self._editor.toPlainText()
        self._yank_buffer = doc_text[start:end]

    def _delete_lines(self, count: int) -> None:
        """Delete one or more full lines."""
        self._yank_lines(count)
        cursor = self._editor.textCursor()
        start = cursor.block().position()
        end_block = cursor.block()
        for _ in range(max(1, count) - 1):
            if end_block.next().isValid():
                end_block = end_block.next()
        end = end_block.position() + end_block.length()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self._editor.setTextCursor(cursor)

    def _delete_motion(self, motion: str, count: int) -> None:
        """Delete text selected by a simple motion."""
        cursor = self._editor.textCursor()
        start = cursor.position()
        if motion == "$":
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
        elif motion in {"w", "e"}:
            op = (
                QTextCursor.MoveOperation.NextWord
                if motion == "w"
                else QTextCursor.MoveOperation.EndOfWord
            )
            for _ in range(max(1, count)):
                cursor.movePosition(op, QTextCursor.MoveMode.KeepAnchor)
        self._yank_buffer = cursor.selectedText().replace("\u2029", "\n")
        cursor.removeSelectedText()
        cursor.setPosition(start)
        self._editor.setTextCursor(cursor)

    def _change_motion(self, motion: str, count: int) -> None:
        """Change text selected by a simple motion then enter insert mode."""
        self._delete_motion(motion, count)
        self._replace_mode = False
        self._set_insert_mode(True)

    def _yank_motion(self, motion: str, count: int) -> None:
        """Yank text selected by a simple motion."""
        cursor = self._editor.textCursor()
        if motion == "$":
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
        elif motion == "w":
            for _ in range(max(1, count)):
                cursor.movePosition(
                    QTextCursor.MoveOperation.NextWord,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        self._yank_buffer = cursor.selectedText().replace("\u2029", "\n")

    def _text_object_word(self, command: str) -> None:
        """Apply yiw/yaw/diw/daw/ciw on the word under cursor."""
        cursor = self._editor.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        if command in {"yaw", "daw", "ya"}:
            doc = self._editor.toPlainText()
            if end < len(doc) and doc[end].isspace():
                end += 1
        text = self._editor.toPlainText()[start:end]
        if command.startswith("y"):
            self._yank_buffer = text
            return

        edit = self._editor.textCursor()
        edit.setPosition(start)
        edit.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._yank_buffer = text
        edit.removeSelectedText()
        self._editor.setTextCursor(edit)
        if command.startswith("c"):
            self._replace_mode = False
            self._set_insert_mode(True)

    def _toggle_char_case_under_cursor(self) -> None:
        """Toggle case for character under cursor (~)."""
        cursor = self._editor.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
        )
        text = cursor.selectedText()
        if not text:
            return
        repl = text.swapcase()
        cursor.insertText(repl)
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        self._editor.setTextCursor(cursor)

    def _apply_case_motion(self, mode: str, motion: str, count: int) -> None:
        """Apply g~, gu, gU against a basic motion."""
        cursor = self._editor.textCursor()
        if motion == "w":
            for _ in range(max(1, count)):
                cursor.movePosition(
                    QTextCursor.MoveOperation.NextWord,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        elif motion == "$":
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
        else:
            return
        text = cursor.selectedText()
        if mode == "swap":
            repl = text.swapcase()
        elif mode == "lower":
            repl = text.lower()
        else:
            repl = text.upper()
        cursor.insertText(repl)
        self._editor.setTextCursor(cursor)

    def _search_forward(self) -> None:
        """Prompt for /pattern and jump to next match."""
        pattern, ok = QInputDialog.getText(self._editor, "Vim Search", "pattern:")
        if not ok or not pattern:
            return
        self._editor.find(pattern)

    def _paste(self, *, after: bool) -> None:
        """Paste yanked text before or after the current cursor position."""
        if not self._yank_buffer:
            return

        cursor = self._editor.textCursor()
        text = self._yank_buffer
        if text.endswith("\n"):
            if after:
                cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
                cursor.insertBlock()
            else:
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.insertText(text.rstrip("\n"))
        else:
            if after:
                cursor.movePosition(QTextCursor.MoveOperation.Right)
            cursor.insertText(text)
        self._editor.setTextCursor(cursor)
