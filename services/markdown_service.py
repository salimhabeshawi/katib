"""Markdown rendering and PDF export service."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_pdf import MarkdownPdf, Section
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.style import Style
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
)


class MonokaiProStyle(Style):
    """Monokai Pro Octagon-inspired Pygments style."""

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


@dataclass(frozen=True)
class RenderedDocument:
    """Rendered output container for preview and export targets."""

    body_html: str
    full_html: str
    direction: str


class MarkdownService:
    """Render Markdown content and export it to PDF."""

    _FENCED_CODE_RE = re.compile(
        r"(^|\n)(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)\n"
        r"(?P<code>.*?)(?:\n(?P=indent)(?P=fence)[ \t]*)(?=\n|$)",
        re.DOTALL,
    )

    def __init__(self) -> None:
        """Initialize markdown-it parser with GFM-like features."""
        # gfm-like enables GFM-oriented behavior (tables/strikethrough/linkify).
        # tasklists_plugin adds [ ]/[x] checklist rendering.
        self._code_formatter = HtmlFormatter(
            style=MonokaiProStyle,
            nowrap=True,
            noclasses=True,
        )
        self._md = (
            MarkdownIt(
                "gfm-like",
                {
                    "linkify": True,
                    "typographer": True,
                    "highlight": self._highlight_fence,
                },
            )
            .enable("table")
            .use(tasklists_plugin, enabled=True)
        )

    def render(self, text: str, direction: str) -> str:
        """Render Markdown into a complete HTML document for in-app preview."""
        return self.render_document(text, direction).full_html

    def render_document(self, text: str, direction: str) -> RenderedDocument:
        """Render Markdown into reusable HTML output."""
        safe_direction = "rtl" if direction == "rtl" else "ltr"
        text_align = "right" if safe_direction == "rtl" else "left"
        lang = "ar" if safe_direction == "rtl" else "en"
        body_html = self._md.render(text).strip()
        if not body_html:
            empty_message = (
                "لا يوجد محتوى للمعاينة بعد."
                if safe_direction == "rtl"
                else "Nothing to preview yet."
            )
            body_html = f"<p>{html.escape(empty_message)}</p>"

        full_html = f"""
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
        font-family: "Noto Kufi Arabic", "IBM Plex Sans", "Segoe UI", sans-serif;
        font-size: 16px;
        line-height: 1.8;
      }}
      h1, h2, h3, h4, h5, h6 {{
        color: #f3eee5;
        font-weight: 600;
        line-height: 1.3;
        margin: 1.4em 0 0.55em;
      }}
      p, ul, ol, pre, blockquote, table {{
        margin: 0 0 1em;
      }}
      code {{
        font-family: "JetBrains Mono", "Cascadia Mono", monospace;
        background: #22262d;
        border-radius: 6px;
        padding: 0.15em 0.35em;
      }}
      pre {{
        background: #221f22;
        border: 1px solid #312c31;
        border-radius: 12px;
        overflow-x: auto;
        padding: 14px 16px;
      }}
      pre code {{
        background: transparent;
        padding: 0;
      }}
      blockquote {{
        border-inline-start: 3px solid #58708a;
        color: #a9b5c3;
        font-style: italic;
        margin-inline-start: 1.25em;
        padding-inline-start: 1em;
      }}
      blockquote > :first-child {{
        margin-top: 0;
      }}
      blockquote > :last-child {{
        margin-bottom: 0;
      }}
      table {{
        border-collapse: collapse;
        width: 100%;
      }}
      th, td {{
        border: 1px solid #2e3540;
        padding: 8px 10px;
        text-align: {text_align};
      }}
      th {{
        background: #20252d;
        color: #efe8dc;
      }}
      li.task-list-item {{
        list-style: none;
      }}
      li.task-list-item input[type="checkbox"] {{
        margin-inline-end: 0.5em;
      }}
      a {{
        color: #8cb8e8;
      }}
      hr {{
        border: 0;
        border-top: 1px solid #2e3540;
        margin: 1.5em 0;
      }}
    </style>
  </head>
  <body>{body_html}</body>
