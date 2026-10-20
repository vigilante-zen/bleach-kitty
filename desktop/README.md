# Bankai desktop editions

Both implementations are published as source alongside the terminal theme:

- [Python + PySide6](python/README.md): original desktop control center, tray, presets and snapshot management.
- [Rust + Qt Widgets](rust/README.md): experimental compiled edition with a Rust core and C++ Qt view.
- `shared/`: eight matching wallpapers, KDE color schemes and artwork prompts. See the repository artwork documentation for provenance and character ownership.

Install the terminal theme from the repository root first. Both desktop editions use the same installed artwork, settings and snapshots. Select one tray app for login startup. This folder contains source and shared assets, without personal preferences, snapshots, build output or login-screen modifications.

For the Rust edition, install the shared assets at the paths described in the Python README, build from `rust/` with `cargo build --release --locked`, and copy `target/release/bankai-rust` to `~/.local/bin/`. Its terminal helpers are supplied by the root theme. Some compatibility and benchmark scripts additionally require the Python edition to be installed.
