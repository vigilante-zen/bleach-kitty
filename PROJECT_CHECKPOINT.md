# Project checkpoint

This file records a continuation point for the Bankai desktop project.

## Windows Terminal integration handoff (2026-10-22)

Windows Terminal color integration is implemented and pushed through `23f601c`.
The app now has Wallpaper and Windows Terminal tabs. Terminal detects Stable,
Preview, Canary and standard unpackaged settings, supports choosing another JSONC
settings file, lists explicit profiles plus inherited defaults, and previews all
18 character schemes. Colors match the existing Kitty palette and character
accent overrides. Apply adds a named Bankai scheme and changes only the chosen
profile's colorScheme. Fonts, commands, keybindings, background images, unrelated
profiles, schemes and settings text are preserved. Existing comments, BOMs and
trailing commas are supported; ambiguous duplicate keys and conflicting existing
Bankai scheme names are rejected.

`TerminalSettingsManager` saves exact bytes and SHA-256 metadata separately for
each target under `%LOCALAPPDATA%\Bankai\TerminalBackups`. It locks across Bankai
instances, checks for external edits, and uses atomic replacement. Restore checks
integrity and refuses settings edited since Bankai's last write, saves the file it
replaces, and can itself be undone. A failed replacement restores the preceding
backup metadata. Reads are bounded at 8 MiB and symlink/junction paths are refused.
Recovery is independent of current profile selection. Refresh rediscovers current
installations while retaining a selected custom settings file.

All 11 wallpaper and 16 Terminal checks pass on Linux and Windows (27 per host).
The platform-specific Terminal checks differ: Linux tests symlink boundaries;
Windows tests a sharing violation during atomic replacement and continued access
to the earlier restore point. Windows run
https://github.com/vigilante-zen/bleach-kitty/actions/runs/39882854418 passed publish,
wallpaper preview/search checks and a real WinUI Terminal Apply/Restore flow using
an isolated temporary settings file. No real wallpaper or Terminal settings were
changed. The run uploaded the portable ZIP and its SHA-256 sidecar. Local download:
`dist/windows-terminal-23f601c`.

Start on another computer with `docs/WINDOWS_HANDOFF.md` and
`desktop/windows/README.md`. Live Terminal reload, picker use, profile override
behavior, Narrator and real wallpaper/multi-monitor behavior still need interactive
Windows validation. Shell artwork/prompt installation, terminal launchers, tray,
single-instance activation, startup, a backup browser and installer/signing remain
future work. User screenshots in `artifacts/` and Linux editions are preserved.
The older checkpoints below describe earlier milestones, not unfinished Terminal
color integration. The Linux release is still separate and pending publication.

## Current Windows handoff (2026-10-22)

For switching computers, start with `docs/WINDOWS_HANDOFF.md`: it includes clone,
build and test commands, the verified preview checksum, and a resume prompt for a
new coding session. All implementation work is pushed to `main`; the original
computer's untracked screenshots and generated downloads remain local.

The user explicitly switched focus to continuing the Windows package. The WinUI 3
C# preview is committed and pushed through `e91ddac`. It shares the existing 18
preset definitions and wallpaper assets, supports character search and previews,
and has explicit Apply wallpaper / Restore previous wallpaper controls.

Windows wallpaper changes use `IDesktopWallpaper` on a background STA thread.
Before changes, the app saves independent image copies, per-monitor assignments,
position and background color under `%LOCALAPPDATA%\Bankai\WallpaperBackups`, with
an atomically replaced previous-wallpaper pointer. Applied images have their own
stable copies under the same state root. Failed changes attempt rollback, and
restores save the background they replace. Operations are serialized across app
instances. Static Picture and Solid color backgrounds are supported; slideshow
backgrounds are refused, and restore requires the original monitor set.

