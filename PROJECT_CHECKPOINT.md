# Project checkpoint

This file records a continuation point for the Bankai desktop project.

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

The next project change can follow the user's next request. The latest push attempt failed because this environment could not resolve `github.com`; push `main` when GitHub DNS is available.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.

## Resume here

The latest code commit is `30094e3` (`Preserve snapshot list after scan failure`) on `main`, tracking `origin/main`; at that code commit the branch was 91 commits ahead of its upstream. There are no uncommitted tracked changes after the accompanying checkpoint note is committed. The untracked `artifacts/` directory contains user-local screenshots and must be preserved.

The latest Rust UI change adds a live, singular/plural-aware matching-character count to the terminal picker. Its accessible description now includes the current count, including zero results, so assistive technology can query it on Qt versions without live announcement support. The smoke test verifies both accessible descriptions. Validation passed 41 Rust tests, Clippy with warnings denied, the optimized Rust build, the offscreen GUI smoke test and `git diff --check`.

Latest continuation work adds a polite, 350 ms debounced screen-reader announcement when the terminal picker's visible result set changes, even when two different result sets have the same size. The announcement and accessible description identify the active search, selected filter, result count and first matching character; zero results omit the stale first-result text. Resize-only rebuilds do not announce because the IDs remain unchanged. The isolated smoke home creates a second synthetic portrait and verifies that replacing one result with another keeps the count at one, changes the exposed first-result name, and restarts the announcement timer. Offscreen Qt does not deliver announcement events to the installed test update handler, so spoken output still requires a live KDE screen-reader check. Validation passed 41 Rust tests, Clippy with warnings denied, the optimized build and the native offscreen smoke test.

The current environment has Wayland display variables but no Orca process, and querying the session accessibility bus fails with `Operation not permitted`. Do not mark spoken output verified here; repeat that check from an unrestricted KDE session with a running screen reader.

An additional cross-edition validation sweep after `5e16d3f` passed all 57 repository tests, all 26 Python snapshot-manager checks, the Python runtime checks, all 22 compiled Rust binary integration checks, and shared command routing. The Rust-specific Clippy, 41 tests, optimized build and native offscreen smoke test also passed. GitHub remains unsynced because `git push origin main` still fails DNS lookup for `github.com`; the branch is 86 commits ahead and `artifacts/` remains untouched.

The Python offscreen control-center suite also passed 21 checks; its local-socket forwarding check was skipped because the sandbox rejects `QLocalServer::listen`. It ran after the prior cross-edition sweep and did not change tracked files.

The Rust Backups page now distinguishes snapshot scan errors from a successful scan that found no snapshots. On failure, it keeps the last snapshot list and selection for context, disables Verify/Preview/Restore/Protect/Cleanup until a successful scan, and directs the user to Refresh. The native smoke test simulates a failed scan with a stale selected snapshot, verifies the selection remains visible and actions are disabled, then confirms a successful empty refresh replaces the stale item. Validation passed 41 Rust tests, Clippy with warnings denied, the optimized build, native smoke checks and `git diff --check`.

Snapshot scans now run in a dedicated background process, keeping the Qt interface responsive while Rust walks and fingerprints saved backups. Overlapping page, watcher and periodic refreshes are coalesced; the visible list remains until a successful scan replaces it, and actions stay disabled while results could be stale. The native smoke check now waits for asynchronous scans and confirms external snapshot refresh still works. Validation passed Clippy with warnings denied, all 41 Rust tests, the optimized build, native offscreen smoke checks and `git diff --check`. `cargo fmt --check` still reports broad pre-existing formatting differences across Rust files, so no unrelated formatting sweep was applied. The user's untracked `artifacts/` folder remains untouched.

To resume, open this repository, read this checkpoint, then check `git status --short --branch` and inspect the implementation related to the next requested change. Keep `artifacts/` untouched. GitHub may still need syncing: push `main` only when network access is available and after checking the remote state.
