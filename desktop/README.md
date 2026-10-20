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
