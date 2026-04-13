# Windows Packaging Guide for Katib

This guide explains how to package Katib into:

1. A Windows desktop executable (`Katib.exe`)
2. A standard Windows installer (`Katib-Setup-<version>.exe`)

The process uses:

- PyInstaller: builds the application bundle
- Inno Setup: builds the installation wizard/uninstaller

## Goals

After following this guide, users should get a normal Windows app experience:

- Double-click installer wizard
- App installed under Program Files
- Start Menu shortcut (optional desktop shortcut)
- Clean uninstall entry in Windows Apps settings
- Custom app icon in installer and app shortcuts

## Important Notes

- Build Windows binaries on Windows (local machine or Windows CI runner).
- Building a production Windows `.exe` from Linux is not recommended.
- Use the same Python major/minor version consistently (recommended: Python 3.11).

## 1. Prepare Project Assets

Create an icon file:

- `assets/icons/katib.ico`

Recommended ICO sizes included in one file:

- 16x16
- 32x32
- 48x48
- 256x256

Suggested folders:

```text
assets/
  icons/
    katib.ico
installer/
  output/
```

`installer/output/` is generated during installer build and should stay ignored by Git.

## 2. Set Up Build Environment on Windows

Open PowerShell in the project root and run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install .
pip install pyinstaller
```

## 3. Build Katib.exe with PyInstaller

Run from the project root:

```powershell
pyinstaller --noconfirm --clean --windowed \
  --name Katib \
  --icon assets\icons\katib.ico \
  --collect-all PySide6 \
  --collect-all markdown_it \
  --collect-all mdit_py_plugins \
  --collect-all pygments \
  --collect-all markdown_pdf \
  --collect-all linkify_it \
  app\main.py
```

Expected output:

- `dist/Katib/Katib.exe`

## 4. Smoke Test Before Installer

Run and validate:

```powershell
.\dist\Katib\Katib.exe
```

Check these behaviors before creating an installer:

- App starts with no console window
- Open/create/rename/delete Markdown files work
- Preview toggling works
- PDF export works
- Arabic text and RTL/LTR direction still behave correctly

## 5. Create a Standard Windows Installer with Inno Setup

1. Install Inno Setup 6.
2. Create `installer/katib.iss` with this content:

```ini
; Inno Setup script for Katib

[Setup]
AppId={{B3D1A8C8-7DFB-4E1C-9F2E-0A3F2D9F7A10}
AppName=Katib
AppVersion=0.1.0
AppPublisher=Katib
DefaultDirName={autopf}\Katib
DefaultGroupName=Katib
OutputDir=installer\output
OutputBaseFilename=Katib-Setup-0.1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\icons\katib.ico
UninstallDisplayIcon={app}\Katib.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "dist\Katib\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Katib"; Filename: "{app}\Katib.exe"
Name: "{commondesktop}\Katib"; Filename: "{app}\Katib.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Katib.exe"; Description: "Launch Katib"; Flags: nowait postinstall skipifsilent
```

3. Compile with Inno Setup Compiler.

Expected output:

- `installer/output/Katib-Setup-0.1.0.exe`

## 6. Recommended App Polish for Windows

To improve Windows integration quality:

- Keep `QApplication` name and organization set (already in app entrypoint).
- Ensure the app/window icon is set from your icon asset.
- Optionally set Windows AppUserModelID for better taskbar grouping.
- Ensure high DPI rendering is enabled and verified at 125% and 150% scaling.

## 7. Optional but Highly Recommended: Code Signing

Unsigned executables/installers can trigger SmartScreen warnings.

Sign both files:

- `dist/Katib/Katib.exe`
- `installer/output/Katib-Setup-<version>.exe`

Use a trusted code-signing certificate for production distribution.

## 8. Release Checklist

Before publishing each release:

- Bump version in project metadata and installer script
- Rebuild executable
- Rebuild installer
- Install on a clean Windows VM
- Verify launch, shortcuts, uninstall, file workflow, and PDF export
- Sign binaries (if available)
- Publish installer artifact (GitHub Releases, website, or internal distribution)

## 9. Useful Troubleshooting

If app starts but crashes on a tester machine:

- Rebuild with `--clean`
- Confirm all required libraries are collected
- Test from a clean VM where Python is not installed

If icon does not appear:

- Confirm `.ico` contains multiple sizes
- Confirm `--icon` path is correct
- Rebuild and reinstall (Windows can cache icons)

If preview/export is missing functionality:

- Re-check PyInstaller `--collect-all` list
- Validate runtime behavior from `dist/Katib/Katib.exe` before building installer

## 10. Suggested Future Automation

Automate this process with a GitHub Actions Windows workflow:

1. Install Python and dependencies
2. Build with PyInstaller
3. Build installer via Inno Setup
4. Upload installer as release artifact

This gives reproducible installers for each tag/release.
