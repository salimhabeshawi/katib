"""Application entry point for Katib."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from services.settings_service import SettingsService
from ui.main_window import MainWindow
from ui.theme import build_stylesheet


def main() -> int:
    """Run the Katib desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Katib")
    app.setOrganizationName("Katib")
    app.setStyleSheet(build_stylesheet())

    settings = SettingsService()
    window = MainWindow(settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
