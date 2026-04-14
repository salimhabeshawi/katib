# Katib Change Workflow Guide

This guide defines what to do every time you change the app, whether you add a feature or fix a bug.

Use this as your default process so your local repo stays clean, regressions are caught early, and releases remain stable.

## 0. Goals of This Workflow

- Keep source control clean and reviewable
- Catch regressions before push
- Keep documentation accurate
- Keep packaging reproducible
- Avoid shipping broken UX paths

## 1. Start Every Task With a Clean Baseline

From project root:

```bash
git status -sb
git pull --ff-only origin main
```

If you see unrelated local changes, decide before coding:

- Commit them
- Stash them
- Or intentionally continue with them if they are part of the same task

Do not mix unrelated work in one commit.

## 2. Define the Change Scope

Before coding, write down:

- What user problem this change solves
- Which files are likely to change
- What behavior must remain unchanged
- How you will verify success

Use a tiny scope statement in your notes or commit message draft.

Example scope statement:

- Add sidebar toggle button in main window without changing file tree behavior

## 3. Branching Strategy

Recommended:

- Create a short-lived branch per change

```bash
git checkout -b feat/sidebar-toggle
```

If you choose to work directly on main, keep commits small and atomic.

## 4. Implement in Small Steps

While coding:

- Make one logical change at a time
- Run the app frequently
- Avoid broad refactors unless required
- Preserve existing behavior not related to your task

Typical local run:

```bash
uv run katib
```

## 5. Verify Functionality Before Commit

After each meaningful change, test manually.

Core smoke checklist for Katib:

- App opens without crash
- Open project works
- File tree operations work (open, rename, delete)
- Editor typing works in LTR and RTL
- Preview toggle works
- Vim mode toggle works
- PDF export works

If your change touches typography:

- Verify Latin text appearance
- Verify Arabic text appearance
- Verify mixed Arabic and Latin lines

If your change touches packaging:

- Re-run only required packaging step, not full pipeline by default
- Keep AppDir, dist, and AppImage out of git tracking

## 6. Check Errors Before Staging

Use editor Problems panel and fix errors in changed files.

Also run:

```bash
git status -sb
```

Look for accidental files such as:

- Runtime logs
- Build outputs
- Large binaries
- Temporary scratch files

## 7. Update Documentation When Behavior Changes

Update docs whenever user-visible behavior changes.

Common doc targets:

- README for end-user shortcuts and features
- docs/appimage-packaging.md for Linux packaging flow
- docs/windows-packaging.md for Windows packaging changes

If no docs update is needed, explicitly confirm that in your PR notes or commit body.

## 8. Stage Only What Belongs to This Change

Inspect diffs carefully before staging:

```bash
git diff
```

Then stage intentionally:

```bash
git add path/to/file1 path/to/file2
```

Re-check what is staged:

```bash
git diff --staged
```

## 9. Commit Message Standard

Use clear prefixes and concise intent.

Preferred types:

- feat: new behavior
- fix: bug fix
- docs: documentation-only
- chore: maintenance/tooling/ignore rules
- refactor: structural changes without behavior change

Examples:

- feat: add sidebar header toggle button
- fix: retry PDF export without TOC when heading hierarchy is invalid
- docs: add detailed AppImage workflow for Arch

## 10. Push and Sync

Push branch or main after local validation:

```bash
git push origin <branch-name>
```

If working on main:

```bash
git push origin main
```

After push:

```bash
git status -sb
git log --oneline -n 1
```

Confirm local and remote refs match expected state.

## 11. Post-Change Validation (Release Safety)

When a change is complete, perform a quick regression pass:

- Open existing project
- Create a new markdown file
- Edit text in both directions
- Toggle preview multiple times
- Export at least one PDF

For packaging-affecting changes, verify:

- PyInstaller build still works
- AppImage build command still works
- Final artifact launches

## 12. How To Update AppImage After Changes

Use this every time you change features or fix bugs and want a fresh AppImage.

### 12.1 Decide rebuild depth

