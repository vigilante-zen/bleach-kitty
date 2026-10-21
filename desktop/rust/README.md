# Bankai Rust — default desktop edition

**[Install the Rust edition →](INSTALL.md)** · [Compare editions](../README.md) · [Install Python instead](../python/INSTALL.md)

A separately installed, compiled edition of the Bankai desktop control center. Application logic is Rust; a Qt Widgets C++ presentation layer provides the window, SVG rendering, tray integration, file watching and background-process plumbing. The main app does not start a Python interpreter. It is not an all-Rust GUI toolkit.

## Try it

```fish
bankai
bankai tray
bankai backups
bankai status
```

You can also search **Bankai** in KDE's app launcher. `bankai-rust` remains a direct compatibility command. The Python alternative is `bankai-python`. The Rust app has its own instance channel and optional login-startup preference. It is not enabled at login by default. Avoid enabling both tray apps at login unless you want two icons.

Both editions read the same saved preset, character artwork, KDE settings, Kitty accents, portrait selection, snapshots and protected-snapshot list. Applying a preset or restoring a snapshot changes the shared desktop. Appearance-option saves detect changes made in the other edition while a dialog is open; close and reopen the options before retrying. Comparing their windows and previews is read-only; do not apply competing presets from both editions simultaneously.

## Terminal artwork controls

Under **Terminal & tools**, open **Choose terminal character…** to browse a searchable thumbnail grid. Filter by faction, forms, new arrivals, recently used or favorites, or choose **Random · shuffle current pool** at the top. The picker shows the active random source, portrait count and shuffle mode; **Preview eligible characters** lists exactly who Random can choose. Its search and faction filters only narrow direct choices. Character forms sort beside their base character. Press `/` to focus search, use the arrow keys to move between cards, and press Enter to choose. Then select **Color**, **Manga**, or **Mixed color and manga**, and click **Save terminal artwork**. Changes apply to new terminal tabs. Random rotation uses the groups and favorites configured in the terminal. Color artwork is used when manga is unavailable. Existing shell-only overrides continue to take precedence in that shell; use `bankai-pick --session reset` to follow saved preferences.

Enable **Match desktop character** and save to follow the currently saved desktop preset and future preset changes. Disable it and save a portrait or random rotation to keep terminal artwork independent. Art style remains independent in both modes. The TYBW desktop preset uses random rotation.

The live preview updates before saving. Mixed mode shows color and manga side by side; missing manga falls back to color. Random mode shows a labeled sample without advancing the shuffle deck or changing saved preferences.

Desktop preset changes preserve independent terminal portrait and art preferences. The Python app still uses its original preset behavior. Settings use the same files as `bankai-pick` and `bankai-art`, and external changes appear in the app.

The Rust unit suite, compiled-binary integration checks and offscreen native smoke checks pass. The local installed executable includes these controls. Live KDE interaction still needs desktop testing.

## Ported behavior

- All eighteen presets, wallpaper previews, explicit Apply, automatic snapshots, and rollback if a preset write fails partway through.
- Named custom combinations that capture the current wallpaper, accent, and login-scene choices; failed applies preserve the prior choices.
- Searchable desktop preset cards, searchable login shuffle pools with select/clear shown, and a confirmed reset to the default appearance settings and TYBW preset.
- KDE desktop and lock-screen wallpaper, color schemes and terminal accents; independent terminal portrait and art preferences.
- Hollow-mask tray icon colored for the saved character; updates after command-line changes.
- Tray preset selection, terminal and monitor launchers, snapshot creation, and window reopening.
- Background workers run the same Rust binary; action errors are shown and active operations prevent quitting.
- Snapshot creation, verification, restore with a pre-restore backup, sizes, protection, and reviewed cleanup.
- Original baseline protection, newest-copy retention, symlink/path rejection, and cleanup-plan revalidation.
- Existing Python version-1 manifests and protection metadata remain compatible in both directions.
- Independent Rust autostart toggle and single-instance window handoff.

Existing Fish terminal-settings and monitoring commands are launched as external integrations. Diagnostics can launch the existing `bankai-doctor` helper. The system SDDM installer remains a separate Python tool: this app only shows its existing command. The portrait/greeting scripts and login installer were not rewritten.

The Rust executable and its startup preference are not part of the legacy desktop snapshot allowlist. Source code is in this project. The Python edition remains available as an alternative.

## Measured comparison

Seven interleaved runs per edition, after one discarded warm-up pair, using Qt Fusion with the offscreen platform. Both construct all pages, load eight thumbnails and the initial wallpaper, inspect the same real snapshot directory, show the initial window, and process its first paint.

| Median measurement | Rust + Qt | Python + PySide6 |
| --- | ---: | ---: |
| Reported startup to ready window | 281 ms | 551 ms |
| Parent-measured process wall time | 301 ms | 579 ms |
| Resident memory at ready window | 57.7 MiB | 135.9 MiB |
| Peak resident memory by that point | 57.7 MiB | 135.9 MiB |

The native executable is about 884 KiB and dynamically links the installed Qt libraries. Its smaller footprint also comes from decoding/downscaling thumbnail previews earlier. These results measure the whole rewrite, not Rust versus Python in isolation. RSS includes shared library mappings; it is not proportional physical memory. Live Wayland startup, tray hosting, and steady-state idle CPU were not measured.

