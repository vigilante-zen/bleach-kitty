#!/usr/bin/env python3
"""Build edition-specific release archives from an explicit public-file allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def package(edition, output, binary=None, platform=None):
    if edition not in {'python', 'rust'}:
        raise ValueError('Unknown edition')
    if binary and (edition != 'rust' or not platform or not re.fullmatch(r'[a-z0-9-]+', platform)):
        raise ValueError('Rust binaries require a platform name such as linux-x86-64')
    if binary and (binary.is_symlink() or not binary.is_file()):
        raise ValueError('Rust binary must be an existing regular file')
    name = 'bankai-python' if edition == 'python' else 'bankai-rust-' + (platform if binary else 'source')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (name + '.tar.gz')
    paths = [ROOT / p for p in ['install.py', 'MANIFEST.json', 'LICENSE', 'files', 'docs',
             'login/ARTWORK.json', 'login/install.py', 'login/sync.py', 'login/greeter_preview.py', 'login/legacy-theme.json', 'login/README.md', 'login/preview.py', 'login/preview.png', 'login/theme', 'desktop/install.py', 'desktop/README.md', 'desktop/shared', 'desktop/' + edition]]
    import io
    summary = f'''# Bankai {edition.title()} release package

This package contains the {edition.title()} desktop edition and its shared terminal theme/artwork.

1. Install the prerequisites listed in [the edition guide](desktop/{edition}/INSTALL.md).
2. Preview installation: `python3 desktop/{edition}/install.py --dry-run`
3. Install: `python3 desktop/{edition}/install.py`
4. Launch {'`bankai-python`' if edition == 'python' else '`bankai`'}.

[Full setup, update and uninstall instructions](desktop/{edition}/INSTALL.md).
[Compare editions on GitHub](https://github.com/vigilante-zen/bleach-kitty/blob/main/desktop/README.md).

The Rust binary, when present, is dynamically linked and requires compatible Qt/system libraries.
'''
    with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
        for start in paths:
            for path in sorted(start.rglob('*')) if start.is_dir() else [start]:
                if path.is_relative_to(ROOT / 'desktop/rust/bin'):
                    continue  # Add a compiled executable only through the explicit --binary option.
                if not path.is_file() or any(part in {'__pycache__', '.git', 'target', 'artifacts', 'bin-release'} for part in path.relative_to(ROOT).parts):
                    continue
                if path.is_symlink():
                    raise ValueError(f'Unexpected package symlink: {path}')
                tar.add(path, arcname=name + '/' + str(path.relative_to(ROOT)), recursive=False)
        for relative, data in [('README.md', summary.encode()), ('PACKAGE.json', (json.dumps({'edition': edition, 'platform': platform, 'prebuilt': bool(binary)}, indent=2)+'\n').encode())]:
            entry = tarfile.TarInfo(name + '/' + relative); entry.size = len(data); entry.mode = 0o644
            tar.addfile(entry, io.BytesIO(data))
        if binary:
            entry = tar.gettarinfo(str(binary), arcname=name + '/desktop/rust/bin/bankai-rust'); entry.mode = 0o755
            with binary.open('rb') as stream:
                tar.addfile(entry, stream)
    with archive.open('rb') as stream:
        sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    archive.with_suffix(archive.suffix + '.sha256').write_text(sha + '  ' + archive.name + '\n')
    print(archive)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', choices=['python', 'rust', 'all'], default='all')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--platform')
    args = parser.parse_args()
    if args.binary and args.edition != 'rust':
        parser.error('--binary is only supported with --edition rust')
    for edition in ['python', 'rust'] if args.edition == 'all' else [args.edition]:
        package(edition, args.output, args.binary, args.platform)


if __name__ == '__main__':
    main()
