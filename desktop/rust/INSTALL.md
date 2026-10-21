# Install Bankai (Rust edition)

[Choose another edition](../README.md) · [Rust overview](README.md) · [Install Python instead](../python/INSTALL.md)

## Requirements

Linux with KDE Plasma 6, Python 3, a compatible Qt 6 runtime, and (for a source installation) Rust/Cargo, a C++17 compiler, pkg-config and Qt 6 Widgets/SVG/Network development libraries. The prebuilt Linux x86-64 release is built on Ubuntu 24.04 with its system Qt libraries; use a source build on systems with incompatible libraries or other architectures. It is not a portable static binary.

Both editions use the shared terminal theme, which requires Kitty, Fish, Fastfetch, btop, fzf and Python 3. Install those prerequisites with your distribution's package manager. The installer does not install system packages or change your default shell. If Fish is not your default, open Kitty and run `fish`.

For a source installation, the installer runs `cargo build --release --locked`. Cargo downloads locked dependencies on the first build. A prebuilt Rust package contains `desktop/rust/bin/bankai-rust`, which the installer uses directly; Rust/Cargo and C++ build tools are then unnecessary. Check native runtime compatibility with `ldd desktop/rust/bin/bankai-rust`; no libraries should say `not found`.

## 1. Download your edition