</html>
"""
        return RenderedDocument(
            body_html=body_html,
            full_html=full_html,
            direction=safe_direction,
        )

    def _highlight_fence(
        self,
        code: str,
        lang: str | None = None,
        _attrs: str = "",
    ) -> str:
        """Highlight fenced code content using Pygments for preview mode."""
        lexer_name = (lang or "").strip().lower()
        try:
            lexer = get_lexer_by_name(lexer_name) if lexer_name else TextLexer()
        except Exception:
            lexer = TextLexer()
        return highlight(code, lexer, self._code_formatter)

    def export_pdf(
        self,
        text: str,
        output_path: Path,
        *,
        source_root: Path,
        direction: str,
        title: str,
    ) -> None:
        """Export Markdown text to a high-quality PDF with TOC and links."""
        safe_direction = "rtl" if direction == "rtl" else "ltr"
        highlighted_text = self._inject_pdf_syntax_highlight(text)
        pdf = self._build_pdf_document(
            highlighted_text,
            source_root=source_root,
            direction=safe_direction,
            title=title,
            enable_toc=True,
        )
        try:
            pdf.save(str(output_path))
        except Exception as exc:
            # markdown-pdf can fail when the first heading level is not H1.
            # Retry without TOC/bookmarks so export still succeeds.
            if "hierarchy level of item 0 must be 1" not in str(exc):
                raise
            fallback_pdf = self._build_pdf_document(
                highlighted_text,
                source_root=source_root,
                direction=safe_direction,
                title=title,
                enable_toc=False,
            )
            fallback_pdf.save(str(output_path))

    def _build_pdf_document(
        self,
        markdown_text: str,
        *,
        source_root: Path,
        direction: str,
        title: str,
        enable_toc: bool,
    ) -> MarkdownPdf:
        """Create a configured MarkdownPdf instance with one document section."""
        pdf = MarkdownPdf(toc_level=6, optimize=True)
        # Keep markdown parsing active so heading syntax renders as headings in PDF.
        # Raw HTML is enabled only for injected syntax-highlighted blocks.
        pdf.m_d.options["html"] = True
        pdf.meta["title"] = title
        section = Section(
            markdown_text,
            root=str(source_root),
            toc=enable_toc,
        )
        pdf.add_section(section, user_css=self._pdf_css(direction))
        return pdf

    def _inject_pdf_syntax_highlight(self, text: str) -> str:
        """Replace fenced code blocks with highlighted HTML for PDF export."""

        def replace(match: re.Match[str]) -> str:
            info = match.group("info").strip()
            lang = info.split(maxsplit=1)[0] if info else ""
            code = match.group("code").rstrip("\n")
            highlighted = self._highlight_fence(code, lang)
            indent = match.group("indent")
            prefix = match.group(1)
            return (
                f'{prefix}{indent}<div class="pdf-code-block">'
                f"<pre><code>{highlighted}</code></pre>"
                "</div>"
            )

        return self._FENCED_CODE_RE.sub(replace, text)

    def _pdf_css(self, direction: str) -> str:
        """Return PDF CSS tuned to match preview typography."""
        text_align = "right" if direction == "rtl" else "left"
        quote_side = "right" if direction == "rtl" else "left"
        opposite_quote_side = "left" if direction == "rtl" else "right"
        list_padding_side = "right" if direction == "rtl" else "left"
        list_padding_opposite = "left" if direction == "rtl" else "right"
        return f"""
          @font-face {{
            font-family: 'KatibArabic';
            src:
              local('Noto Kufi Arabic'),
              local('NotoKufiArabic'),
              url('file:///usr/share/fonts/truetype/noto/NotoKufiArabic-Regular.ttf') format('truetype'),
              url('file:///usr/share/fonts/truetype/noto/NotoKufiArabic-VariableFont_wght.ttf') format('truetype');
            font-style: normal;
            font-weight: 400;
          }}

            html, body {{
            direction: {direction} !important;
            }}
          body, .markdown-body, .katib-pdf-root {{
            direction: {direction} !important;
            text-align: {text_align} !important;
            unicode-bidi: plaintext !important;
            font-family: 'KatibArabic', 'Noto Kufi Arabic', 'IBM Plex Sans', 'Segoe UI', sans-serif !important;
                font-size: 12pt;
                line-height: 1.7;
            }}
          .markdown-body *, .katib-pdf-root * {{
            direction: inherit;
            text-align: inherit;
            font-family: 'KatibArabic', 'Noto Kufi Arabic', 'IBM Plex Sans', 'Segoe UI', sans-serif !important;
          }}
            blockquote {{
                border-{quote_side}: 3px solid #6d7f93;
                color: #4f5c6a;
                font-style: italic;
                margin-{quote_side}: 1.5em;
                padding-{quote_side}: 0.9em;
                margin-{opposite_quote_side}: 0;
                padding-{opposite_quote_side}: 0;
            }}
            ul, ol {{
                padding-{list_padding_side}: 1.6em;
                padding-{list_padding_opposite}: 0;
            }}
            pre {{
                background: #221f22;
                border: 1px solid #312c31;
                border-radius: 6px;
                padding: 10px;
                white-space: pre;
                color: #f8f8f2;
            text-align: left !important;
            }}
          code, pre code {{
                font-family: 'JetBrains Mono', 'Cascadia Mono', monospace;
                background: transparent;
                padding: 0;
                color: inherit;
            }}
            p code, li code, td code, th code, blockquote code {{
                background: #edf1f5;
                border-radius: 4px;
                padding: 0.1em 0.3em;
            }}
            .pdf-code-block {{
                margin: 0 0 1em;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
            }}
            th, td {{
                border: 1px solid #c9d1da;
                padding: 6px 8px;
                text-align: {text_align};
            }}
            th {{
                background: #edf1f5;
            }}
            a {{
                color: #1d5fa8;
                text-decoration: underline;
            }}
        """
