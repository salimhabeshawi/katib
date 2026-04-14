# Katib

> A focused desktop Markdown writing app built with Python and PySide6, designed for fast writing workflows, Arabic-first typography, RTL/LTR flexibility, and local PDF export.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/PySide6-Qt6-green.svg)](https://www.qt.io/qt-for-python)
[![MarkdownIt](https://img.shields.io/badge/markdown--it-py-renderer-orange.svg)](https://markdown-it-py.readthedocs.io/)
[![PDF Export](https://img.shields.io/badge/markdown--pdf-export-red.svg)](https://pypi.org/project/markdown-pdf/)

## Overview

Katib is a local-first writing environment for Markdown documents. It combines a clean editor, live preview, file tree navigation, Vim-style modal editing, and export to PDF in one lightweight desktop app.

It is built for writers who switch between English and Arabic, and need direction-aware editing and rendering with minimal friction.

## Screenshots

Place your screenshots in `docs/screenshots/` using these names:

- `docs/screenshots/english.png`
- `docs/screenshots/arabic.png`

English UI:

![Katib English UI](docs/screenshots/english.png)

Arabic UI (RTL):

![Katib Arabic UI RTL](docs/screenshots/arabic.png)

## Key Highlights

- Calm, distraction-free writing column
- Project-based Markdown workflow
- Live preview with markdown-it rendering
- Arabic + RTL/LTR support across editor and preview
- Vim mode with modal status, normal/insert/visual modes
- Local PDF export (no cloud dependency)
- Auto-save and session restore

## Features

### Writing Experience

| Feature               | Description                                                                   |
| --------------------- | ----------------------------------------------------------------------------- |
| Smart Markdown typing | Auto-pairing for markers and symbols, plus fence/bracket enter splitting      |
| List ergonomics       | Dash list indentation helpers and single-backspace list exit                  |
| Line numbers          | Gutter with active-line highlighting and RTL-aware placement                  |
| Vim mode              | Normal/Insert modes, visual modes, core motions/operators, `jj` insert escape |
| Direction control     | Toggle RTL/LTR per document with stored preference                            |

### Preview and Export

| Feature             | Description                                                                 |
| ------------------- | --------------------------------------------------------------------------- |
| Live preview        | Immediate HTML preview from current editor text                             |
| Markdown engine     | `markdown-it-py` with table and task list support                           |
| Syntax highlighting | Pygments-based fenced code highlighting                                     |
| PDF export          | Export current document to PDF with typography and direction styling        |
| Arabic support      | Arabic-friendly font stack (Noto Kufi Arabic) in editor and rendered output |

## Technology Stack

### Core

- Python 3.11+
- PySide6 (Qt6)
- markdown-it-py
- mdit-py-plugins
- markdown-pdf
- Pygments
- linkify-it-py

### Architecture

- Layered modules: `core/`, `services/`, `ui/`, `app/`
- Service-based rendering/export pipeline (`MarkdownService`)
- Stateful desktop workflow with settings/session persistence
- Signal-slot UI updates for preview/status/file actions

## Installation

## Linux AppImage (Recommended for Most Users)

Use this if you just want to install and run Katib.

### Step 1: Download

1. Open the latest GitHub Release.
2. Download `Katib-x86_64.AppImage`.

### Step 2: Move It to an Apps Folder

```bash
mkdir -p "$HOME/Applications/Katib"
mv "$HOME/Downloads/Katib-x86_64.AppImage" "$HOME/Applications/Katib/"
chmod +x "$HOME/Applications/Katib/Katib-x86_64.AppImage"
```

### Step 3: Run It Once

```bash
"$HOME/Applications/Katib/Katib-x86_64.AppImage"
```

### Step 4: Create a Desktop Shortcut (Debian/Ubuntu/Linux Mint/Pop!\_OS)

```bash
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/katib-appimage.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Katib
Comment=Markdown writing app
Exec=$HOME/Applications/Katib/Katib-x86_64.AppImage
Icon=accessories-text-editor
Terminal=false
Categories=Office;TextEditor;Utility;
StartupNotify=true
EOF
update-desktop-database "$HOME/.local/share/applications" || true
```

### Step 5: Create a Desktop Shortcut (Arch/Manjaro/EndeavourOS)

```bash
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/katib-appimage.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Katib
Comment=Markdown writing app
Exec=$HOME/Applications/Katib/Katib-x86_64.AppImage
Icon=accessories-text-editor
Terminal=false
Categories=Office;TextEditor;Utility;
StartupNotify=true
EOF
update-desktop-database "$HOME/.local/share/applications" || true
```

After this, search for `Katib` in your app launcher and pin it to favorites/dock.

### Optional: Use a Custom Icon in the Launcher

If you downloaded `katib.png`, use this instead:

```bash
mkdir -p "$HOME/.local/share/icons"
cp "$HOME/Downloads/katib.png" "$HOME/.local/share/icons/katib.png"
sed -i 's|^Icon=.*|Icon='$HOME'/.local/share/icons/katib.png|' "$HOME/.local/share/applications/katib-appimage.desktop"
```

## Run From Source (For Developers)

### Prerequisites

- Python 3.11+
- `uv`

### Quick Start

For HTTPS:

```bash
git clone https://github.com/salimhabeshawi/katib.git
cd katib
```

For SSH:

```bash
git clone git@github.com:salimhabeshawi/katib.git
cd katib
```

Create environment and install dependencies:

```bash
uv venv
uv sync
```

Run:

```bash
uv run katib
```

## Project Structure

```text
katib/
├── app/
│   ├── __init__.py
│   └── main.py
├── core/
│   ├── __init__.py
│   ├── models.py
│   └── project_manager.py
├── docs/
│   └── screenshots/
│       ├── arabic.png
│       └── english.png
├── services/
│   ├── __init__.py
│   ├── markdown_service.py
│   └── settings_service.py
├── ui/
│   ├── __init__.py
│   ├── editor.py
│   ├── file_tree.py
│   ├── main_window.py
│   ├── markdown_highlighter.py
│   ├── preview.py
│   ├── theme.py
│   └── vim_mode.py
├── pyproject.toml
├── uv.lock
└── README.md
```

## Usage Notes

- Open or create a project folder, then work with `.md` files from the sidebar.
- Use `Ctrl+P` to toggle preview.
- Use `Ctrl+Alt+D` to toggle RTL/LTR.
- Use `Ctrl+Alt+V` to toggle Vim mode.
- Export current document with `Ctrl+Shift+E`.

## Development

Run checks and app locally:

```bash
uv run katib
```

If you modify dependencies:

```bash
uv sync
```

## Contributing

Contributions are welcome via pull requests. Keep changes focused, test manually in both LTR and RTL flows, and update this README when behavior changes.