Choose a package on the [GitHub Releases page](https://github.com/vigilante-zen/bleach-kitty/releases):

- **`bankai-rust-linux-x86-64.tar.gz`** — compiled Linux x86-64 app, Rust source and shared terminal theme/artwork.
- **`bankai-rust-source.tar.gz`** — source build for other compatible Linux environments.

Release assets appear after a release is published and the packaging workflow passes. Until the first release is available, clone the repository instead. Each edition archive includes only the selected desktop edition plus common files. Its `.sha256` sidecar verifies the download; for example, run `sha256sum -c ARCHIVE.tar.gz.sha256` in the download directory.

Extract the archive and open its top-level directory, or clone:

```bash
git clone https://github.com/vigilante-zen/bleach-kitty.git
cd bleach-kitty
```

## 2. Preview and install

From the repository root, the default desktop installer selects Rust:

```bash
python3 desktop/install.py --dry-run
python3 desktop/install.py
```

The edition-specific equivalent is `python3 desktop/rust/install.py`. The Python alternative remains available through `python3 desktop/python/install.py`.

One command installs the selected app, shared wallpapers/color schemes, its icon and KDE app-menu entry. It also installs the shared terminal theme unless a receipt from the root theme installer already exists. An unmanaged theme setup can cause the root theme installer to refuse conflicting managed blocks; use `--skip-theme` only when you have already installed a working terminal theme yourself.

Existing desktop files are backed up before replacement. Installer state and originals are kept in `~/.local/state/bankai-desktop-install/`. Locally edited managed desktop files block updates until you preserve or resolve those edits. Shared desktop assets stay installed while another edition still owns them. No portrait preferences, snapshots or login-startup settings are bundled or reset.

For a staging installation, add `--home /absolute/test/home`. It does not launch a desktop session. `--dry-run` writes no installation files and does not compile Rust. Actual theme installation and desktop installation have separate receipts: if desktop installation fails after installing the theme, the theme remains installed and can be uninstalled separately.

## 3. Launch

Search **Bankai** in KDE's app menu, or run:

```bash
"$HOME/.local/bin/bankai"
```

Use `bankai tray` for tray mode and `bankai backups` for backup management. `bankai-rust` remains available as a direct compatibility command. If the short command is not found, open a new Fish session or use the absolute path above. Run `bankai-doctor` inside Fish to check the terminal theme.

In **Terminal & tools**, open **Choose terminal character…** for a searchable thumbnail grid. Filter by faction, forms, new arrivals, recent use or favorites; Random stays available at the top. Press `/` to focus search, use arrow keys to move between cards, and press Enter to select. Choose Color/Manga/Mixed and click **Save terminal artwork**. Enable **Match desktop character** to follow desktop preset changes; leave it off for independent rotation. New tabs use the saved choice. `bankai-pick --session reset` in Fish clears a shell-only override.

## Update or switch editions

Quit the tray app before updating. In a Git clone, run `git pull --ff-only`, then rerun `python3 desktop/rust/install.py`. For a release package, extract the new package and run its installer. Original pre-install files remain backed up across upgrades. The desktop installer updates unchanged managed terminal files and adds new artwork while preserving preferences and local edits. Use `--skip-theme` to leave the terminal installation untouched. Original backups are retained.

To switch, disable login startup in the current edition, quit its tray app, and follow the [other edition's guide](../python/INSTALL.md). Both commands can coexist. They share desktop settings and snapshots; do not apply changes from both at once. Enable only your preferred edition at login. Rust tray startup keeps the control center hidden; if the tray is unavailable, its fallback window starts minimized. Repeated tray launches do not raise an existing window.

## Uninstall

Disable the edition's login-startup checkbox, then quit its tray app. From the package or repository root:

```bash
python3 desktop/rust/install.py uninstall --dry-run
python3 desktop/rust/install.py uninstall
```

Uninstall restores originals and removes files added by this desktop installer. Files edited since installation are retained and remain tracked for manual resolution. Shared desktop files remain while the other edition uses them. Theme files, runtime preferences and snapshots are kept. To remove the common terminal theme as well, use the separate root `python3 install.py uninstall` command after removing both desktop editions.

The manga SDDM login theme and its system installer are bundled with both editions. Use **Login screen setup** in the app to preview it and copy the install or restore command. Activate separately with `sudo python3 ~/.local/share/bleach-desktop/install-login.py install`; restore with the same command ending in `restore`. Activation requires SDDM with Qt 6 and systemd. Setup follows the sudo caller’s selected desktop preset using full manga wallpaper scenes; later character changes need no sudo prompt. Updates preserve locally edited system files by refusing to overwrite them. Desktop uninstall does not change an activated system theme; restore it first if desired. Shared login assets remain until both editions are uninstalled.

## Validation

For a source checkout:

```bash
cd desktop/rust
cargo test --locked
cargo build --release --locked
QT_QPA_PLATFORM=offscreen target/release/bankai-rust --smoke-test
```

After installing a prebuilt package, use `QT_QPA_PLATFORM=offscreen ~/.local/bin/bankai --smoke-test`. Smoke checks read installed artwork and snapshots without applying presets. They save screenshots under `artifacts/` unless `BANKAI_ARTIFACT_DIR` overrides the location. Live KDE behavior needs desktop testing. `scripts/check_binary.py` checks Rust/Python snapshot compatibility and verifies the Rust preset catalog matches the shared Python catalog. Benchmarking requires the Python desktop edition too. For restore, select a local snapshot or run `bankai restore SNAPSHOT_NAME`.

## Appearance controls

Search desktop characters by name, form or subtitle, or press `/` to focus the search. Open **Appearance options** beside the background controls. Choose Color or Manga for desktop/lock screen, an optional custom accent (`#RRGGBB`), a fixed manga login character or Follow background, and the character pool for optional shuffle when Bankai starts at login. Save, then Apply a preset for wallpaper/accent changes. Use **Reset to defaults** to confirm and restore the default appearance settings and TYBW desktop preset. This leaves saved custom presets and separate Fastfetch portrait preferences intact. Login choice syncs after the one-time SDDM setup. Enable only one edition at login when using shuffle. Settings are shared by both apps and included in desktop snapshots; uninstall preserves them.

Eighteen desktop presets include adult Nelliel with Gamuza, Aizen, TYBW Renji, adult Bankai Hitsugaya, Bankai Kenpachi and Yhwach. Terminal selection also offers TYBW True Shikai Ichigo and Bankai Kenpachi; the `tybw-forms` terminal group rotates TYBW forms separately from the desktop shuffle pool. Ulquiorra remains a legacy-arc option.
