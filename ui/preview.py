"""Preview widgets for rendered Markdown."""

from __future__ import annotations

import base64

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView


class PreviewPage(QWebEnginePage):
    """Custom web page to intercept preview-specific links."""

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        """Handle copy links internally and open external links in system browser."""
        if url.scheme() == "copy-code":
            encoded = url.path().lstrip("/")
            try:
                text = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
            except Exception:
                return False
            QGuiApplication.clipboard().setText(text)
            return False

        if url.scheme() in {"http", "https", "mailto"}:
            QDesktopServices.openUrl(url)
            return False

        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class PreviewBrowser(QWebEngineView):
    """Markdown preview browser backed by Qt WebEngine."""

    def __init__(self, parent: object | None = None) -> None:
        """Initialize the preview browser."""
        super().__init__(parent)
        self.setPage(PreviewPage(self))

    def clear(self) -> None:
        """Clear preview content."""
        self.setHtml("")
