# Install Bankai Python

[Choose another edition](../README.md) · [Python overview](README.md) · [Install Rust instead](../rust/INSTALL.md)

## Requirements

Linux with KDE Plasma 6, Python 3 and PySide6 (Qt 6). Install PySide6 through your distribution or a Python environment; the `bankai` command uses `python3` from PATH. If using a virtual environment, activate it before installing and before using the `bankai` terminal command. The app-menu launcher records the Python interpreter running the installer, so it can use that environment directly.

Both editions use the shared terminal theme, which requires Kitty, Fish, Fastfetch, btop, fzf and Python 3. Install those prerequisites with your distribution's package manager. The installer does not install system packages or change your default shell. If Fish is not your default, open Kitty and run `fish`.

## 1. Download your edition

Choose a package on the [GitHub Releases page](https://github.com/vigilante-zen/bleach-kitty/releases):

- **`bankai-python.tar.gz`** — Python desktop source and shared terminal theme/artwork.

Release assets appear after a release is published and the packaging workflow passes. Until the first release is available, clone the repository instead. Each edition archive includes only the selected desktop edition plus common files. Its `.sha256` sidecar verifies the download; for example, run `sha256sum -c ARCHIVE.tar.gz.sha256` in the download directory.

Extract the archive and open its top-level directory, or clone:

```bash
git clone https://github.com/vigilante-zen/bleach-kitty.git
cd bleach-kitty
```

## 2. Preview and install

From the extracted package or repository root:

```bash
python3 desktop/python/install.py --dry-run
python3 desktop/python/install.py
```

One command installs the selected app, shared wallpapers/color schemes, its icon and KDE app-menu entry. It also installs the shared terminal theme unless a receipt from the root theme installer already exists. An unmanaged theme setup can cause the root theme installer to refuse conflicting managed blocks; use `--skip-theme` only when you have already installed a working terminal theme yourself.

Existing desktop files are backed up before replacement. Installer state and originals are kept in `~/.local/state/bankai-desktop-install/`. Locally edited managed desktop files block updates until you preserve or resolve those edits. Shared desktop assets stay installed while another edition still owns them. No portrait preferences, snapshots or login-startup settings are bundled or reset.

For a staging installation, add `--home /absolute/test/home`. It does not launch a desktop session. `--dry-run` writes no installation files and does not compile Rust. Actual theme installation and desktop installation have separate receipts: if desktop installation fails after installing the theme, the theme remains installed and can be uninstalled separately.

## 3. Launch

Search **Bankai Python** in KDE's app menu, or run:

```bash
"$HOME/.local/bin/bankai"
```

Use `bankai tray` for tray mode and `bankai backups` for backup management. If the short command is not found, open a new Fish session or use the absolute path above. Run `bankai-doctor` inside Fish to check the terminal theme.

Applying a Python desktop preset also selects its matching terminal portrait. Run `bankai-pick random` in Fish to resume rotation.

## Update or switch editions

Quit the tray app before updating. In a Git clone, run `git pull --ff-only`, then rerun `python3 desktop/python/install.py`. For a release package, extract the new package and run its installer. Original pre-install files remain backed up across upgrades. Update the terminal theme separately using its [uninstall/reinstall procedure](../../README.md#uninstall-and-restore); the desktop updater preserves an existing managed terminal installation.

To switch, disable login startup in the current edition, quit its tray app, and follow the [other edition's guide](../rust/INSTALL.md). Both commands can coexist. They share desktop settings and snapshots; do not apply changes from both at once. Enable only your preferred edition at login.

## Uninstall

Disable the edition's login-startup checkbox, then quit its tray app. From the package or repository root:

```bash
python3 desktop/python/install.py uninstall --dry-run
python3 desktop/python/install.py uninstall
```

Uninstall restores originals and removes files added by this desktop installer. Files edited since installation are retained and remain tracked for manual resolution. Shared desktop files remain while the other edition uses them. Theme files, runtime preferences and snapshots are kept. To remove the common terminal theme as well, use the separate root `python3 install.py uninstall` command after removing both desktop editions.

The legacy system login-screen installer is not bundled; its app shortcut requires a separately installed setup. These installers do not change the system login screen.

## Validation

```bash
python3 desktop/python/check_snapshot_manager.py
QT_QPA_PLATFORM=offscreen python3 desktop/python/check_control_center.py
```

The UI checks expect the shared desktop artwork to be installed. Snapshot tests use temporary directories. Cross-process activation and live KDE behavior need a desktop session. For restore, select a local snapshot in the app or run `bankai restore SNAPSHOT_NAME`; the no-argument legacy restore retains the original developer baseline identifier.