All 11 isolated recovery checks pass on both Linux and Windows. GitHub run
https://github.com/vigilante-zen/bleach-kitty/actions/runs/39810412818 passed the
Windows x64 publish, launched the published app, verified initial image loading,
character filtering, empty-result action safety and clearing search, then uploaded
the `bankai-windows-x64-preview` artifact containing a portable ZIP and SHA-256
sidecar. Tested source commit: `e91ddac`. WinUI publish requires
`EnableMsixTooling=true` and an explicitly named `resources.pri`; smoke checks catch
missing resources. Search checks wait for WinUI's deferred text-change events.
The downloaded artifact is under `dist/windows-e91ddac`.

Real wallpaper application/restore through the native COM implementation,
multi-monitor behavior, keyboard navigation and Narrator still need live Windows
desktop testing; automated recovery checks use a fake backend and do not change
the runner's real wallpaper. Windows Terminal integration, tray/single-instance
activation, login startup, a backup browser, installer/signing and automatic
updates remain future work. Linux implementations and user screenshots in
`artifacts/` were preserved. No Windows GitHub release was published.

The Linux release below is still pending publication; its earlier network-blocked
notes are historical. Do not treat the Windows artifact as a completed Linux
release. The current user focus is the Windows edition.

## Linux release preparation (2026-10-22)

Network access was enabled later on 2026-10-22. Git fetch/push and the GitHub API
now work. Release prep and follow-up fixes are pushed through `dcb7696` on main.
There are no existing remote release tags or GitHub releases at this check.
The old GitHub CI failures exposed a Python socket-wrapper lifetime crash and
a Rust smoke predicate that waited on retired hidden thumbnails. Both are fixed;
all 23 Python UI checks (including socket forwarding, no skip), all 43 Rust tests,
Clippy, the optimized build, native smoke, 60 repository tests and 22 binary
integration checks pass locally. Updated packages from clean commit `dcb7696`
are verified in `dist/v2026.10.22-dcb7696`.

Manual release preflight is running at
https://github.com/vigilante-zen/bleach-kitty/actions/runs/39804029105 . Python and
installer jobs passed; the Rust job was still installing native build dependencies
at the last check. Push checks also run at 39804030177. Wait for the preflight to
pass before publishing; the release and tag still have NOT been created. Release
notes with the changelog link adjusted for GitHub are prepared at
`/tmp/bankai-v2026.10.22-release-notes.md`. User authorization to publish persists.
Use the exact tested commit as the tag target, then verify release workflow success
and all download assets. Preserve uncommitted Windows work and user screenshots.

The user authorized publishing the completed Linux changes. Commit `899e178`
groups them under proposed tag `v2026.10.22` in `docs/CHANGES.md` and adds release
notes at `docs/releases/v2026.10.22.md`. Packages were rebuilt from a clean
`git archive` of that commit into `dist/v2026.10.22`, excluding the uncommitted
Windows preview. Python, Rust-source and local CachyOS x86-64 Rust archives all
passed `scripts/check_release_packages.py`, including checksums, extracted
installers, login lifecycle and snapshot restore. Existing dist archives and
user screenshots were preserved.

Publication is pending: `gh release list` could not connect to api.github.com and
`git ls-remote --tags origin` failed DNS resolution. No tag or GitHub release was
created, and the release commit was not pushed. When GitHub is reachable, inspect
remote tags/releases and branch state first; confirm the proposed tag is unused,
push the Linux release commit, then publish with its notes. The release workflow
will build the Ubuntu Linux binary and attach packages after checks pass. Keep
Windows changes separate and do not upload the CachyOS binary under the Ubuntu
`linux-x86-64` filename.

## Windows edition start (2026-10-22)

The user chose a dedicated WinUI 3 Windows interface. `desktop/windows` now
contains an initial C# / .NET 10 unpackaged x64 app with character search and
wallpaper previews, linked to the existing shared catalog and artwork. No Windows
desktop changes, Rust bridge, backups, tray, or startup integration are implemented
yet. `.github/workflows/windows.yml` builds and uploads the preview on Windows;
that workflow has not been run in this session. This Linux host has no .NET SDK,
so compilation and live WinUI behavior remain unverified. Start with the Windows
build and runtime checks documented in `desktop/windows/README.md` before adding
desktop integrations. Preserve the user's untracked `artifacts/` screenshots.

