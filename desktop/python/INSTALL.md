# Install Bankai Python

[Choose another edition](../README.md) · [Python overview](README.md) · [Rust installation](../rust/INSTALL.md)

Choose this edition for the original Python + PySide6 control center. Requires Linux with KDE Plasma 6, Python 3 and PySide6 (Qt 6). Install PySide6 through your distribution's packages or Python environment before continuing. If using a virtual environment, activate it before launching Bankai; the `bankai` script uses `python3` from PATH.

## 1. Get the repository and install the terminal theme

Run these commands in Bash. If you already cloned the repository, open that folder instead of cloning again.

```bash
git clone https://github.com/vigilante-zen/bleach-kitty.git
cd bleach-kitty
```

Both desktop editions use the shared Kitty/Fish theme. If it is already installed, skip these two commands. The theme installer rejects a second installation; see the [theme update and restore notes](../../README.md#uninstall-and-restore) before reinstalling.

```bash
python3 install.py --dry-run
python3 install.py
```

The theme needs Kitty, Fish, Fastfetch, btop, fzf and Python 3. It does not change your default shell. Open Kitty and run `fish` if needed. Use `bankai-doctor` inside Fish to check the theme.

## 2. Install the shared desktop artwork

Run from the repository root. These copy commands replace matching installed files. Before upgrading an existing desktop installation, quit its tray app and save a backup with `bankai backup` or `bankai-rust backup`; retain your previous executable separately if you want to roll back the application itself.

```bash
mkdir -p "$HOME/Pictures/Bleach-TYBW/Wallpapers" \
  "$HOME/.local/share/color-schemes" \
  "$HOME/.local/share/bleach-desktop" \
  "$HOME/.local/share/icons/hicolor/scalable/apps" \
  "$HOME/.local/share/applications" "$HOME/.local/bin"
cp desktop/shared/wallpapers/*.png "$HOME/Pictures/Bleach-TYBW/Wallpapers/"
cp desktop/shared/color-schemes/*.colors "$HOME/.local/share/color-schemes/"
```

## 3. Install the Python app

From the repository root:

```bash
cp desktop/python/control_center.py desktop/python/snapshot_manager.py \
  "$HOME/.local/share/bleach-desktop/"
cp desktop/python/README.md "$HOME/.local/share/bleach-desktop/README.md"
cp -r desktop/python/icons "$HOME/.local/share/bleach-desktop/"
install -m 755 desktop/python/bin/bankai desktop/python/bin/bankai-desktop \
  desktop/python/bin/bankai-desktop-backup desktop/python/bin/bankai-desktop-restore \
  "$HOME/.local/bin/"
cp desktop/python/icons/bleach-tray.svg \
  "$HOME/.local/share/icons/hicolor/scalable/apps/bleach-bankai.svg"
```

Confirm the interpreter can load the GUI:

```bash
python3 -c 'from PySide6.QtWidgets import QApplication; print("PySide6 ready")'
```

## 4. Add the app launcher

```bash
cat > "$HOME/.local/share/applications/bleach-bankai.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Bankai Python
Comment=Bleach desktop control center — Python edition
Exec="$HOME/.local/bin/bankai"
Icon=bleach-bankai
Terminal=false
Categories=Settings;DesktopSettings;
StartupNotify=false
EOF
```

Search **Bankai Python** in KDE's app menu, or launch directly:

```bash
"$HOME/.local/bin/bankai"
```

## Use and update

- `bankai` opens the window; `bankai tray` starts tray mode; `bankai backups` opens backup management.
- Applying a desktop preset also selects its matching terminal portrait. Use `bankai-pick random` in Fish to resume rotation.
- Choose your login-startup preference in **Terminal & tools**. When switching editions, disable the previous edition's startup first and quit its tray app.
- To update, quit Bankai, run `git pull --ff-only` in the repository, then repeat steps 2–3. The root theme installer is separate and should not be rerun over an existing theme installation.
- For restore, use the app to select an existing snapshot, or pass its name explicitly to `bankai restore SNAPSHOT_NAME`. The no-argument restore command retains the original developer baseline identifier and is unsuitable for a fresh installation.

## Validation and limits

```bash
cd desktop/python
python3 check_snapshot_manager.py
QT_QPA_PLATFORM=offscreen python3 check_control_center.py
```

The checks use temporary snapshot/configuration directories. Cross-process activation and live KDE wallpaper/tray behavior need a desktop session. The system login-screen installer is not included in this edition package; the app's login-screen setup shortcut does not supply it. Desktop installation is manual, and the root terminal uninstaller does not remove these desktop files.
