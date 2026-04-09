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
    QTextBrowser {
        padding: 0;
    }
    QWidget#writingColumn {
        background: #15191e;
        border-radius: 16px;
    }
    QPushButton#directionToggle {
        background: #222932;
        border: 1px solid #303a46;
        border-radius: 8px;
        color: #e7e1d6;
        font-weight: 600;
        min-width: 56px;
        padding: 6px 10px;
    }
    QPushButton#directionToggle:hover {
        background: #2a3440;
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