## Current handoff (2026-10-21)

- Repository: `/home/zen/Projects/bleach-kitty`; branch `main`, synced at `55aaaa7` according to the local `origin/main` ref, and the user-provided push output confirms GitHub accepted that commit. A subsequent fetch from this environment failed because it could not resolve `github.com`. The tracked worktree is clean; `artifacts/` is untracked user data.
- Preserve the untracked `artifacts/` directory. It contains user screenshots; do not remove, replace, or add it to commits.
- The latest Rust picker change makes cached missing portraits keep one accessible error description. Its smoke assertion covers a repeated cache hit. Clippy, all 43 Rust tests, the optimized build, the offscreen native smoke test, and `git diff --check` passed.
- The terminal picker's Recently used filter now reads `art-history.json` through a 64 KiB limit, rejects symlinks and non-regular files, and ignores oversized or malformed data. The native smoke test feeds it a valid oversized history and confirms no recent result is shown. Clippy, all 43 Rust tests, the optimized build, native smoke checks, and `git diff --check` passed.
- The character picker now retrieves installed groups, group members, favorites, portrait display names, rotation, and shuffle mode in one roster-helper invocation, replacing up to eleven synchronous process launches. Five-run medians on this machine were 488 ms for the old helper-call sequence and 45 ms for the batched call (10.9× for metadata loading; this is not a whole-dialog benchmark). Python CLI tests cover the response and unchanged preferences; the staged installer and native picker smoke test pass.
- Roster favorite and shuffle-deck JSON reads are now limited to 64 KiB, and shuffle-mode reads to 128 bytes. The helper opens no-follow, nonblocking and verifies regular files before reading; tests cover malformed, oversized, symlinked and FIFO input. `MANIFEST.json` has the refreshed helper digest.
- Wallpaper preview loading/error status now appears in a compact badge at the top of the artwork panel instead of over the character title. Clippy, all 43 Rust tests, the optimized build and native smoke test pass; the smoke screenshot visually confirms the title and status do not overlap.
- The current release binary and shared payload are installed in `/home/zen`. The installer preserved the edited terminal launcher and login-startup preference; the installed binary version, roster-helper checksum, seven-group/46-portrait response, and installed offscreen native smoke test were verified. Test screenshots went to `/tmp/bankai-installed-smoke-artifacts`.
- Fresh verification on 2026-10-21 passed: all 60 repository Python tests, 26 Python snapshot-manager checks, 23 Python offscreen control-center checks (one local-socket test skipped because this environment blocks sockets), all 43 Rust tests, 22 compiled-binary integration checks, Clippy with warnings denied, the optimized release build, the offscreen native GUI smoke test, and `git diff --check`. Smoke screenshots were directed to `/tmp/bankai-resume-smoke`; the user's `artifacts/` directory was not touched.
- Existing archives under `dist/` had been stale: the Python archive lacked `desktop/shared/snapshot_paths.json`. They were preserved under `dist/archive-20261021-stale/`; current Python, Rust-source, and prebuilt CachyOS x86-64 Rust packages now occupy `dist/`. `python3 scripts/check_release_packages.py dist` passed for all three current packages, including checksum, extracted installer, login-theme lifecycle, and snapshot restore checks.
- The user confirmed live KDE behavior: changing a wallpaper applied its colors, and launching a second instance produced the intended single-window behavior. Tray display and spoken picker announcements remain to be checked in a live session. The offscreen smoke suite also passed with `QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1`, but this session has no Orca and blocks access to its session accessibility bus, so that does not verify spoken output.
- To resume, check `git status --short --branch`, preserve `artifacts/`, and continue with the next requested feature. There is no uncommitted implementation work at this handoff.

