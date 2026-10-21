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

The previous custom-preset improvement also remains in place: both editions snapshot old appearance choices, then commit the preset and replacement choices together. Validation for the latest restore work passed: 57 Python tests, 33 Rust tests, 22 Rust/Python snapshot compatibility checks, nine Python snapshot-manager checks, the Python runtime check, Clippy with warnings denied, and an optimized Rust build.

Release-package verification runs a snapshot create/restore cycle against the extracted Python package and prebuilt Rust package, including absent-file cleanup and the pre-restore backup. The Python, Rust-source and prebuilt-Rust archives all passed that check. Regular push and pull-request CI now builds and verifies the same three packages.

The next project change can follow the user's next request. The latest push attempt failed because this environment could not resolve `github.com`; push `main` when GitHub DNS is available.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.
