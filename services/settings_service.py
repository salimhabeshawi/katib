"""Local JSON-backed persistence service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths

from core.models import AppState


class SettingsService:
    """Persist small application settings as JSON."""

    def __init__(self) -> None:
        """Initialize the settings service."""
        self._settings_path = self._resolve_settings_path()

    def load_state(self) -> AppState:
        """Load the persisted application state."""
        data = self._read_payload()
        return AppState(
            last_project=data.get("last_project"),
            last_file=data.get("last_file"),
            sidebar_visible=bool(data.get("sidebar_visible", True)),
            preview_visible=bool(data.get("preview_visible", False)),
            global_direction=data.get("global_direction", "rtl"),
        )

    def save_state(self, state: AppState) -> None:
        """Persist the application state."""
        payload = {
            "last_project": state.last_project,
            "last_file": state.last_file,
            "sidebar_visible": state.sidebar_visible,
            "preview_visible": state.preview_visible,
            "global_direction": state.global_direction,
            "document_directions": self.load_document_directions(),
        }
        self._write_payload(payload)

    def load_document_directions(self) -> dict[str, str]:
        """Load per-document text directions."""
        data = self._read_payload()
        raw = data.get("document_directions", {})
        if not isinstance(raw, dict):
            return {}
        return {
            str(key): "rtl" if value == "rtl" else "ltr"
            for key, value in raw.items()
        }

    def save_document_directions(self, mapping: dict[str, str]) -> None:
        """Persist per-document text directions."""
        data = self._read_payload()
        data["document_directions"] = {
            key: "rtl" if value == "rtl" else "ltr"
            for key, value in mapping.items()
        }
        self._write_payload(data)

    def _resolve_settings_path(self) -> Path:
        """Resolve the local settings file path."""
        base_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        settings_dir = Path(base_dir) / "katib"
        settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir / "settings.json"

    def _read_payload(self) -> dict[str, Any]:
        """Read the JSON payload from disk."""
        if not self._settings_path.exists():
            return {}

        try:
            with self._settings_path.open("r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            return {}

        return data if isinstance(data, dict) else {}

    def _write_payload(self, payload: dict[str, Any]) -> None:
        """Write the JSON payload to disk."""
        with self._settings_path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2, ensure_ascii=False)