- Repository: `bleach-kitty`
- Branch: `main`
- Starting checkpoint: `b28bb11` (`Make Python preset application transactional`); the continuation note was committed as `35c3443`.
- Preserve the six user-local screenshots in `artifacts/`; they are untracked and should not be deleted or replaced.

## Current verification checkpoint

At `58c938a` and later, the full local CI-equivalent check passed: 57 repository installer/package tests, 23 Python snapshot-manager checks, the Python runtime check, 20 offscreen control-center checks (one local-socket check skipped because this environment blocks sockets), 39 Rust tests, Clippy with warnings denied, an optimized Rust build, 22 compiled Rust integration checks, shared command routing, and create/restore verification for the Python, Rust-source, and prebuilt Rust release archives. Temporary package outputs were written under `/tmp/bankai-ci-packages`.

The current branch remains local-only because this environment cannot resolve `github.com`; `main` is ahead of `origin/main`. The untracked `artifacts/` screenshots remain user data.

The latest continuation adds `desktop/shared/snapshot_paths.json` as the common restore and cleanup allowlist. Rust embeds it, while Python loads it from the source tree or beside the installed module; the installer includes it in Python packages. Regression checks ensure both implementations share the Rust catalog paths, Python-created backup manifests remain cleanup-eligible, and paths such as `.ssh/id_rsa` are rejected. The Python package verifier also installs and exercises the actual packaged Python scanner. The latest local validation passed 26 snapshot-manager checks, 57 repository tests, Python runtime and offscreen UI checks, 40 Rust tests, Clippy with warnings denied, an optimized Rust build, 22 Rust/Python integration checks, and all three release archive checks. The branch still needs pushing when GitHub DNS is available.

The Rust UI now gives screen readers named appearance and terminal-artwork previews, character-specific preview descriptions, and accessible names/descriptions for terminal search, faction filters and Random. The native smoke test verifies that preview descriptions update with the selected character. Validation passed 40 Rust tests, Clippy with warnings denied, the optimized build, the offscreen native smoke test, and 22 compiled-binary integration checks. The live Qt screen-reader experience still needs verification on a desktop session.

Small-screen layout now derives the main window minimum from available display geometry, lets the navigation sidebar shrink to 150 logical pixels, and wraps Backup & restore in a scroll area. The smoke test checks minimum-size calculations at 800×600 and 1920×1080, plus the backup scroll container. The 40 Rust tests, Clippy, optimized build and offscreen native smoke test pass.

Appearance-options shuffle controls now describe the character filter, list, live selected count and select/clear shown actions to screen readers. Backup selection, details, storage status, protection, restore review and cleanup preview also have explicit accessible context. The native smoke test checks these properties. The 40 Rust tests, Clippy, optimized build and offscreen smoke test pass.

Keyboard focus now has a high-contrast pink border on buttons, character cards, combo boxes, search fields, spin boxes, lists, checkboxes and activity text. The smoke test checks that these control families have focus styling, and its keyboard-search test confirms focus reaches the search field. The 40 Rust tests, Clippy, optimized build and offscreen smoke test pass.

The native UI smoke test now queries Qt's `QAccessibleInterface` for names and descriptions on appearance previews, terminal search/filter/Random controls, shuffle-pool controls, and snapshot actions. It also verifies character descriptions change after selection. This checks the accessibility values exposed by Qt, beyond checking widget properties; actual spoken output still requires a live KDE accessibility session.

The accessibility interface check now also covers main navigation, custom preset selection and actions, terminal desktop-follow and art-style choices, Rust autostart, and the activity log. The 41 Rust tests, Clippy, optimized build and offscreen native smoke test pass. Live announcements remain unverified because this environment has no Orca and cannot access its session D-Bus.

