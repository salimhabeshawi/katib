"""Markdown rendering service."""

from __future__ import annotations

import base64
import html
import re

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.style import Style
from pygments.token import Comment, Keyword, Literal, Name, Number, Operator, Punctuation, String, Text


class KatibCodeStyle(Style):
    """Monokai Pro Octagon-inspired Pygments style for preview mode."""

    background_color = "#221f22"
    default_style = ""
    styles = {
        Text: "#f8f8f2",
        Comment: "italic #727072",
        Keyword: "bold #ff6188",
        Name: "#78dce8",
        Name.Function: "#78dce8",
        Name.Class: "#78dce8",
        String: "#ffd866",
        Number: "#ab9df2",
        Literal: "#ab9df2",
        Operator: "#ff6188",
        Punctuation: "#f8f8f2",
    }


class MarkdownService:
    """Render Markdown content into styled HTML."""

    _FENCE_PATTERN = re.compile(
        r"(?P<fence>^[ \t]*(?:`{3,}|~{3,}))(?P<lang>[^\n`]*)\n(?P<code>.*?)(?:\n^[ \t]*(?:`{3,}|~{3,})[ \t]*$)",
        re.MULTILINE | re.DOTALL,
    )

    def __init__(self) -> None:
        """Initialize the renderer."""
        self._formatter = HtmlFormatter(style=KatibCodeStyle, nowrap=True)
        self._extensions = ["tables", "sane_lists"]

    def render(self, text: str, direction: str) -> str:
        """Render Markdown into a complete HTML document."""
        source = self._inject_code_placeholders(text)
        body = markdown.markdown(source, extensions=self._extensions)
        body = self._restore_code_blocks(body)
        safe_direction = "rtl" if direction == "rtl" else "ltr"
        text_align = "right" if safe_direction == "rtl" else "left"
        lang = "ar" if safe_direction == "rtl" else "en"
        code_css = self._formatter.get_style_defs(".preview-code")

        return f"""
<!DOCTYPE html>
<html lang="{lang}" dir="{safe_direction}">
  <head>
    <meta charset="utf-8">
    <style>
      :root {{
        color-scheme: dark;
      }}
      body {{
        margin: 0;
        padding: 36px 42px;
        background: #171a1f;
        color: #e6e1d8;
        direction: {safe_direction};
        text-align: {text_align};
        font-family: "Noto Naskh Arabic", "IBM Plex Sans", "Segoe UI", sans-serif;
        font-size: 16px;
        line-height: 1.8;
      }}
      h1, h2, h3, h4, h5, h6 {{
        color: #f3eee5;
        font-weight: 600;
        line-height: 1.3;
        margin: 1.4em 0 0.55em;
      }}
      p, ul, ol, pre, blockquote {{
        margin: 0 0 1em;
      }}
      code {{
        font-family: "JetBrains Mono", "Cascadia Mono", monospace;
        background: #22262d;
        border-radius: 6px;
        padding: 0.15em 0.35em;
      }}
      blockquote {{
        border-inline-start: 3px solid #58708a;
        color: #bcc7d4;
        padding-inline-start: 14px;
      }}
      a {{
        color: #8cb8e8;
      }}
      hr {{
        border: 0;
        border-top: 1px solid #2e3540;
        margin: 1.5em 0;
      }}
      .code-block {{
        margin: 0.25em 24px 1.2em;
        background: transparent;
        border: 1px solid #312c31;
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.22);
        overflow: hidden;
      }}
      .code-block-header {{
        background: transparent;
        padding: 10px 14px;
        margin: 0;
      }}
      .code-block-language {{
        color: #9b949b;
        font-family: "JetBrains Mono", "Cascadia Mono", monospace;
        font-size: 12px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}
      .code-block-copy {{
        background: #343034;
        border: 1px solid #423d42;
        border-radius: 8px;
        color: #f8f8f2;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        font-size: 12px;
        font-weight: 600;
        display: inline-block;
        padding: 4px 10px;
        text-decoration: none;
      }}
      .code-block-body {{
        background: #221f22;
        overflow-x: auto;
        padding: 0 16px 14px;
      }}
      .preview-code, .preview-code span {{
        font-family: "JetBrains Mono", "Cascadia Mono", monospace;
        font-size: 13px;
        line-height: 1.25;
      }}
      .preview-code {{
        background: #221f22;
        border: 0;
        margin: 0;
        padding: 0;
        padding-top: 0 !important;
        white-space: pre;
      }}
      {code_css}
      .preview-code, .preview-code * {{
        line-height: inherit !important;
      }}
      .preview-code > *:first-child {{
        margin-top: 0 !important;
        padding-top: 0 !important;
      }}
      .preview-code span {{
        background: transparent !important;
      }}
    </style>
  </head>
  <body>{body or f"<p>{html.escape('Nothing to preview yet.')}</p>"}</body>
</html>
"""

    def _inject_code_placeholders(self, text: str) -> str:
        """Replace fenced code blocks with HTML placeholders before Markdown conversion."""
        blocks: list[str] = []

        def replace(match: re.Match[str]) -> str:
            language = match.group("lang").strip().lower() or "text"
            code = match.group("code").strip("\n")
            blocks.append(self._render_code_block(code, language))
            return f"\n\nKATIB_CODE_BLOCK_{len(blocks) - 1}\n\n"

        self._rendered_blocks = blocks
        return self._FENCE_PATTERN.sub(replace, text)

    def _restore_code_blocks(self, body: str) -> str:
        """Replace placeholder paragraphs with rendered code block HTML."""
        for index, block_html in enumerate(getattr(self, "_rendered_blocks", [])):
            placeholder = f"<p>KATIB_CODE_BLOCK_{index}</p>"
            body = body.replace(placeholder, block_html)
        return body

    def _render_code_block(self, code: str, language: str) -> str:
        """Render a fenced code block with a copy button."""
        # Pygments may emit a leading newline for some inputs; trim it to avoid
        # a visual gap between the header and first rendered code line.
        highlighted = highlight(code, self._lexer_for_language(language), self._formatter).lstrip("\n")
        payload = base64.urlsafe_b64encode(code.encode("utf-8")).decode("ascii")
        label = html.escape(language if language != "text" else "plain text")
        return (
            '<div class="code-block">'
            '<div class="code-block-header">'
            '<table width="100%" cellspacing="0" cellpadding="0" border="0"><tr>'
            f'<td align="left" valign="middle"><span class="code-block-language">{label}</span></td>'
            f'<td align="right" valign="middle"><a class="code-block-copy" href="copy-code:{payload}">Copy</a></td>'
            '</tr></table>'
            '</div>'
            f'<div class="code-block-body"><pre class="preview-code">{highlighted}</pre></div>'
            "</div>"
        )

    def _lexer_for_language(self, language: str):
        """Return the best lexer for a requested language name."""
        try:
            return get_lexer_by_name(language)
        except Exception:
            return TextLexer()
