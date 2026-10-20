# Edition packages and automated checks

Every push and pull request runs the theme/desktop installer suite, Python snapshot/UI checks, and Rust unit/integration/UI checks. Native builds run on Ubuntu 24.04 with Qt development libraries; Python UI checks use PySide6 with offscreen rendering. CI success does not verify live KDE wallpaper changes or tray hosting.

## Build packages locally

From the repository root:

```bash
python3 scripts/package_editions.py
python3 scripts/check_release_packages.py
```

This creates `dist/bankai-python.tar.gz` and `dist/bankai-rust-source.tar.gz`, each with a SHA-256 sidecar. Packages include the selected desktop edition, common terminal theme/artwork, and optional manga SDDM theme with twelve full wallpaper scene variants, its system installer, and the preset-sync helper. SDDM activation is a separate administrator command available in both apps; extracted desktop installation never changes the system login screen. Boot splash source remains repository-only and is not included in edition packages. Opposite-edition source, build caches, personal preferences and snapshots are excluded.

Package verification checks both the extracted desktop installer and staged login-theme install/restore. The login system installer has its own receipt and protects modified files.

For a compiled Rust package, build on the intended target system, then label its actual platform:

```bash
cd desktop/rust
cargo build --release --locked
cd ../..
python3 scripts/package_editions.py --edition rust \
  --binary desktop/rust/target/release/bankai-rust --platform linux-x86-64
```

The binary is dynamically linked. The workflow's Linux x86-64 package is built on Ubuntu 24.04 and needs compatible glibc/Qt runtime libraries. No other architectures or universal portability are claimed. Cross-check checksums with `cd dist` followed by `sha256sum -c *.sha256` (the sidecars record archive basenames).

## Publish a release

1. Push the reviewed code and workflow files to GitHub.
2. In **Actions → Edition release packages → Run workflow**, create a test run. It must pass all edition checks before packaging. The resulting `bankai-edition-downloads` artifact provides downloadable test packages for 14 days.
3. Create and publish a GitHub Release for the chosen tag. The release workflow reruns checks, builds the Rust app, and attaches all three edition packages and their checksums to that release.
4. Verify the release's Assets section contains Python, Rust source, and Rust Linux x86-64 downloads. Try the preferred installer from an extracted package on a compatible desktop.

No release is published by running the packaging script locally. The workflow listens to published releases and attaches packages only after its checks pass; a manual workflow run uploads test artifacts without publishing a release. Failed runs leave the release without the expected assets until corrected and rerun.

The packaging job grants `contents: write` for attaching release assets; regular checks have read-only access. See [GitHub workflow permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions) and [GitHub CLI release upload](https://cli.github.com/manual/gh_release_upload).
