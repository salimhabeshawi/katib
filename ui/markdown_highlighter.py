"""Live Markdown syntax highlighting for the writing editor."""

from __future__ import annotations

import re

from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from pygments import lex
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.token import (
    Comment,
    Keyword,
    Literal,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Token,
)


class MarkdownHighlighter(QSyntaxHighlighter):
    """Render Markdown with subtle live styling while editing."""

    _PLAIN_FENCE_STATE = 1000

    def __init__(self, document: QTextDocument) -> None:
        """Initialize the Markdown highlighter."""
        super().__init__(document)
        self._formats = self._build_formats()
        self._state_to_language: dict[int, str] = {self._PLAIN_FENCE_STATE: "text"}
        self._language_to_state: dict[str, int] = {"text": self._PLAIN_FENCE_STATE}

    def highlightBlock(self, text: str) -> None:
        """Apply Markdown-aware formatting to a text block."""
        previous_state = self.previousBlockState()
        if previous_state >= self._PLAIN_FENCE_STATE:
            if self._is_fence_line(text):
                self._highlight_fence(text)
                self.setCurrentBlockState(-1)
            else:
                self._highlight_code_block(
                    text, self._language_for_state(previous_state)
                )
                self.setCurrentBlockState(previous_state)
            return

        self.setCurrentBlockState(-1)

        if self._is_fence_line(text):
            language = self._language_from_fence(text)
            self._highlight_fence(text)
            self.setCurrentBlockState(self._state_for_language(language))
            return

        self._highlight_heading(text)
        self._highlight_blockquote(text)
        self._highlight_list_marker(text)
        self._highlight_inline_code(text)
        self._highlight_emphasis(text)
        self._highlight_links(text)

    def _highlight_fence(self, text: str) -> None:
        """Highlight a fenced code delimiter line."""
        if not text:
            return
        self.setFormat(0, len(text), self._formats["code_block"])
        match = re.match(r"^(\s*)(`{3,}|~{3,})([^\s`~]+)?(.*)$", text)
        if not match:
            return
        marker_start = len(match.group(1))
        self.setFormat(marker_start, len(match.group(2)), self._formats["syntax"])
        if match.group(3):
            self.setFormat(
                match.start(3), len(match.group(3)), self._formats["code_language"]
            )
        if match.group(4):
            self.setFormat(match.start(4), len(match.group(4)), self._formats["syntax"])

    def _highlight_code_block(self, text: str, language: str) -> None:
        """Highlight a fenced code block line using the selected lexer."""
        if not text:
            return
        self.setFormat(0, len(text), self._formats["code_block"])
        cursor = 0
        for token_type, value in lex(text, self._lexer_for_language(language)):
            if not value:
                continue
            length = len(value)
            text_format = self._format_for_token(token_type)
            if text_format is not None:
                self.setFormat(cursor, length, text_format)
            cursor += length

    def _highlight_heading(self, text: str) -> None:
        """Highlight Markdown headings."""
        match = re.match(r"^(\s{0,3})(#{1,6})(\s+)(.*)$", text)
        if not match:
            return

        level = len(match.group(2))
        content_start = len(match.group(1)) + len(match.group(2)) + len(match.group(3))
        content_length = len(text) - content_start

        self.setFormat(
            len(match.group(1)), len(match.group(2)), self._formats["syntax"]
        )
        self.setFormat(
            len(match.group(1)) + len(match.group(2)),
            len(match.group(3)),
            self._formats["syntax"],
        )
        if content_length > 0:
            self.setFormat(
                content_start, content_length, self._formats[f"heading_{level}"]
            )

    def _highlight_blockquote(self, text: str) -> None:
        """Highlight blockquote markers and content."""
        match = re.match(r"^(\s*)(>+)(\s?)(.*)$", text)
        if not match:
            return

        marker_start = len(match.group(1))
        self.setFormat(marker_start, len(match.group(2)), self._formats["syntax"])
        if match.group(3):
            self.setFormat(
                marker_start + len(match.group(2)),
                len(match.group(3)),
                self._formats["syntax"],
            )
        content_start = marker_start + len(match.group(2)) + len(match.group(3))
        if content_start < len(text):
            self.setFormat(
                content_start, len(text) - content_start, self._formats["blockquote"]
            )

    def _highlight_list_marker(self, text: str) -> None:
        """Highlight ordered and unordered list markers."""
        match = re.match(r"^(\s*)([-+*]|\d+[.)])(\s+)(.*)$", text)
        if not match:
            return

        marker_start = len(match.group(1))
        self.setFormat(marker_start, len(match.group(2)), self._formats["syntax"])
        self.setFormat(
            marker_start + len(match.group(2)),
            len(match.group(3)),
            self._formats["syntax"],
        )

    def _highlight_inline_code(self, text: str) -> None:
        """Highlight inline code spans."""
        for match in re.finditer(r"(`+)([^`]+?)(\1)", text):
            start = match.start()
            opening = len(match.group(1))
            content_start = start + opening
            content_length = len(match.group(2))
            closing_start = content_start + content_length

            self.setFormat(start, opening, self._formats["syntax"])
            self.setFormat(content_start, content_length, self._formats["inline_code"])
            self.setFormat(closing_start, opening, self._formats["syntax"])

    def _highlight_emphasis(self, text: str) -> None:
        """Highlight emphasis and strong emphasis."""
        strong_emphasis_patterns = [
            r"(?<!\*)\*\*\*(?!\*)(?=\S)(.+?)(?<=\S)(?<!\*)\*\*\*(?!\*)",
            r"(?<!_)___(?!_)(?=\S)(.+?)(?<=\S)(?<!_)___(?!_)",
        ]
        for pattern in strong_emphasis_patterns:
            for match in re.finditer(pattern, text):
                marker_length = 3
                content_start = match.start() + marker_length
                content_length = len(match.group(1))
                closing_start = content_start + content_length

                self.setFormat(match.start(), marker_length, self._formats["syntax"])
                self.setFormat(
                    content_start, content_length, self._formats["strong_emphasis"]
                )
                self.setFormat(closing_start, marker_length, self._formats["syntax"])

        strong_patterns = [
            r"(?<!\*)\*\*(?!\*)(?=\S)(.+?)(?<=\S)(?<!\*)\*\*(?!\*)",
            r"(?<!_)__(?!_)(?=\S)(.+?)(?<=\S)(?<!_)__(?!_)",
        ]
        for pattern in strong_patterns:
            for match in re.finditer(pattern, text):
                marker_length = 2
                content_start = match.start() + marker_length
                content_length = len(match.group(1))
                closing_start = content_start + content_length

                self.setFormat(match.start(), marker_length, self._formats["syntax"])
                self.setFormat(content_start, content_length, self._formats["strong"])
                self.setFormat(closing_start, marker_length, self._formats["syntax"])

        emphasis_patterns = [
            r"(?<!\*)\*(?!\*)(?=\S)(.+?)(?<=\S)(?<!\*)\*(?!\*)",
            r"(?<!_)_(?!_)(?=\S)(.+?)(?<=\S)(?<!_)_(?!_)",
        ]
        for pattern in emphasis_patterns:
            for match in re.finditer(pattern, text):
                marker_length = 1
                content_start = match.start() + marker_length
                content_length = len(match.group(1))
                closing_start = content_start + content_length

                self.setFormat(match.start(), marker_length, self._formats["syntax"])
                self.setFormat(content_start, content_length, self._formats["emphasis"])
                self.setFormat(closing_start, marker_length, self._formats["syntax"])

    def _highlight_links(self, text: str) -> None:
        """Highlight links with subdued syntax and readable labels."""
        for match in re.finditer(r"(!?\[)([^\]]+)(\]\()([^)]+)(\))", text):
            self.setFormat(match.start(1), len(match.group(1)), self._formats["syntax"])
            self.setFormat(
                match.start(2), len(match.group(2)), self._formats["link_text"]
            )
            self.setFormat(match.start(3), len(match.group(3)), self._formats["syntax"])
            self.setFormat(
                match.start(4), len(match.group(4)), self._formats["link_url"]
            )
            self.setFormat(match.start(5), len(match.group(5)), self._formats["syntax"])

    def _build_formats(self) -> dict[str, QTextCharFormat]:
        """Build all text formats used by the highlighter."""
        return {
            "syntax": self._format(foreground="#586270"),
            "blockquote": self._format(foreground="#b8c5d4", italic=True),
            "inline_code": self._format(
                foreground="#d9c6a2",
                background="#1e252d",
                family="JetBrains Mono",
            ),
            "code_block": self._format(
                foreground="#f8f8f2",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "code_language": self._format(
                foreground="#586270",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "code_keyword": self._format(
                foreground="#ff6188",
                background="#221f22",
                family="JetBrains Mono",
                weight=QFont.Weight.DemiBold,
            ),
            "code_string": self._format(
                foreground="#ffd866",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "code_comment": self._format(
                foreground="#727072",
                background="#221f22",
                family="JetBrains Mono",
                italic=True,
            ),
            "code_name": self._format(
                foreground="#78dce8",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "code_literal": self._format(
                foreground="#ab9df2",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "code_operator": self._format(
                foreground="#ff6188",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "code_punctuation": self._format(
                foreground="#f8f8f2",
                background="#221f22",
                family="JetBrains Mono",
            ),
            "strong_emphasis": self._format(weight=QFont.Weight.Bold, italic=True),
            "strong": self._format(weight=QFont.Weight.Bold),
            "emphasis": self._format(italic=True),
            "link_text": self._format(foreground="#9bc7f0", underline=True),
            "link_url": self._format(foreground="#7088a0"),
            "heading_1": self._format(
                foreground="#f2ede4", weight=QFont.Weight.Bold, point_delta=8
            ),
            "heading_2": self._format(
                foreground="#efe9dd", weight=QFont.Weight.Bold, point_delta=6
            ),
            "heading_3": self._format(
                foreground="#ebe4d9", weight=QFont.Weight.DemiBold, point_delta=4
            ),
            "heading_4": self._format(
                foreground="#e7dfd2", weight=QFont.Weight.DemiBold, point_delta=3
            ),
            "heading_5": self._format(
                foreground="#e2dacd", weight=QFont.Weight.DemiBold, point_delta=2
            ),
            "heading_6": self._format(
                foreground="#ddd4c7", weight=QFont.Weight.Medium, point_delta=1
            ),
        }

    def _format(
        self,
        *,
        foreground: str | None = None,
        background: str | None = None,
        italic: bool = False,
        underline: bool = False,
        weight: QFont.Weight | None = None,
        family: str | None = None,
        point_delta: int = 0,
    ) -> QTextCharFormat:
        """Create a configured text format."""
        text_format = QTextCharFormat()
        if foreground:
            text_format.setForeground(QColor(foreground))
        if background:
            text_format.setBackground(QColor(background))
        if italic:
            text_format.setFontItalic(True)
        if underline:
            text_format.setFontUnderline(True)
        if weight is not None:
            text_format.setFontWeight(weight)
        if family:
            text_format.setFontFamilies(["JetBrains Mono", "Noto Kufi Arabic"])
        if point_delta:
            text_format.setFontPointSize(12 + point_delta)
        return text_format

    def _is_fence_line(self, text: str) -> bool:
        """Return whether the line is a fenced code delimiter."""
        return bool(re.match(r"^\s*(`{3,}|~{3,})", text))

    def _language_from_fence(self, text: str) -> str:
        """Extract the language name from a fenced code marker."""
        match = re.match(r"^\s*(?:`{3,}|~{3,})\s*([^\s`~]+)?", text)
        if not match or not match.group(1):
            return "text"
        return match.group(1).lower()

    def _state_for_language(self, language: str) -> int:
        """Return or create a block-state id for a language."""
        normalized = language.lower() or "text"
        if normalized not in self._language_to_state:
            state = self._PLAIN_FENCE_STATE + len(self._language_to_state)
            self._language_to_state[normalized] = state
            self._state_to_language[state] = normalized
        return self._language_to_state[normalized]

    def _language_for_state(self, state: int) -> str:
        """Return the language mapped to a block-state id."""
        return self._state_to_language.get(state, "text")

    def _lexer_for_language(self, language: str):
        """Return a Pygments lexer for the requested language."""
        try:
            return get_lexer_by_name(language)
        except Exception:
            return TextLexer()

    def language_for_block_state(self, state: int) -> str | None:
        """Return the fenced-code language for a block state, if any."""
        if state < self._PLAIN_FENCE_STATE:
            return None
        return self._language_for_state(state)

    def _format_for_token(self, token_type: Token) -> QTextCharFormat | None:
        """Resolve a Qt format for a Pygments token."""
        token_map = {
            Keyword: self._formats["code_keyword"],
            String: self._formats["code_string"],
            Comment: self._formats["code_comment"],
            Name: self._formats["code_name"],
            Number: self._formats["code_literal"],
            Literal: self._formats["code_literal"],
            Operator: self._formats["code_operator"],
            Punctuation: self._formats["code_punctuation"],
            Text: self._formats["code_block"],
        }
        current = token_type
        while current is not None:
            if current in token_map:
                return token_map[current]
            current = current.parent
        return self._formats["code_block"]