The Rust Backups & restore page now filters snapshots case-insensitively by their displayed name and status. Empty matches disable restore and explain how to clear the search, distinct from the true empty-backup state. The offscreen smoke test verifies case-insensitive matching, clearing, empty-result safety and external snapshot refresh. Validation passed all 40 Rust tests, Clippy, the optimized build and native UI smoke checks.

The Backups page now offers an asynchronous, integrity-checked restore preview. It lists every file that would be restored and every path that would be removed because it was absent in the selected snapshot; it does not apply changes. A Rust test confirms inspection leaves current files untouched, and the native smoke test opens and verifies the actual preview dialog. All 41 Rust tests, Clippy, optimized build and native smoke checks pass.

The Rust sidebar now uses a content-sized maximum width and tighter navigation spacing so “Backups & restore” is fully visible without a horizontal scrollbar; tooltips include full labels and Ctrl+1/2/3 shortcuts. The UI smoke test asserts sidebar navigation needs no horizontal scrolling. Rust tests, Clippy, optimized build and native smoke checks pass.

Single-instance startup in Python and Rust now rejects symlinked state-directory ancestors and existing control lock/socket symlinks before creating or using IPC paths. Rust bootstrap validates the state path before the Qt launcher creates it. The offscreen Python UI suite passes 21 checks (one socket test skipped because sockets are blocked), and all 40 Rust tests, Clippy, and the optimized build pass.

## Latest completed work

Snapshot restore in both Rust and Python now stages and verifies all target bytes before applying them. Replacements and absent-file deletions are transactional: if a later operation fails, earlier files are restored with their original contents and permissions. Failure-injection tests cover a restore that has already replaced and deleted files before failing. Python and Rust also reject a boolean manifest version instead of treating JSON `true` as integer version `1`.

Snapshot manifests are capped at 16 MiB across Rust verification, Python backup/restore and Python snapshot scanning; creation refuses a manifest larger than the verifier accepts.

Subprocess and extracted-package tests confirm the Python backup CLI includes and restores KDE configuration alongside terminal settings. Creation now rejects dangling symlinks in configured files instead of recording them as absent.

Python snapshot path checks now reject symlinked boundary directories and paths outside their allowed root, matching Rust behavior.

Python snapshot scans and cleanup previews now take the same cross-edition lock used by Rust and the Python backup utility. Cleanup revalidates its reviewed plan through the internal scan while holding one lock, avoiding nested locking. The scanner also rejects boolean manifest versions, duplicate paths and noncanonical relative paths, matching Rust's cleanup eligibility checks. The snapshot-manager suite now has 11 passing checks covering these cases and lock use; `python desktop/python/check.py` also passed after these changes.

Python snapshot manifest reads now stop at 16 MiB plus one byte in both the cleanup scanner and backup/restore utility, matching Rust's bounded read and preventing oversized files from being fully loaded before rejection. The 12 snapshot-manager checks, including a read-bound assertion, and the Python runtime check passed.

Python backup now checks its state directory and lock path for symlinks before opening the cross-edition lock; `SnapshotStore` also refuses a symlinked lock file. Regression checks confirm the CLI does not create a lock through a symlinked state directory. All 14 snapshot-manager checks and the Python runtime check pass.

`SnapshotStore` now checks every ancestor of its snapshot root and state/lock paths for symlinks, so an indirect alias cannot bypass the snapshot boundary checks used by Rust. The snapshot-manager suite now has 15 passing checks, including a symlinked-parent regression, and the Python runtime check passes.

Python cleanup planning and reviewed-plan validation now enforce Rust's maximum of 1,000 retained snapshots. All 16 snapshot-manager checks and the Python runtime check pass.

The Python control center now attempts snapshot scans, previews and protection changes without waiting on the cross-edition lock, avoiding a frozen UI while backup or restore is running elsewhere. A busy scan shows a status message and retries after one second; cleanup still waits in its background process and revalidates while holding the lock. All 17 snapshot-manager checks, 20 offscreen control-center checks (one local-socket check skipped because sockets are unavailable here), and the Python runtime check pass.

