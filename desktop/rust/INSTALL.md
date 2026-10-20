# Install Bankai Rust

[Choose another edition](../README.md) · [Rust overview](README.md) · [Python installation](../python/INSTALL.md)

Choose this edition for the compiled Rust core and Qt Widgets interface, including live portrait previews and optional matching to the desktop character. It is experimental. Installing the Python control-center edition is optional; Rust runs its own preset and snapshot backend.

Requirements: Linux with KDE Plasma 6, Rust and Cargo supporting this source, a C++17 compiler, pkg-config, and Qt 6 Widgets, SVG and Network development libraries. The source was built and tested with Rust/Cargo 1.99.1 and Qt 6.12. The terminal theme still uses Python and Fish helpers.

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

## 3. Build and test Rust

From the repository root:

```bash
cd desktop/rust
cargo test --locked
cargo build --release --locked
cd ../..
```

Cargo downloads the locked build dependencies on the first build. Add `--offline` only when those dependencies are already cached. If Qt detection fails, check that `pkg-config --modversion Qt6Widgets Qt6Svg Qt6Network` succeeds after installing your distribution's Qt development packages.

## 4. Install the Rust executable

```bash
install -m 755 desktop/rust/target/release/bankai-rust "$HOME/.local/bin/bankai-rust"
cp desktop/rust/assets/bleach-tray.svg \
  "$HOME/.local/share/icons/hicolor/scalable/apps/bleach-bankai-rust.svg"
```

## 5. Add the app launcher

```bash
cat > "$HOME/.local/share/applications/bleach-bankai-rust.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Bankai Rust
Comment=Bleach desktop control center — Rust edition
Exec="$HOME/.local/bin/bankai-rust"
Icon=bleach-bankai-rust
Terminal=false
Categories=Settings;DesktopSettings;
StartupNotify=false
EOF
```

Search **Bankai Rust** in KDE's app menu, or launch directly:

```bash
"$HOME/.local/bin/bankai-rust"
```

## Use and update

- `bankai-rust` opens the window; `bankai-rust tray` starts tray mode; `bankai-rust backups` opens backup management.
- In **Terminal & tools**, choose a portrait or random rotation and Color/Manga/Mixed. Preview first, then click **Save terminal artwork**. New terminal tabs use your selection.
- Enable **Match desktop character** and save to follow desktop presets. Leave it off to preserve independent portrait selection. Random previews are examples and do not advance the shuffle deck.
- Shell-only overrides take precedence in that shell. Run `bankai-pick --session reset` in Fish to follow saved preferences.
- Choose your login-startup preference in the app. Disable the previous edition's startup and quit its tray app when switching editions.
- To update, quit Bankai Rust, run `git pull --ff-only` from the repository, and repeat steps 2–4. Keep your settings and snapshots; do not rerun the root theme installer over an existing theme installation.
- For restore, select an existing snapshot in the app or pass its name to `bankai-rust restore SNAPSHOT_NAME`.

## Validation and limits

From `desktop/rust/` after building and installing the shared artwork:

```bash
QT_QPA_PLATFORM=offscreen target/release/bankai-rust --smoke-test
```

The smoke test previews installed artwork and reads your real snapshot list without applying presets. Screenshots go to the ignored `artifacts/` directory. `scripts/check_binary.py` and `scripts/benchmark.py` compare against the Python installation and need that edition installed too; they are optional for Rust-only users.

Live KDE tray display, cross-process activation and wallpaper/color changes need desktop testing. The app's setup-guide and system login-screen shortcuts refer to legacy installed Python setup files; those are not supplied by a Rust-only installation. Use this guide for Rust setup. Desktop installation is manual, and the root terminal uninstaller does not remove these desktop files.
