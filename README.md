# Katib

Katib is a minimal PySide6 Markdown writing application focused on calm, distraction-free writing with strong Arabic and RTL support.

## Features

- Project-based workflow using folders
- Markdown-only file explorer
- Auto-save editor
- Edit and preview modes
- Per-document and global RTL/LTR control
- Session persistence for the last project and file

## Project Structure

```text
app/
core/
services/
ui/
```

## `uv` Commands

```bash
uv venv
uv sync
uv run katib
```

## Optional first-time project bootstrap

```bash
uv init --package .
uv add PySide6 markdown
```
