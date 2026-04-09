"""Preview widgets for rendered Markdown."""

from __future__ import annotations

import base64

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QTextBrowser


class PreviewBrowser(QTextBrowser):
    """Markdown preview browser with in-document code copy support."""

    def __init__(self, parent: object | None = None) -> None:
        """Initialize the preview browser."""
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(True)
        self.anchorClicked.connect(self._handle_anchor_clicked)

    def _handle_anchor_clicked(self, url: QUrl) -> None:
        """Handle internal preview actions such as copying code blocks."""
        if url.scheme() == "copy-code":
            encoded = url.path().lstrip("/")
            try:
                text = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
            except Exception:
                return
            QGuiApplication.clipboard().setText(text)
            return

        self.setSource(url)
