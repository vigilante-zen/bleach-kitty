# Project checkpoint

This file records a continuation point for the Bankai desktop project.

- Repository: `bleach-kitty`
- Branch: `main`
- Starting checkpoint: `b28bb11` (`Make Python preset application transactional`)
- At this checkpoint, `main` is 26 commits ahead of `origin/main`.
- Preserve the six user-local screenshots in `artifacts/`; they are untracked and should not be deleted or replaced.

## Next work

Review and complete custom preset application so the automatic safety snapshot captures the previous appearance choices. The Rust and Python paths should both update saved appearance preferences in the same transaction as the preset configuration, after the snapshot is created. Then run the relevant Rust and Python validation, commit the completed changes, and push `main` when GitHub is reachable.

The active Codex project goal tracks this continuation across sessions. Start by checking `git status` and reading the current implementation before editing.
