# Linux AppImage Packaging Guide (Qt WebEngine Included)

This guide packages Katib as a `.AppImage` on Linux while keeping `QWebEngineView` enabled.
It is optimized for size as much as possible without changing runtime behavior.

This is a full, step-by-step process. Do not skip steps on the first run.

## 0. What You Should Expect

- Because Katib uses `PySide6` + `QtWebEngine`, the AppImage will not be tiny.
- A realistic size for a WebEngine desktop app is often much larger than simple Qt apps.
- The goal here is to avoid unnecessary bloat while keeping current functionality intact.

## 1. Build Host Strategy (Important)

You can build on Arch Linux, but release compatibility needs extra attention.

Recommended strategy:

- For local testing: build directly on Arch.
- For public release artifacts: build on Ubuntu 22.04 x86_64 (VM/container/CI).

Why:

- AppImage compatibility depends heavily on the build host glibc baseline.
- Arch usually has newer glibc than many target machines.
- A binary built on Arch can fail on older distributions.

If your audience is only Arch users, Arch-native build is usually fine.

## 2. System Dependencies

### 2.1 Arch Linux (your environment)

Install required build tools and runtime libraries:

```bash
sudo pacman -Syu --needed \
  base-devel \
  uv \
  patchelf \
  file \
  wget \
  curl \
  desktop-file-utils \
  glib2 \
  libxkbcommon \
  nss \
  alsa-lib \
  libdrm \
  mesa
```

Install Qt development tools for plugin detection:

```bash
sudo pacman -S --needed qt6-base
```

### 2.2 Ubuntu 22.04 (recommended for public release builds)

If you build release artifacts in an Ubuntu VM/container/CI, use:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  patchelf \
  file \
  wget \
  curl \
  desktop-file-utils \
  libglib2.0-dev \
  libxkbcommon-x11-0 \
  libnss3 \
  libasound2 \
  libdrm2 \
  libgbm1
```

Notes:

- `libxkbcommon-x11-0`, `libnss3`, `libgbm1`, and friends are commonly needed by Qt WebEngine.
- Missing these during testing can look like runtime crashes.
- On Arch, the equivalent packages are installed in section 2.1.

## 3. Project Preparation

From project root:

```bash
cd /home/salimhabeshawi/Projects/katib
```

Clean old build outputs:

```bash
rm -rf build dist AppDir *.spec
```

Keep your normal development venv untouched. Use a dedicated packaging venv.

## 4. Create a Clean Packaging Environment

```bash
uv venv .venv-appimage
source .venv-appimage/bin/activate
uv pip install --upgrade pip setuptools wheel
```

Install Katib and packager:

```bash
uv pip install .
uv pip install pyinstaller
```

Why this matters:

- Clean environment prevents hidden dependencies from being accidentally bundled.
- Smaller and more reproducible output.

## 5. Download linuxdeploy Tooling

Create a local tools folder:

```bash
mkdir -p tools
cd tools
```

Download linuxdeploy:

```bash
wget -O linuxdeploy-x86_64.AppImage \
  https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage
```

Make it executable:

```bash
chmod +x linuxdeploy-x86_64.AppImage
```

Go back to project root:

```bash
cd ..
```

## 6. Add Linux Desktop Metadata Files

Create folders:

```bash
mkdir -p packaging/linux assets/icons
```

### 6.1 Desktop entry

Create `packaging/linux/katib.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Katib
Comment=Minimal distraction-free Markdown writing app
Exec=katib
Icon=katib
Categories=Office;TextEditor;
Terminal=false
StartupNotify=true
```

### 6.2 App icon

Add a PNG icon named:

```text
assets/icons/katib.png
```

Recommended size:

- Square PNG only (width must equal height)
- Use one of: 256x256, 384x384, or 512x512

Validate your icon before building:

```bash
file assets/icons/katib.png
```

If needed, convert to 512x512:

```bash
magick assets/icons/katib.png -resize 512x512^ -gravity center -extent 512x512 assets/icons/katib.png
```

## 7. Create a PyInstaller Spec Optimized for WebEngine

Create `packaging/linux/katib-appimage.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parents[1]

block_cipher = None

hiddenimports = []
hiddenimports += collect_submodules("app")
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("services")
hiddenimports += collect_submodules("ui")
hiddenimports += collect_submodules("PySide6.QtWebEngineCore")
hiddenimports += collect_submodules("PySide6.QtWebEngineWidgets")
hiddenimports += collect_submodules("PySide6.QtWebChannel")

# Only collect what Katib needs, avoid collect-all PySide6.
datas = []
datas += collect_data_files("PySide6", include_py_files=False)
datas += collect_data_files("markdown_it", include_py_files=False)
datas += collect_data_files("mdit_py_plugins", include_py_files=False)
datas += collect_data_files("pygments", include_py_files=False)
datas += collect_data_files("markdown_pdf", include_py_files=False)
datas += collect_data_files("linkify_it", include_py_files=False)