When a busy scan is retried, the control center keeps the current snapshot list and selection visible until fresh data is available. The offscreen UI check verifies the retained selection and list.

Rust and Python snapshot scanners now validate the manifest's `absent` list before marking a snapshot eligible for cleanup. They reject malformed lists, traversal paths, and paths duplicated in the saved-file entries; Rust also applies its restore allowlist. The Python snapshot suite (18 checks), Python runtime check, Rust suite (34 tests), and Clippy with warnings denied all pass.

Python protection metadata loading now checks dangling symlinks before testing for file existence and reads no more than 16 MiB plus one byte, matching Rust's bounded JSON reader. Regression tests cover dangling links and oversized metadata; Python snapshot checks (20) and runtime checks pass, as do 35 Rust tests and Clippy with warnings denied.

Snapshot verification and protection loading in both editions now reject FIFOs and other non-regular files before opening or hashing them, preventing indefinite waits on special files. Python and Rust cover FIFO manifests, payloads and protection metadata. All 22 Python snapshot checks, the Python runtime check, 38 Rust tests and Clippy with warnings denied pass.

Both editions now reject a symlinked snapshot manifest when the user tries to protect that snapshot, preventing invalid snapshots from being recorded as protected. The Python snapshot suite now has 23 passing checks; all 39 Rust tests and Clippy with warnings denied pass.

The previous custom-preset improvement also remains in place: both editions snapshot old appearance choices, then commit the preset and replacement choices together. Validation for the latest restore work passed: 57 Python tests, 33 Rust tests, 22 Rust/Python snapshot compatibility checks, nine Python snapshot-manager checks, the Python runtime check, Clippy with warnings denied, and an optimized Rust build.

Release-package verification runs a snapshot create/restore cycle against the extracted Python package and prebuilt Rust package, including absent-file cleanup and the pre-restore backup. The Python, Rust-source and prebuilt-Rust archives all passed that check. Regular push and pull-request CI now builds and verifies the same three packages.

The last push attempt failed because this environment could not resolve `github.com`; the current local commits remain ahead of `origin/main` and should be pushed when GitHub DNS is available.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.

## Resume here

The current feature work is committed on `main`, which has local commits ahead of `origin/main`; use `git log -5 --oneline` for the exact handoff point. The worktree has no uncommitted tracked changes at this checkpoint. The untracked `artifacts/` directory contains user-local screenshots and must be preserved.

The latest Rust UI change adds a live, singular/plural-aware matching-character count to the terminal picker. Its accessible description now includes the current count, including zero results, so assistive technology can query it on Qt versions without live announcement support. The smoke test verifies both accessible descriptions. Validation passed 41 Rust tests, Clippy with warnings denied, the optimized Rust build, the offscreen GUI smoke test and `git diff --check`.

Latest continuation work adds a polite, 350 ms debounced screen-reader announcement when the terminal picker's visible result set changes, even when two different result sets have the same size. The announcement and accessible description identify the active search, selected filter, result count and first matching character; zero results omit the stale first-result text. Resize-only rebuilds do not announce because the IDs remain unchanged. The isolated smoke home creates a second synthetic portrait and verifies that replacing one result with another keeps the count at one, changes the exposed first-result name, and restarts the announcement timer. Offscreen Qt does not deliver announcement events to the installed test update handler, so spoken output still requires a live KDE screen-reader check. Validation passed 41 Rust tests, Clippy with warnings denied, the optimized build and the native offscreen smoke test.

The current environment has Wayland display variables but no Orca process, and querying the session accessibility bus fails with `Operation not permitted`. Do not mark spoken output verified here; repeat that check from an unrestricted KDE session with a running screen reader.

