# Bankai Rust — experimental native edition

A separately installed, compiled edition of the Bankai desktop control center. Application logic is Rust; a Qt Widgets C++ presentation layer provides the window, SVG rendering, tray integration, file watching and background-process plumbing. The main app does not start a Python interpreter. It is not an all-Rust GUI toolkit.

## Try it

```fish
bankai-rust
bankai-rust tray
bankai-rust backups
bankai-rust status
```

You can also search **Bankai Rust** in KDE's app launcher. The existing Python edition remains `bankai`. The Rust edition has its own instance channel and optional login-startup preference. It is not enabled at login by default. Avoid enabling both tray apps at login unless you want two icons.

Both editions read the same saved preset, character artwork, KDE settings, Kitty accents, portrait selection, snapshots and protected-snapshot list. Applying a preset or restoring a snapshot changes the shared desktop. Comparing their windows and previews is read-only; do not apply competing presets from both editions simultaneously.

## Terminal artwork controls

Under **Terminal & tools**, choose **Random characters** or an installed portrait, then **Color**, **Manga**, or **Mixed color and manga**, and click **Save terminal artwork**. Changes apply to new terminal tabs. Random rotation uses the groups and favorites configured in the terminal. Color artwork is used when manga is unavailable. Existing shell-only overrides continue to take precedence in that shell; use `bankai-pick --session reset` to follow saved preferences.

Desktop preset changes now preserve terminal portrait and art preferences. Select the matching portrait explicitly here if desired. The Python app still uses its original preset behavior. Settings use the same files as `bankai-pick` and `bankai-art`, and external changes appear in the app.

These controls require rebuilding from this source. The previously installed executable predates this change.

## Ported behavior

- All eight presets, wallpaper previews, explicit Apply, and automatic snapshots before changes.
- KDE desktop and lock-screen wallpaper, color schemes and terminal accents; independent terminal portrait and art preferences.
- Hollow-mask tray icon colored for the saved character; updates after command-line changes.
- Tray preset selection, terminal and monitor launchers, snapshot creation, and window reopening.
- Background workers run the same Rust binary; action errors are shown and active operations prevent quitting.
- Snapshot creation, verification, restore with a pre-restore backup, sizes, protection, and reviewed cleanup.
- Original baseline protection, newest-copy retention, symlink/path rejection, and cleanup-plan revalidation.
- Existing Python version-1 manifests and protection metadata remain compatible in both directions.
- Independent Rust autostart toggle and single-instance window handoff.

Existing Fish terminal-settings and monitoring commands are launched as external integrations. Diagnostics can launch the existing `bankai-doctor` helper. The system SDDM installer remains a separate Python tool: this app only shows its existing command. The portrait/greeting scripts and login installer were not rewritten.

The Rust executable and its experimental startup preference are not part of the legacy desktop snapshot allowlist. Source code is in this project. Keep the Python edition available while evaluating the port.

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
cargo build --release --locked --offline
```

Requirements: Rust and Cargo, a C++17 compiler, pkg-config, and Qt 6 Widgets, SVG and Network development packages. Rust `cc` and `pkg-config` are build-only dependencies. The JSON codec is local and strict, with duplicate-key, UTF-8, nesting and size checks. Snapshot SHA-256 uses Qt's established `QCryptographicHash` through the narrow native bridge rather than a custom hash implementation.

The machine's package cleanup removed Rust, Cargo and rustfmt **after the release build succeeded**. The executable still runs. Rebuilding and rerunning Rust unit tests requires restoring the toolchain; no system packages were reinstalled by this task. Additional Rust test cases were added afterward but could not be compiled in the resulting environment. `native/gui.cpp` was subsequently formatted with clang-format; its behavior matches the built executable.

References: [Rust FFI](https://doc.rust-lang.org/nomicon/ffi.html), [Qt tray API](https://doc.qt.io/qt-6/qsystemtrayicon.html), [Qt hashing](https://doc.qt.io/qt-6/qcryptographichash.html).

## Validation

- The initial five Rust unit tests passed before toolchain removal.
- Fifteen integration checks passed against the compiled release executable, using disposable homes. They cover all eight presets and two desktop containments, exact SHA-256 compatibility, Rust reading/restoring Python snapshots, Python restoring Rust snapshots, permissions and absent files, corruption rejection, path traversal, symlinks, baseline/favorite/recent-copy retention, changed/protected snapshots after review, extra files, corrupt protection metadata, and independent autostart settings.
- The native offscreen smoke check passed: eight previews and exact mask accents, nonmutating preview selection, tray action population, cleanup protection, background Rust worker, and screenshots at normal/smaller sizes.
- The existing real baseline snapshot was verified read-only by Rust.
- No real desktop settings were changed and no real snapshots were deleted during validation.
- Live KDE tray display, cross-process single-instance activation and live color/wallpaper application remain unverified from this sandbox because it blocks session-bus and Unix-socket access.

```sh
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
