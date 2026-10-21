# Project checkpoint

This file records a continuation point for the Bankai desktop project.

- Repository: `bleach-kitty`
- Branch: `main`
- Starting checkpoint: `b28bb11` (`Make Python preset application transactional`); the continuation note was committed as `35c3443`.
- Preserve the six user-local screenshots in `artifacts/`; they are untracked and should not be deleted or replaced.

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

The previous custom-preset improvement also remains in place: both editions snapshot old appearance choices, then commit the preset and replacement choices together. Validation for the latest restore work passed: 57 Python tests, 33 Rust tests, 22 Rust/Python snapshot compatibility checks, nine Python snapshot-manager checks, the Python runtime check, Clippy with warnings denied, and an optimized Rust build.

Release-package verification runs a snapshot create/restore cycle against the extracted Python package and prebuilt Rust package, including absent-file cleanup and the pre-restore backup. The Python, Rust-source and prebuilt-Rust archives all passed that check. Regular push and pull-request CI now builds and verifies the same three packages.

The next project change can follow the user's next request. The latest push attempt failed because this environment could not resolve `github.com`; push `main` when GitHub DNS is available.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.
