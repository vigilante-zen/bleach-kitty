# Project checkpoint

This file records a continuation point for the Bankai desktop project.

- Repository: `bleach-kitty`
- Branch: `main`
- Starting checkpoint: `b28bb11` (`Make Python preset application transactional`); the continuation note was committed as `35c3443`.
- Preserve the six user-local screenshots in `artifacts/`; they are untracked and should not be deleted or replaced.

## Latest completed work

Snapshot restore in both Rust and Python now stages and verifies all target bytes before applying them. Replacements and absent-file deletions are transactional: if a later operation fails, earlier files are restored with their original contents and permissions. Failure-injection tests cover a restore that has already replaced and deleted files before failing. Python and Rust also reject a boolean manifest version instead of treating JSON `true` as integer version `1`.

The previous custom-preset improvement also remains in place: both editions snapshot old appearance choices, then commit the preset and replacement choices together. Validation for the latest restore work passed: 52 Python tests, 32 Rust tests, 22 Rust/Python snapshot compatibility checks, the Python runtime check, Clippy with warnings denied, and an optimized Rust build.

Release-package verification runs a snapshot create/restore cycle against the extracted Python package and prebuilt Rust package, including absent-file cleanup and the pre-restore backup. The Python, Rust-source and prebuilt-Rust archives all passed that check. Regular push and pull-request CI now builds and verifies the same three packages.

The next project change can follow the user's next request. Push `main` when GitHub DNS is available; a push from this environment previously failed because `github.com` could not be resolved.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.