An additional cross-edition validation sweep after `5e16d3f` passed all 57 repository tests, all 26 Python snapshot-manager checks, the Python runtime checks, all 22 compiled Rust binary integration checks, and shared command routing. The Rust-specific Clippy, 41 tests, optimized build and native offscreen smoke test also passed. At that sweep the branch was 86 commits ahead; GitHub remained unsynced because `git push origin main` failed DNS lookup for `github.com`, and `artifacts/` remained untouched.

The Python offscreen control-center suite also passed 21 checks; its local-socket forwarding check was skipped because the sandbox rejects `QLocalServer::listen`. It ran after the prior cross-edition sweep and did not change tracked files.

The Rust Backups page now distinguishes snapshot scan errors from a successful scan that found no snapshots. On failure, it keeps the last snapshot list and selection for context, disables Verify/Preview/Restore/Protect/Cleanup until a successful scan, and directs the user to Refresh. The native smoke test simulates a failed scan with a stale selected snapshot, verifies the selection remains visible and actions are disabled, then confirms a successful empty refresh replaces the stale item. Validation passed 41 Rust tests, Clippy with warnings denied, the optimized build, native smoke checks and `git diff --check`.

Snapshot scans now run in a dedicated background process, keeping the Qt interface responsive while Rust walks and fingerprints saved backups. Overlapping page, watcher and periodic refreshes are coalesced; the visible list remains until a successful scan replaces it, and actions stay disabled while results could be stale. Cleanup planning also runs in a worker, since it scans and fingerprints every saved snapshot before showing the review dialog. The native smoke check verifies that a scan keeps the prior list visible, collapses repeated refresh triggers into one pending scan, replaces stale results, refreshes after external snapshots, and returns an empty cleanup plan through the background UI path. Validation passed Clippy with warnings denied, all 41 Rust tests, the optimized build, native offscreen smoke checks and `git diff --check`. `cargo fmt --check` still reports broad pre-existing formatting differences across Rust files, so no unrelated formatting sweep was applied. The user's untracked `artifacts/` folder remains untouched.

The confirmed Rust appearance reset also runs through a background worker because it creates a snapshot before applying the default desktop. Its success updates the selected preview only after the operation completes; errors are surfaced through the normal task status. The native smoke test now accepts the reset confirmation in its isolated home and verifies the real worker completes successfully, using a temporary regular TYBW artwork file to retain the app's symlink protections. Clippy, all 41 Rust tests, the optimized build and native offscreen smoke checks pass.

Rust appearance-option saves and repairs, plus custom-preset saves and deletes, also use background workers because they acquire the lock shared with Python and Rust snapshot operations. The appearance editor closes when saving begins and reports conflicts or other failures in the main task status/log; successful saves refresh the selected preview. Native smoke coverage exercises successful UI appearance saves, stale-save conflict handling, malformed-settings repair, and custom-preset save/delete. Verify this flow along with appearance reset, cleanup planning and snapshot scanning when revisiting UI responsiveness. Keep `artifacts/` untouched; the last GitHub push still failed because `github.com` could not be resolved from this environment.

Worker RPC output now retains complete responses up to 32 MiB, replacing the previous silent 2 MiB truncation that could break large restore previews, cleanup plans or snapshot lists. Larger responses stop with a clear status error; activity-log display remains capped to its most recent 2 MiB. The native smoke test streams a 3 MiB child-process response through the new buffer path and confirms it is preserved. Clippy, all 41 Rust tests, the optimized build, native offscreen smoke checks and `git diff --check` pass.

The shared custom-preset JSON is now capped at 64 KiB in both editions. Rust and Python read at most one byte over the limit before rejecting the file, reject FIFOs and other non-regular files without reading them, and enforce the same cap when writing. New checks cover oversized files and FIFOs in both editions. Clippy and all 43 Rust tests pass; the Python offscreen control-center suite passes 23 checks (one local-socket test skipped because this environment blocks sockets); the optimized Rust build, native smoke check and `git diff --check` pass.