Raw runs and method details are in `artifacts/benchmark.json`. Reproduce with:

```sh
python3 scripts/benchmark.py --runs 7
```

## Build

The first release executable was successfully built with Rust/Cargo 1.99.1, Qt 6.12, and the installed C++ compiler, using only cached build dependencies. The package registry could not be resolved from this session.

```sh
cargo build --release --locked
```

Requirements: Rust and Cargo, a C++17 compiler, pkg-config, and Qt 6 Widgets, SVG and Network development packages. Rust `cc` and `pkg-config` are build-only dependencies. The JSON codec is local and strict, with duplicate-key, UTF-8, nesting and size checks. Snapshot SHA-256 uses Qt's established `QCryptographicHash` through the narrow native bridge rather than a custom hash implementation.

References: [Rust FFI](https://doc.rust-lang.org/nomicon/ffi.html), [Qt tray API](https://doc.qt.io/qt-6/qsystemtrayicon.html), [Qt hashing](https://doc.qt.io/qt-6/qcryptographichash.html).

## Validation

- The Rust unit suite passes. Compiled-binary integration checks pass against the release executable using disposable homes. They cover all eighteen presets and two desktop containments, rollback after a mid-apply write failure, catalog parity with Python, exact SHA-256 compatibility, Rust reading/restoring Python snapshots, Python restoring Rust snapshots, permissions and absent files, corruption rejection, path traversal, symlinks, baseline/favorite/recent-copy retention, changed/protected snapshots after review, extra files, corrupt protection metadata, independent autostart settings, and appearance reset behavior and recovery.
- The native offscreen smoke check passed in an isolated temporary home: eighteen previews and exact mask accents, searchable desktop and terminal character selection, configured Random pool summary and eligible-name preview, recovery for malformed custom presets and appearance settings with the original appearance file preserved, automatic reload after an external repair, external snapshot refresh, stale appearance-save conflict protection, nonmutating preview selection, tray action population, cleanup protection, reset-confirmation cancellation without changing saved preferences, background Rust worker, and screenshots at normal/smaller sizes.
- The existing real baseline snapshot was verified read-only by Rust.
- No real desktop settings were changed and no real snapshots were deleted during validation.
- Live KDE tray display, cross-process single-instance activation and live color/wallpaper application remain unverified from this sandbox because it blocks session-bus and Unix-socket access.

```sh
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked --offline
python3 scripts/check_binary.py
QT_QPA_PLATFORM=offscreen target/release/bankai-rust --smoke-test
```

`BANKAI_HOME=/absolute/test/home` selects an isolated home and automatically disables live KDE commands. `BANKAI_OFFLINE=1` disables live KDE commands with normal paths; it does **not** prevent configuration writes. `--smoke-test` uses the real artwork and snapshot directory read-only and saves screenshots under `artifacts/` by default (`BANKAI_ARTIFACT_DIR` overrides that directory).

## Layout

- `src/main.rs`: CLI, configuration, application dispatch and narrow string-ownership FFI boundary.
- `src/presets.rs`: KConfig updates, preset application and KDE subprocess refresh.
- `src/snapshots.rs`: native backup, verification, restore, protection, inspection and cleanup.
- `src/fsutil.rs`: confined paths, atomic writes, shared locking and hash bridge.
- `src/json.rs`: local JSON codec for manifests and local RPC.
- `native/gui.cpp`: Qt view, event handling, worker process, SVG/tray and instance channel.
- `assets/`: imported preset catalog, backup compatibility list, stylesheet, panel script and SVG icons.
- `scripts/`: executable integration checks and reproducible comparison harness.

## Remove the trial

Disable the Rust login-startup checkbox if enabled and quit Bankai Rust. Remove `~/.local/bin/bankai-rust`, `~/.local/share/applications/bleach-bankai-rust.desktop`, `~/.config/fish/completions/bankai-rust.fish`, `~/.local/share/icons/hicolor/scalable/apps/bleach-bankai-rust.svg`, and `~/.local/share/bankai-rust`. The project can be retained for future builds. The existing Python command, artwork and shared desktop settings remain available.

The benchmark measurements above are historical results from the original eight-preset build. The expanded eighteen-preset build and appearance options have not been re-benchmarked.

## Lightweight interface polish

The main preview decodes to at most 1024 × 640 pixels and reuses its scaled image between repaints. Original wallpaper files remain full resolution. Character cards switch between three and four columns as the window resizes. Press `/` to focus desktop preset search. Ctrl+1, Ctrl+2 and Ctrl+3 open Appearance, Backups & restore and Terminal & tools.

Backup scanning starts when Backups & restore is opened, then watches for external snapshot and protection changes while the page is visible, with a 30-second refresh fallback. Status checks retain unsaved portrait choices and skip decoding portrait previews when saved preferences and the desktop character are unchanged.

A local three-run offscreen check on the twelve-character build measured median Rust startup at 353 ms versus 420 ms before this pass, with resident memory around 66 MiB versus 67 MiB. These are development-machine measurements, not live Wayland or steady-state CPU measurements. Startup now defers backup scanning, so it performs less work before showing the window than the historical benchmark above.