a = Analysis(
  [str(ROOT / "app" / "main.py")],
  pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.Qt3DAnimation",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DExtras",
        "PySide6.Qt3DInput",
        "PySide6.Qt3DLogic",
        "PySide6.Qt3DRender",
        "PySide6.QtBluetooth",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtQuick3D",
        "PySide6.QtQuickControls2",
        "PySide6.QtRemoteObjects",
        "PySide6.QtScxml",
        "PySide6.QtSensors",
        "PySide6.QtSerialBus",
        "PySide6.QtSerialPort",
        "PySide6.QtSql",
        "PySide6.QtStateMachine",
        "PySide6.QtTest",
        "PySide6.QtTextToSpeech",
        "PySide6.QtWebSockets",
        "PySide6.QtXml",
        "PySide6.QtXmlPatterns",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="katib",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="katib",
)
```

Why this is size-conscious:

- No blanket `--collect-all PySide6`.
- Explicitly excludes unused Qt modules.
- Keeps WebEngine modules required by your current preview behavior.

## 8. Build the Onedir App with PyInstaller

```bash
source .venv-appimage/bin/activate
uv pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean packaging/linux/katib-appimage.spec
```

Expected output folder:

```text
dist/katib/
```

## 9. Quick Local Smoke Test (Before AppImage)

```bash
./dist/katib/katib
```

Validate all core behavior:

- App starts.
- File tree works.
- Edit/preview toggle works.
- `QWebEngineView` preview works.
- PDF export works.
- RTL/LTR and Arabic text behavior are unchanged.

If anything fails, fix now before AppImage wrapping.

## 10. Prepare AppDir Layout

```bash
rm -rf AppDir
mkdir -p AppDir/usr/bin
```

Copy PyInstaller output into AppDir:

```bash
cp -a dist/katib/* AppDir/usr/bin/
```

Copy desktop file and icon to AppDir root (required by linuxdeploy):

```bash
cp packaging/linux/katib.desktop AppDir/
cp assets/icons/katib.png AppDir/
```

Make launcher executable explicit:

```bash
chmod +x AppDir/usr/bin/katib
```

## 11. Build AppImage with linuxdeploy

For a PyInstaller bundle, do not use `--plugin qt`.
PyInstaller already bundles the Qt runtime in `dist/katib/_internal`, and linuxdeploy-plugin-qt may fail to auto-detect modules from a frozen Python launcher.

Run linuxdeploy:

```bash
./tools/linuxdeploy-x86_64.AppImage \
  --appdir AppDir \
  --desktop-file AppDir/katib.desktop \
  --icon-file AppDir/katib.png \
  --output appimage
```

Expected output:

- `Katib-x86_64.AppImage` (name may vary slightly)

## 12. Space Optimization Pass (Safe)

Do these only after a working AppImage build.

### 12.1 Remove obviously unused plugin families from AppDir

After linuxdeploy, inspect plugin folders:

```bash
find AppDir/usr/plugins -maxdepth 2 -type d | sort
```

Commonly removable (if not used by your app):

- `AppDir/usr/plugins/gamepads`
- `AppDir/usr/plugins/sensors`
- `AppDir/usr/plugins/canbus`
- `AppDir/usr/plugins/position`
- `AppDir/usr/plugins/geoservices`

Example:

```bash
rm -rf AppDir/usr/plugins/gamepads \
       AppDir/usr/plugins/sensors \
       AppDir/usr/plugins/canbus \
       AppDir/usr/plugins/position \
       AppDir/usr/plugins/geoservices
```

Rebuild AppImage after each pruning step and retest.

### 12.2 Strip only safe local binaries (optional)

```bash
find AppDir/usr/bin -type f -executable -exec strip --strip-unneeded {} + || true
```

Do not blindly strip everything under WebEngine directories.

### 12.3 Keep compression defaults

linuxdeploy/appimagetool already uses solid compression suitable for distribution.

## 13. Validate Final AppImage on Clean System

Test on a separate machine/VM without your dev environment:

```bash
chmod +x Katib-x86_64.AppImage
./Katib-x86_64.AppImage
```

Validate again:

- App launches.
- WebEngine preview renders content and syntax highlighting.
- External links open correctly.
- PDF export still works.
- No regressions in editor behavior.

## 14. Measure Size Correctly

Measure each stage to know where size comes from:

```bash
du -sh .venv-appimage

du -sh dist/katib

du -sh AppDir

ls -lh *.AppImage
```

Interpretation:

- `.venv-appimage` is not shipped.
- Only `.AppImage` is shipped to users.
- WebEngine assets are expected to dominate final size.

## 15. Common Mistakes That Inflate Size

- Using `--collect-all PySide6`.
- Building from a dirty environment with extra Python packages.
- Shipping both `dist/`, `AppDir/`, and `.AppImage` instead of only `.AppImage`.
- Adding debug symbols and then never stripping safe binaries.

## 16. Troubleshooting

### App starts but preview is blank

- Check WebEngine resources exist in AppDir:

```bash
find AppDir -iname "*QtWebEngine*" | head
```

- Rebuild with clean cache:

```bash
rm -rf build dist AppDir
source .venv-appimage/bin/activate
uv pip install --upgrade pyinstaller
pyinstaller --noconfirm --clean packaging/linux/katib-appimage.spec
```

### AppImage runs on your machine but not others

- If you built on Arch and need broader compatibility, rebuild on Ubuntu 22.04 baseline.
- Test in a clean VM.

### Sandbox/GPU warnings

Some Vulkan/GPU warnings are environment-specific and not always fatal.
If app function is correct, they can be benign.

## 17. Release Checklist

Before publishing:

1. Build from clean git state.
2. Run full smoke test on PyInstaller output.
3. Build AppImage.
4. Run full smoke test on AppImage.
5. Test on second machine/VM.
6. Record final size and checksum:

```bash
sha256sum Katib-x86_64.AppImage
```

7. Publish only the `.AppImage` artifact.

## 18. Optional: Keep Build Reproducible

Pin packaging tool versions in a requirements file used only for release builds.
Example tools to pin:

- `pyinstaller`
- `setuptools`
- `wheel`

This reduces size and behavior drift between releases.

---

If you want, the next step can be a companion `packaging/linux/build-appimage.sh` script that automates this exact flow without changing app logic.
