# Project checkpoint

This file records a continuation point for the Bankai desktop project.

- Repository: `bleach-kitty`
- Branch: `main`
- Starting checkpoint: `b28bb11` (`Make Python preset application transactional`); the continuation note was committed as `35c3443`.
- Preserve the six user-local screenshots in `artifacts/`; they are untracked and should not be deleted or replaced.

## Latest completed work

Custom preset application in both Rust and Python now creates its automatic safety snapshot before updating shared appearance choices. The preset configuration, current/pending markers, and replacement appearance settings are committed together with rollback on write failure. Rust and Python regression checks confirm the snapshot retains the previous choices.

Validation passed: 50 Python unit tests, 30 Rust unit tests, 22 Rust/Python binary compatibility checks, 19 control-center checks (one local-socket test skipped by the environment), the Python runtime check, Clippy with warnings denied, and an optimized Rust build.

The next project change can follow the user's next request. Push `main` when GitHub DNS is available; a push from this environment previously failed because `github.com` could not be resolved.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.
