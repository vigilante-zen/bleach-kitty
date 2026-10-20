# Choose your Bankai edition

Install the edition you prefer. Both use the same terminal artwork and KDE desktop assets.

| | Python + PySide6 | Rust + Qt Widgets |
| --- | --- | --- |
| Install guide | **[Install Python](python/INSTALL.md)** | **[Install Rust](rust/INSTALL.md)** |
| Source and details | [Python overview](python/README.md) | [Rust overview](rust/README.md) |
| App command | `bankai` | `bankai-rust` |
| App runtime | Python and PySide6 | Compiled Rust core and Qt C++ view |
| Build required | No | Yes: Rust/Cargo, C++17 and Qt development libraries |
| Terminal artwork controls | Fish settings menu | In-app selection and live color/manga preview |
| Portrait follows desktop | Presets select their matching portrait | Optional; independent rotation is preserved by default |
| Status | Original edition | Experimental edition |

The Rust edition has a smaller measured startup footprint on the development machine; [benchmark details and limitations](rust/README.md#measured-comparison) explain the comparison. Choose Python for the original implementation without a compilation step, or Rust for the compiled app and its portrait controls.

Each install guide is self-contained. You do not need to install the other control-center edition. Both need the shared terminal theme, whose Python/Fish helpers also run when using the Rust edition.

## Screenshots

| Python control center | Rust control center |
| --- | --- |
| ![Python desktop control center](../docs/screenshots/python-control-center.png) | ![Rust desktop control center](../docs/screenshots/rust-control-center.png) |

**Rust terminal artwork preview**

![Rust color and manga preview with desktop matching](../docs/screenshots/rust-terminal-art.png)

## Downloads and installers

[Choose a release download](https://github.com/vigilante-zen/bleach-kitty/releases). Python and Rust are packaged separately, each with the shared terminal theme and artwork. Assets appear after the release workflow succeeds. Run just your chosen installer from the package or repository root:

```bash
python3 desktop/python/install.py  # Python edition
# OR
python3 desktop/rust/install.py    # Rust edition; builds source if needed
```

Both bundle the optional Ichigo manga SDDM login theme. Open **Login screen setup** in either app to preview it and copy activation or restore commands. Activation requires administrator access and stays separate from desktop presets.

Both support `--dry-run`, upgrades, `uninstall`, original-file backups and shared-asset ownership. Read the selected edition's install guide before running. No system dependencies are installed automatically.

## Switching editions

1. Disable login startup in the currently running edition and quit its tray app.
2. Follow the other edition's installation guide.
3. Launch the new edition and enable its login startup if desired.

The two commands can coexist. Their desktop presets, terminal preferences and snapshots are shared, so changes made by either edition affect the same desktop. Avoid applying changes from both at the same time. Python presets always select a matching terminal portrait; Rust's optional matching preference applies to Rust preset changes.

## Repository layout

- `python/`: Python source, command scripts, requirements and its own install guide.
- `rust/`: Rust/C++ source, build files and its own install guide.
- `shared/`: wallpapers, KDE color schemes and artwork prompts used by either edition.

[Back to the repository](../README.md) · [Artwork ownership and provenance](../docs/ARTWORK.md)

## Login startup

Choose **Start the Rust edition in the tray at login** in Rust, or the corresponding checkbox in Python. Disable the other edition before switching. Rust tray startup keeps its window hidden; when the tray is unavailable, the fallback window starts minimized. Repeated tray launches do not raise an existing control center. A normal app-menu launch opens the window.

These settings control Bankai only. Minimizing other restored applications is a per-user KDE session customization; it is not enabled for everyone by an edition installer. The development machine uses a separate login-only minimizer with a 20-second startup interval. Any app opened manually in that interval also minimizes; apps opened after it behave normally. This machine-specific helper and autostart entries are outside the repository and release archives.