A full local CI-equivalent sweep after the custom-preset limit passed all 57 repository tests, 26 Python snapshot checks, 23 Python control-center checks (one sandbox socket skip), all 43 Rust tests, Clippy with warnings denied, the release build, 22 compiled Rust integration checks, shared command routing, and create/restore verification for the Python, Rust-source and prebuilt Rust archives. Packages were staged under `/tmp/bankai-current-packages`. The native offscreen smoke test also passed, and `artifacts/` remains untouched.

Snapshot-list model refresh now suspends dynamic proxy filtering and view repaint while rows are replaced, then filters once after the batch. The native smoke test applies 4,096 synthetic rows, checks the full count, searches to one match, clears search and resets the list. Worker RPC JSON responses are decoded on a thread-pool worker before queued delivery to the UI, covering both snapshot scans and regular tasks; the UI remains in its in-progress state until the result is handled. The native smoke test parses a 4 MiB JSON response and verifies the UI event loop remains responsive and the payload is complete. Clippy with warnings denied, all 43 Rust tests, the optimized release build, native offscreen smoke checks and `git diff --check` pass. `artifacts/` remains untouched.

The native smoke suite now also sends a 33 MiB worker response through the output collector and verifies it is stopped at the configured 32 MiB cap without retaining excess bytes. Clippy, all 43 Rust tests, the optimized release build, native offscreen smoke checks and `git diff --check` pass. GitHub synchronization remains blocked because `git ls-remote origin refs/heads/main` could not resolve `github.com`; the local branch was 105 commits ahead before this check-only commit. Preserve `artifacts/`.

Worker JSON parsing now uses a two-thread pool owned by the Rust window instead of the process-wide pool. Window teardown waits for outstanding parses, preventing a parser job from outliving the callback target during tray-driven shutdown. The native smoke suite destroys a temporary window with a parse callback queued and verifies no completion is delivered afterward. Clippy, all 43 Rust tests, release build, native smoke checks and `git diff --check` pass.

The comparison benchmark now imports the Python edition from this checkout, verifies both source catalogs contain the same presets, reports the current catalog size and host/runtime versions, and supports `--output` so a fresh measurement does not overwrite existing results. Rust preset-card images and the main wallpaper preview decode on the window-owned worker pool. A shared atomic generation cancels obsolete preview jobs before and after decoding, and generation checks prevent late results replacing the current selection; RPC parsing has higher queue priority than images. Native smoke checks rapidly select six characters, verify the newest preview wins, verify every card loads, and ensure missing thumbnails show an accessible error state. Seven interleaved runs on this AMD Ryzen 9 3950X (Python 3.14.8, Qt 6.12.0) measured Rust first paint at 77 ms, all wallpaper art ready at 260 ms and 82.4 MiB RSS after loading, versus 1,615 ms / 105.5 MiB for Python, which loads thumbnails synchronously. Backup scanning is lazy and excluded. Raw data was kept under `/tmp` to preserve user artifacts. Clippy, all 43 Rust tests, optimized build, native smoke checks, Python compilation and benchmark runs pass.

The searchable terminal character picker now also decodes portrait thumbnails on the window-owned pool and uses a search-generation token so filtering drops queued and late stale artwork. A 64-entry cache of scaled images, keyed by file path, size and modification time, prevents repeated decodes when returning to prior results. Opening the picker raises its thumbnail tasks above background preset thumbnails. The native smoke test waits for its two real portrait fixtures, confirms a filter rebuild hits the cache, and exercises the missing-file state, including the parent card's screen-reader description. Reusing a cached missing portrait keeps that description idempotent, covered by a second-card cache-hit smoke assertion. Clippy, all 43 Rust tests, the optimized release build, native smoke checks and `git diff --check` pass for this picker responsiveness change.

To resume, open this repository, read this checkpoint, then check `git status --short --branch` and inspect the implementation related to the next requested change. Keep `artifacts/` untouched. GitHub may still need syncing: push `main` only when network access is available and after checking the remote state.
