# Bankai Python + PySide6 · alternative edition

**[Install the Python edition →](INSTALL.md)** · [Compare editions](../README.md) · [Install Rust instead](../rust/INSTALL.md)

Source for the original Bankai desktop control center. Requires Linux/KDE Plasma 6, Python 3, PySide6, and the Bleach Kitty terminal theme from the repository root.

`control_center.py` provides the window and tray; `snapshot_manager.py` manages verified snapshots and cleanup. `bin/` contains the four installed command scripts. Preset application snapshots first and rolls back its configuration and state-marker writes if a later write fails. Both editions share desktop preferences and backups.

Install or update with `python3 desktop/python/install.py` from the repository root. The installer creates the app launcher, installs shared assets, backs up existing files and supports uninstalling. Follow the [complete installation guide](INSTALL.md) for requirements and commands.

Run `bankai-python` for the window, `bankai-python tray` for the tray, or `bankai-python backups` for snapshots. The shared `bankai` command prefers Rust when installed and falls back to Python. No startup-at-login preference is bundled. `bankai-desktop-restore` retains the original installation's baseline identifier; on another machine, provide an explicit local snapshot name.

Validation: `python3 check_snapshot_manager.py` and `QT_QPA_PLATFORM=offscreen python3 check_control_center.py`. The backend `check.py` also needs the installed command scripts and color schemes. Live KDE integration needs a desktop session.
