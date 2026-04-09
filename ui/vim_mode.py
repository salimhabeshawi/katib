"""Vim mode controller for the Markdown editor."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt
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
        self._visual_mode: str | None = None
        self._visual_anchor: int | None = None
        self._last_visual_selection: tuple[int, int, str] | None = None
        self._block_insert_start: int | None = None
        self._block_insert_targets: list[int] = []
        self._insert_j_pending = False
        self._insert_j_timer = QTimer(self._editor)
        self._insert_j_timer.setSingleShot(True)
        self._insert_j_timer.setInterval(260)
        self._insert_j_timer.timeout.connect(self._flush_pending_insert_j)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable Vim-style modal keybindings."""
        self._enabled = enabled
        self._pending_command = ""
        self._visual_mode = None
        self._visual_anchor = None
        self._block_insert_start = None
        self._block_insert_targets = []
        self._insert_j_pending = False
        self._insert_j_timer.stop()
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
        if self._visual_mode == "char":
            return "VISUAL"
        if self._visual_mode == "line":
            return "V-LINE"
        if self._visual_mode == "block":
            return "V-BLOCK"
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
            if self._insert_j_pending:
                if (
                    event.text() == "j"
                    and event.modifiers() == Qt.KeyboardModifier.NoModifier
                ):
                    self._insert_j_pending = False
                    self._insert_j_timer.stop()
                    self._leave_insert_mode()
                    return True
                self._flush_pending_insert_j()

            if event.key() == Qt.Key.Key_Escape:
                self._leave_insert_mode()
                return True

            if (
                event.text() == "j"
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                self._insert_j_pending = True
                self._insert_j_timer.start()
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
            if self._visual_mode is not None:
                self._leave_visual_mode(store_last=True)
            return True

        if self._visual_mode is not None:
            return self._handle_visual_keypress(event)

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
            if key_text == "v":
                self._reselect_last_visual()
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

        if key_text == "v":
            self._enter_visual_mode("char")
            return True

        if key_text == "V":
            self._enter_visual_mode("line")
            return True

        if (
            event.key() == Qt.Key.Key_V
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self._enter_visual_mode("block")
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

    def _leave_insert_mode(self) -> None:
        """Return from insert mode to normal mode with Vim-like cursor placement."""
        self._insert_j_pending = False
        self._insert_j_timer.stop()
        self._apply_pending_block_insert()
        self._pending_command = ""
        self._count_prefix = ""
        self._replace_mode = False

        cursor = self._editor.textCursor()
        if cursor.position() > 0:
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self._editor.setTextCursor(cursor)

        self._set_insert_mode(False)

    def _flush_pending_insert_j(self) -> None:
        """Insert delayed 'j' when jj timeout expires or another key is pressed."""
        if not self._insert_j_pending:
            return
        self._insert_j_pending = False
        self._insert_j_timer.stop()
        cursor = self._editor.textCursor()
        cursor.insertText("j")
        self._editor.setTextCursor(cursor)

    def _enter_visual_mode(self, mode: str) -> None:
        """Enter character, line, or block visual mode."""
        cursor = self._editor.textCursor()
        self._visual_mode = mode
        self._visual_anchor = cursor.position()
        self._pending_command = ""
        self._count_prefix = ""

        if mode == "line":
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            self._visual_anchor = cursor.position()
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
            self._editor.setTextCursor(cursor)
        self._emit_mode_changed()

    def _leave_visual_mode(self, *, store_last: bool) -> None:
        """Exit visual mode and optionally keep range for gv."""
        cursor = self._editor.textCursor()
        if store_last and cursor.hasSelection() and self._visual_mode is not None:
            self._last_visual_selection = (
                cursor.selectionStart(),
                cursor.selectionEnd(),
                self._visual_mode,
            )
        self._visual_mode = None
        self._visual_anchor = None
        self._emit_mode_changed()

    def _reselect_last_visual(self) -> None:
        """Reselect last visual area (gv)."""
        if self._last_visual_selection is None:
            return
        start, end, mode = self._last_visual_selection
        cursor = self._editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cursor)
        self._visual_mode = mode
        self._visual_anchor = start
        self._emit_mode_changed()

    def _handle_visual_keypress(self, event: QKeyEvent) -> bool:
        """Handle keybindings while in visual mode."""
        key_text = event.text()
        cursor = self._editor.textCursor()

        if event.key() == Qt.Key.Key_Escape:
            self._leave_visual_mode(store_last=True)
            return True

        if key_text == "o":
            self._swap_visual_ends()
            return True

        if key_text == "v" and self._visual_mode == "char":
            self._leave_visual_mode(store_last=True)
            return True

        if key_text == "V":
            self._visual_mode = "line"
            self._select_visual_lines()
            self._emit_mode_changed()
            return True

        if (
            event.key() == Qt.Key.Key_V
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self._visual_mode = "block"
            self._emit_mode_changed()
            return True

        if key_text == "d":
            self._yank_buffer = cursor.selectedText().replace("\u2029", "\n")
            cursor.removeSelectedText()
            self._editor.setTextCursor(cursor)
            self._leave_visual_mode(store_last=False)
            return True

        if key_text == "y":
            self._yank_buffer = cursor.selectedText().replace("\u2029", "\n")
            self._leave_visual_mode(store_last=True)
            return True

        if key_text == "c":
            self._yank_buffer = cursor.selectedText().replace("\u2029", "\n")
            cursor.removeSelectedText()
            self._editor.setTextCursor(cursor)
            self._leave_visual_mode(store_last=False)
            self._set_insert_mode(True)
            return True

        if key_text == "U":
            self._replace_selected_case("upper")
            return True

        if key_text == "u":
            self._replace_selected_case("lower")
            return True

        if key_text == ">":
            self._indent_selected_lines(right=True)
            return True

        if key_text == "<":
            self._indent_selected_lines(right=False)
            return True

        if self._visual_mode == "block" and key_text in {"I", "A"}:
            self._start_visual_block_insert(append=(key_text == "A"))
            return True

        count = self._consume_count() if self._count_prefix else 1
        if key_text.isdigit():
            if key_text == "0" and not self._count_prefix:
                self._visual_move("0", 1)
                return True
            self._count_prefix += key_text
            return True

        if key_text in {"h", "j", "k", "l", "w", "b", "e", "$", "^", "0", "G"}:
            self._visual_move(key_text, count)
            return True

        return True

    def _visual_move(self, key_text: str, count: int) -> None:
        """Move the cursor while keeping visual selection active."""
        cursor = self._editor.textCursor()
        operation_done = True

        if key_text == "h":
            cursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.KeepAnchor,
                count,
            )
        elif key_text == "j":
            for _ in range(count):
                cursor.movePosition(
                    QTextCursor.MoveOperation.Down,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        elif key_text == "k":
            for _ in range(count):
                cursor.movePosition(
                    QTextCursor.MoveOperation.Up,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        elif key_text == "l":
            cursor.movePosition(
                QTextCursor.MoveOperation.Right,
                QTextCursor.MoveMode.KeepAnchor,
                count,
            )
        elif key_text == "w":
            for _ in range(count):
                cursor.movePosition(
                    QTextCursor.MoveOperation.NextWord,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        elif key_text == "b":
            for _ in range(count):
                cursor.movePosition(
                    QTextCursor.MoveOperation.PreviousWord,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        elif key_text == "e":
            for _ in range(count):
                cursor.movePosition(
                    QTextCursor.MoveOperation.EndOfWord,
                    QTextCursor.MoveMode.KeepAnchor,
                )
        elif key_text == "$":
            cursor.movePosition(
                QTextCursor.MoveOperation.EndOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
        elif key_text == "^":
            start = cursor.anchor()
            cursor.setPosition(cursor.block().position())
            line_text = cursor.block().text()
            non_blank = len(line_text) - len(line_text.lstrip())
            cursor.setPosition(cursor.block().position() + non_blank)
            cursor.setPosition(start, QTextCursor.MoveMode.KeepAnchor)
            self._swap_visual_ends()
            return
        elif key_text == "0":
            cursor.movePosition(
                QTextCursor.MoveOperation.StartOfBlock,
                QTextCursor.MoveMode.KeepAnchor,
            )
        elif key_text == "G":
            cursor.movePosition(
                QTextCursor.MoveOperation.End,
                QTextCursor.MoveMode.KeepAnchor,
            )
        else:
            operation_done = False

        if not operation_done:
            return

        self._editor.setTextCursor(cursor)
        if self._visual_mode == "line":
            self._select_visual_lines()

    def _select_visual_lines(self) -> None:
        """Expand current visual selection to cover complete lines."""
        cursor = self._editor.textCursor()
        start = min(cursor.anchor(), cursor.position())
        end = max(cursor.anchor(), cursor.position())

        probe = self._editor.textCursor()
        probe.setPosition(start)
        probe.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        start_line = probe.position()

        probe.setPosition(end)
        probe.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        end_line = probe.position()

        new_cursor = self._editor.textCursor()
        new_cursor.setPosition(start_line)
        new_cursor.setPosition(end_line, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(new_cursor)

    def _swap_visual_ends(self) -> None:
        """Swap active and anchor ends in visual selection (o)."""
        cursor = self._editor.textCursor()
        if not cursor.hasSelection():
            return
        anchor = cursor.anchor()
        pos = cursor.position()
        cursor.setPosition(pos)
        cursor.setPosition(anchor, QTextCursor.MoveMode.KeepAnchor)
        self._editor.setTextCursor(cursor)

    def _replace_selected_case(self, case_mode: str) -> None:
        """Apply case transform to the current visual selection."""
        cursor = self._editor.textCursor()
        text = cursor.selectedText()
        if not text:
            return
        replacement = text.upper() if case_mode == "upper" else text.lower()
        cursor.insertText(replacement)
        self._editor.setTextCursor(cursor)
        self._leave_visual_mode(store_last=False)

    def _indent_selected_lines(self, *, right: bool) -> None:
        """Indent or outdent all lines touched by visual selection."""
        cursor = self._editor.textCursor()
        start = min(cursor.selectionStart(), cursor.selectionEnd())
        end = max(cursor.selectionStart(), cursor.selectionEnd())

        start_block = self._editor.document().findBlock(start)
        end_block = self._editor.document().findBlock(max(start, end - 1))
        unit = self._editor._indent_unit("")

        block = start_block
        while block.isValid() and block.blockNumber() <= end_block.blockNumber():
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

    def _visual_block_bounds(self) -> tuple[int, int, int, int] | None:
        """Return start/end lines and columns for block visual selection."""
        cursor = self._editor.textCursor()
        if not cursor.hasSelection():
            return None

        a = self._editor.document().findBlock(cursor.anchor())
        b = self._editor.document().findBlock(cursor.position())
        a_col = cursor.anchor() - a.position()
        b_col = cursor.position() - b.position()

        line_start = min(a.blockNumber(), b.blockNumber())
        line_end = max(a.blockNumber(), b.blockNumber())
        col_start = min(a_col, b_col)
        col_end = max(a_col, b_col)
        return line_start, line_end, col_start, col_end

    def _start_visual_block_insert(self, *, append: bool) -> None:
        """Start block insert/append from visual block selection (I/A)."""
        bounds = self._visual_block_bounds()
        if bounds is None:
            return
        line_start, line_end, col_start, col_end = bounds
        target_col = col_end + 1 if append else col_start

        points: list[int] = []
        for line in range(line_start, line_end + 1):
            block = self._editor.document().findBlockByNumber(line)
            if not block.isValid():
                continue
            points.append(block.position() + min(len(block.text()), target_col))

        if not points:
            return

        cursor = self._editor.textCursor()
        cursor.setPosition(points[0])
        self._editor.setTextCursor(cursor)
        self._leave_visual_mode(store_last=True)
        self._block_insert_start = points[0]
        self._block_insert_targets = points[1:]
        self._replace_mode = False
        self._set_insert_mode(True)

    def _apply_pending_block_insert(self) -> None:
        """Replicate inserted text to remaining lines after block I/A."""
        if self._block_insert_start is None or not self._block_insert_targets:
            self._block_insert_start = None
            self._block_insert_targets = []
            return

        cursor = self._editor.textCursor()
        end_pos = cursor.position()
        if end_pos < self._block_insert_start:
            self._block_insert_start = None
            self._block_insert_targets = []
            return

        doc_text = self._editor.toPlainText()
        inserted = doc_text[self._block_insert_start : end_pos]
        if not inserted:
            self._block_insert_start = None
            self._block_insert_targets = []
            return

        delta = len(inserted)
        extra_shift = 0
        for point in sorted(self._block_insert_targets):
            adjusted = (
                point + (delta if point > self._block_insert_start else 0) + extra_shift
            )
            insert_cursor = self._editor.textCursor()
            insert_cursor.setPosition(adjusted)
            insert_cursor.insertText(inserted)
            extra_shift += delta

        self._block_insert_start = None
        self._block_insert_targets = []

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