- Use quick AppImage refresh if only Python source changed and packaging files did not.
- Use full rebuild if dependencies, PyInstaller spec, desktop file, icon, or packaging docs changed.

### 12.2 Quick refresh (most common)

From project root:

```bash
source .venv-appimage/bin/activate
pyinstaller --noconfirm --clean packaging/linux/katib-appimage.spec

rm -rf AppDir
mkdir -p AppDir/usr/bin
cp -a dist/katib/* AppDir/usr/bin/
cp packaging/linux/katib.desktop AppDir/
cp assets/icons/katib.png AppDir/
chmod +x AppDir/usr/bin/katib

./tools/linuxdeploy-x86_64.AppImage \
	--appdir AppDir \
	--desktop-file AppDir/katib.desktop \
	--icon-file AppDir/katib.png \
	--output appimage
```

Then validate:

```bash
chmod +x Katib-x86_64.AppImage
./Katib-x86_64.AppImage --appimage-version
./Katib-x86_64.AppImage
```

### 12.3 Full rebuild (when packaging inputs changed)

Use this when `pyproject.toml`, `packaging/linux/katib-appimage.spec`, icon, or build toolchain changed.

```bash
rm -rf build dist AppDir
source .venv-appimage/bin/activate
uv pip install --upgrade pyinstaller
uv pip install .

pyinstaller --noconfirm --clean packaging/linux/katib-appimage.spec

mkdir -p AppDir/usr/bin
cp -a dist/katib/* AppDir/usr/bin/
cp packaging/linux/katib.desktop AppDir/
cp assets/icons/katib.png AppDir/
chmod +x AppDir/usr/bin/katib

./tools/linuxdeploy-x86_64.AppImage \
	--appdir AppDir \
	--desktop-file AppDir/katib.desktop \
	--icon-file AppDir/katib.png \
	--output appimage
```

### 12.4 Post-build checks (always)

```bash
ls -lh *.AppImage
sha256sum *.AppImage
du -sh dist/katib AppDir
```

Manual smoke check:

- Launch AppImage
- Open project and edit file
- Toggle preview
- Test PDF export
- Confirm RTL/LTR behavior

### 12.5 Rules to avoid common breakage

- Do not use `--plugin qt` with linuxdeploy for this PyInstaller flow.
- Keep icon square and valid size (256, 384, or 512 recommended).
- Recreate `AppDir` from scratch on each update to avoid stale files.
- Ship only the `.AppImage` file; do not publish `dist/` or `AppDir/`.

## 13. Keep the Repository Clean Over Time

Review ignore rules when new tooling is introduced.

If a new local artifact appears repeatedly, add it to gitignore quickly.

Current local-only categories to keep out of source history:

- Packaging outputs
- Local virtual environments
- Downloaded build tools

## 14. Recovery Playbook for Common Problems

### Problem: app runs locally but frozen build fails

Do this:

1. Rebuild in clean packaging environment
2. Read PyInstaller warnings file
3. Fix import or syntax errors first
4. Rebuild and retest dist executable

### Problem: linuxdeploy Qt plugin fails to find modules

Do this:

1. For PyInstaller bundles, avoid qt plugin mode
2. Use linuxdeploy directly on AppDir
3. Ensure icon resolution is valid and square

### Problem: repo filled with artifacts

Do this:

1. Update gitignore
2. Verify with git status
3. Stage only source/docs/config
4. Commit with chore prefix and clear message

## 15. Definition of Done Checklist

A change is done when all items below are true:

1. Intended behavior works
2. No new errors in changed files
3. Manual smoke checks completed
4. Unrelated files are not in commit
5. Docs updated if behavior changed
6. Commit message is clear and meaningful
7. Remote branch is up to date

## 16. Recommended Command Sequence

This is the shortest safe routine for most tasks:

```bash
git pull --ff-only origin main
uv run katib
git status -sb
git diff
git add <only-related-files>
git diff --staged
git commit -m "type: short meaningful summary"
git push origin <branch-or-main>
```

---

Following this workflow consistently will keep Katib stable, reviewable, and release-ready even as features grow.
