# Bankai Python + PySide6

**[Install the Python edition →](INSTALL.md)** · [Compare editions](../README.md) · [Install Rust instead](../rust/INSTALL.md)

Source for the original Bankai desktop control center. Requires Linux/KDE Plasma 6, Python 3, PySide6, and the Bleach Kitty terminal theme from the repository root.

`control_center.py` provides the window and tray; `snapshot_manager.py` manages verified snapshots and cleanup. `bin/` contains the four installed command scripts. Both editions share desktop preferences and backups.

For a manual installation, copy the Python modules and `icons/` to `~/.local/share/bleach-desktop/`, and the scripts in `bin/` to `~/.local/bin/` with executable permissions. Put `../shared/wallpapers/*.png` in `~/Pictures/Bleach-TYBW/Wallpapers/` and `../shared/color-schemes/*.colors` in `~/.local/share/color-schemes/`. Install the terminal theme first; this desktop source archive has no automatic installer. Back up existing files before replacing them.

Run `bankai` for the window, `bankai tray` for the tray, or `bankai backups` for snapshots. No startup-at-login preference is bundled. `bankai-desktop-restore` retains the original installation's baseline identifier; on another machine, provide an explicit local snapshot name.

Validation: `python3 check_snapshot_manager.py` and `QT_QPA_PLATFORM=offscreen python3 check_control_center.py`. The backend `check.py` also needs the installed command scripts and color schemes. Live KDE integration needs a desktop session.
