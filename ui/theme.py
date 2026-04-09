"""Application theming."""

from __future__ import annotations


def build_stylesheet() -> str:
    """Return the global Qt stylesheet."""
    return """
    QWidget {
        background: #13161b;
        color: #e7e1d6;
        selection-background-color: #3f5368;
        selection-color: #f5efe4;
    }
    QMainWindow {
        background: #13161b;
    }
    QMenuBar, QMenu {
        background: #181c22;
        color: #e7e1d6;
        border: 1px solid #242b33;
    }
    QMenu::item:selected {
        background: #25303b;
    }
    QTreeWidget {
        background: #171b20;
        border: none;
        padding: 8px;
        font-size: 13px;
    }
    QTreeWidget::item {
        padding: 6px 8px;
        margin: 1px 0;
        border-radius: 6px;
    }
    QTreeWidget::item:selected {
        background: #263240;
    }
    QPlainTextEdit, QTextBrowser {
        background: #13161b;
        border: none;
        font-size: 15px;
    }
    QPlainTextEdit QScrollBar:vertical {
        background: #161b21;
        width: 12px;
        margin: 2px;
        border: 1px solid #2a323c;
        border-radius: 6px;
    }
    QPlainTextEdit QScrollBar::handle:vertical {
        background: #5a6674;
        min-height: 28px;
        border-radius: 5px;
    }
    QPlainTextEdit QScrollBar::handle:vertical:hover {
        background: #697686;
    }
    QPlainTextEdit QScrollBar::add-line:vertical,
    QPlainTextEdit QScrollBar::sub-line:vertical,
    QPlainTextEdit QScrollBar::add-page:vertical,
    QPlainTextEdit QScrollBar::sub-page:vertical {
        background: transparent;
        border: none;
        height: 0;
    }
    QPlainTextEdit QScrollBar:horizontal {
        background: #161b21;
        height: 12px;
        margin: 2px;
        border: 1px solid #2a323c;
        border-radius: 6px;
    }
    QPlainTextEdit QScrollBar::handle:horizontal {
        background: #5a6674;
        min-width: 28px;
        border-radius: 5px;
    }
    QPlainTextEdit QScrollBar::handle:horizontal:hover {
        background: #697686;
    }
    QPlainTextEdit QScrollBar::add-line:horizontal,
    QPlainTextEdit QScrollBar::sub-line:horizontal,
    QPlainTextEdit QScrollBar::add-page:horizontal,
    QPlainTextEdit QScrollBar::sub-page:horizontal {
        background: transparent;
        border: none;
        width: 0;
    }
    QTextBrowser {
        padding: 0;
    }
    QWidget#writingColumn {
        background: #15191e;
        border-radius: 16px;
    }
    QSplitter::handle {
        background: #1b2026;
        width: 1px;
    }
    QStatusBar {
        background: #171b20;
        color: #9ea9b6;
    }
    """
